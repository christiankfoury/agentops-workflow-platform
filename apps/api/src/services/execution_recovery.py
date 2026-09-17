"""Explicit recovery without reopening terminal execution history."""

from copy import deepcopy
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import load_only

from src.config import settings
from src.models.durable_job import DurableJob
from src.models.execution_recovery import ExecutionRecovery
from src.models.llm_conversation import LLMConversation
from src.models.tool import ToolExecution, ToolVersion
from src.models.workflow_definition import WorkflowDefinition, WorkflowVersion
from src.models.workflow_execution import (
    TERMINAL,
    ExecutionEvent,
    StepRun,
    WorkflowExecution,
)
from src.schemas.tool import ToolContract
from src.services.audit import record_audit
from src.services.durable_queue import enqueue
from src.services.execution_records import add_step, execution
from src.services.graph_interpreter import graph_for
from src.services.permissions import authorize, current_principal, permits
from src.services.recovery_lineage import ancestors
from src.services.retry_runtime import runtime_now
from src.services.workflow_definitions import require_runnable_version
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import workflow_transaction


def effects_for(db, identities, *, lock=False):
    query = (
        select(ToolExecution)
        .join(StepRun, StepRun.id == ToolExecution.step_run_id)
        .where(
            StepRun.execution_id.in_(identities),
        )
        .order_by(ToolExecution.id)
        .options(
            load_only(
                ToolExecution.id,
                ToolExecution.step_run_id,
                ToolExecution.version_id,
                ToolExecution.status,
                ToolExecution.dispatched,
                ToolExecution.attempts,
                ToolExecution.error_code,
            )
        )
    )
    return db.scalars(
        query.with_for_update(of=ToolExecution).execution_options(populate_existing=True)
        if lock
        else query
    ).all()


def blockers(db, run, *, lock=False):
    reasons = []
    if run.status not in {"failed", "cancelled"}:
        reasons.append("Only failed or cancelled executions can create a recovery run.")
    lineage = ancestors(db, run.id)
    if len(lineage) >= 100:
        reasons.append("Recovery lineage limit reached; create a new start with fresh approvals.")
    version = db.get(WorkflowVersion, run.version_id)
    if lock:
        db.scalar(
            select(WorkflowDefinition)
            .where(WorkflowDefinition.id == version.definition_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        version = db.scalar(
            select(WorkflowVersion)
            .where(WorkflowVersion.id == run.version_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
    try:
        require_runnable_version(db, version.definition_id, version.id)
    except HTTPException:
        reasons.append("The pinned version or its tool policy is unavailable or archived.")
    effects = effects_for(db, lineage, lock=lock)
    for effect in effects:
        if effect.status == "unknown" or (effect.status == "pending" and effect.dispatched):
            reasons.append(
                f"Effect {effect.id} has an uncertain outcome; record reconciliation first."
            )
        elif effect.status == "reconciled" and effect.error_code:
            reasons.append(
                f"Effect {effect.id} was confirmed failed; use a new start and fresh approval."
            )
        elif effect.status not in {"succeeded", "reconciled"}:
            contract = ToolContract.model_validate(db.get(ToolVersion, effect.version_id).contract)
            if effect.attempts >= contract.retry.max_attempts or (
                effect.status == "failed"
                and effect.error_code not in contract.retry.retryable_errors
            ):
                reasons.append(
                    f"Effect {effect.id} exhausted its retry policy; recovery cannot reset it."
                )
    graph = graph_for(db, run)
    nodes = {node.id: node for node in graph.nodes}
    for conversation, step in db.execute(
        select(LLMConversation, StepRun)
        .join(
            StepRun,
            StepRun.id == LLMConversation.step_run_id,
        )
        .where(StepRun.execution_id == run.id)
    ):
        if step.status == "completed":
            continue
        state, node = conversation.state, nodes[step.node_id]
        if state.get("error") or (
            "output" not in state
            and "response" not in state
            and (
                len(state["rounds"]) >= node.config.max_provider_rounds
                or sum(row.get("cost", row["reserved_cost"]) for row in state["rounds"])
                >= node.config.max_cost_usd
            )
        ):
            reasons.append(
                f"LLM step {step.id} has exhausted or rejected its continuation; use a new start."
            )
    return reasons, effects


def controls(db, identity):
    run = execution(db, identity)
    principal = current_principal(db)
    existing = db.scalar(select(ExecutionRecovery).where(ExecutionRecovery.source_id == identity))
    parent = db.scalar(
        select(ExecutionRecovery.source_id).where(ExecutionRecovery.execution_id == identity)
    )
    reasons, effects = blockers(db, run)
    now = runtime_now(db)
    jobs = db.scalars(
        select(DurableJob)
        .where(
            DurableJob.execution_id == identity,
            DurableJob.status.in_(["queued", "running"]),
        )
        .order_by(DurableJob.sequence)
        .limit(50)
    ).all()
    return {
        "id": run.id,
        "status": run.status,
        "state_revision": run.state_revision,
        "source_id": parent,
        "recovery_id": existing.execution_id if existing else None,
        "can_cancel": permits(principal, "workflow.control") and run.status not in TERMINAL,
        "can_recover": permits(principal, "workflow.control")
        and permits(principal, "workflow.start")
        and (bool(existing) or not reasons),
        "can_resolve": permits(principal, "tool.resolve"),
        "reasons": reasons
        if existing is None
        else ["A recovery already exists; repeated requests return that run."],
        "jobs": [
            {
                "id": job.id,
                "status": job.status,
                "due_at": job.due_at,
                "recovery_count": job.recovery_count,
                "max_recoveries": settings.worker_max_recoveries,
                "lease_expires_at": job.lease_expires_at,
                "can_retry": permits(principal, "workflow.control")
                and run.status not in TERMINAL
                and job.status == "running"
                and job.lease_expires_at is not None
                and job.lease_expires_at <= now,
                "note": "Existing retry budgets apply; exhaustion finalizes failure."
                if job.status == "running"
                else "Already scheduled; manual controls do not bypass its backoff.",
            }
            for job in jobs
        ],
        "effects": [
            {
                "id": effect.id,
                "status": effect.status,
                "error_code": effect.error_code,
                "needs_resolution": effect.status == "unknown"
                or (effect.status == "pending" and effect.dispatched),
            }
            for effect in effects
            if effect.status not in {"succeeded", "reconciled"}
        ],
    }


def recover(db, identity, reason):
    try:
        principal = authorize(db, "workflow.control", lock=True)
        authorize(db, "workflow.start", lock=True)
        source = db.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == identity)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if source is None:
            raise HTTPException(404, "Workflow execution not found")
        receipt = db.scalar(
            select(ExecutionRecovery).where(ExecutionRecovery.source_id == identity)
        )
        if receipt:
            result = execution(db, receipt.execution_id)
            db.commit()
            return result
        reasons, _ = blockers(db, source, lock=True)
        if reasons:
            raise HTTPException(409, {"reasons": reasons})
        graph = graph_for(db, source)
        # Approval outputs and every downstream checkpoint are reconsidered under
        # fresh approval. Other completed computation retains its exact provenance.
        excluded = {node.id for node in graph.nodes if node.type == "approval"}
        while True:
            following = excluded | {edge.target for edge in graph.edges if edge.source in excluded}
            if following == excluded:
                break
            excluded = following
        rows = db.scalars(select(StepRun).where(StepRun.execution_id == identity)).all()
        reusable = [
            row
            for row in rows
            if row.status in {"completed", "skipped"} and row.node_id not in excluded
        ]
        latest = {row.node_id for row in reusable}
        checkpoint = deepcopy(source.checkpoint_json)
        checkpoint["edges"] = {
            key: value
            for key, value in checkpoint.get("edges", {}).items()
            if graph.edges[int(key)].source in latest
        }
        checkpoint.pop("approval_retry", None)
        checkpoint.pop("parallel_approval_retries", None)
        for region in checkpoint.get("parallel_regions", {}).values():
            if region.get("join_node") not in latest:
                region["status"] = "forked"
        child = WorkflowExecution(
            version_id=source.version_id,
            input_json=deepcopy(source.input_json),
            runtime_config=deepcopy(source.runtime_config),
            created_by_user_id=principal.user_id,
            business_type=source.business_type,
            run_mode=source.run_mode,
            checkpoint_json=checkpoint,
            deadline_at=runtime_now(db) + timedelta(seconds=graph.overall_timeout_seconds),
        )
        db.add(child)
        db.flush()
        db.add(
            ExecutionRecovery(
                source_id=source.id,
                execution_id=child.id,
                actor_id=principal.user_id,
                reason=reason,
            )
        )
        db.flush()
        with workflow_transaction(db, child):
            transition(db, child, child, "running")
            for row in reusable:
                copied = add_step(
                    db,
                    child,
                    row.node_id,
                    branch=row.branch,
                    iteration=row.iteration,
                    inputs=deepcopy(row.input_json),
                )
                if row.status == "completed":
                    transition(db, child, copied, "running")
                    copied.output_json = deepcopy(row.output_json)
                transition(db, child, copied, row.status)
                db.add(
                    ExecutionEvent(
                        execution_id=child.id,
                        entity_type="step_runs",
                        entity_id=copied.id,
                        to_status=copied.status,
                        details={"reason": "reused_output", "source_step_id": str(row.id)},
                    )
                )
            from src.services.parallel_graph import has_parallel

            if has_parallel(graph) or graph.quality_revision:
                from src.services.parallel_runtime import schedule_parallel

                schedule_parallel(db, child)
            else:
                enqueue(db, child, 0)
            record_audit(
                db,
                principal,
                "workflow.recover",
                "workflow_execution",
                child.id,
                source_id=str(source.id),
                reason=reason,
            )
        return child
    except BaseException:
        db.rollback()
        raise


def retry_job(db, identity, job_id):
    from src.services.durable_queue import Claim
    from src.services.worker_leases import recover_claim

    principal = authorize(db, "workflow.control")
    execution(db, identity)
    job = db.scalar(
        select(DurableJob).where(DurableJob.id == job_id, DurableJob.execution_id == identity)
    )
    if job is None:
        raise HTTPException(404, "Job not found")
    claim = Claim(job.id, job.organization_id, identity, job.sequence, job.claim_token)
    if job.status != "running":
        raise HTTPException(409, "Job is not an expired active claim; refresh its current state")
    # Release the read session before the existing lease authority takes its fence.
    db.rollback()
    if not recover_claim(db.get_bind(), claim, operator=principal):
        raise HTTPException(409, "Claim is live or changed; refresh before retrying")
    return {"id": identity, "job_id": job_id, "recovered": True}
