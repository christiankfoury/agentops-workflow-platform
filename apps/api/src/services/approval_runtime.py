"""Version-bound approval snapshots and short, run-serialized human decisions."""

import hashlib
import json
import uuid
from copy import deepcopy
from datetime import timedelta

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.execution_approval import ExecutionApproval
from src.models.workflow_execution import ExecutionEvent, StepRun, WorkflowExecution
from src.schemas.execution_approval import ApprovalReview
from src.services.audit import record_audit
from src.services.execution_records import execution, pinned_node
from src.services.graph_expressions import ExecutionError
from src.services.graph_validation import validate_data
from src.services.permissions import authorize
from src.services.retry_runtime import expire_execution, runtime_now
from src.services.tenancy import bind_tenant
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def source_hash(run, step):
    return digest(
        [
            str(run.id),
            str(step.id),
            str(run.version_id),
            step.node_id,
            step.iteration,
            step.input_json,
        ]
    )


def new_approval(
    db, run, step, node, *, candidate=None, feedback=None, expires_at=None, identity=None
):
    try:
        inputs = step.input_json or {}
        payload = deepcopy(inputs["payload"] if candidate is None else candidate)
        review = ApprovalReview.model_validate(inputs["review"]).model_dump(mode="json")
        validate_data(payload, node.output_schema)
    except (KeyError, ValueError, TypeError) as error:
        raise ExecutionError(
            "approval_input_invalid", "Approval requires a valid payload and structured review"
        ) from error
    revision = (
        db.scalar(
            select(func.max(ExecutionApproval.revision)).where(
                ExecutionApproval.step_run_id == step.id,
            )
        )
        or 0
    ) + 1
    bound = source_hash(run, step)
    item = ExecutionApproval(
        id=identity or uuid.uuid4(),
        execution_id=run.id,
        step_run_id=step.id,
        version_id=run.version_id,
        node_id=step.node_id,
        iteration=step.iteration,
        revision=revision,
        source_hash=bound,
        payload_hash=digest([bound, payload, review, revision]),
        payload_json=payload,
        review_json=review,
        human_feedback=feedback,
        expires_at=expires_at,
    )
    db.add(item)
    db.flush()
    return item


def register_approval(db, run, step, attempt, node, now, retry=None):
    expiry = (
        now + timedelta(seconds=node.config.deadline_seconds)
        if node.config.deadline_seconds
        else None
    )
    item = new_approval(
        db,
        run,
        step,
        node,
        candidate=(retry or {}).get("payload"),
        feedback=(retry or {}).get("feedback"),
        expires_at=expiry,
    )
    step.waiting_reason = "approval"
    step.wake_at = expiry
    attempt.output_json = {"approval_id": str(item.id), "payload_hash": item.payload_hash}
    transition(db, run, attempt, "completed")
    transition(db, run, step, "waiting")
    if not run.checkpoint_json.get("parallel_mode"):
        transition(db, run, run, "waiting")
    db.add(
        ExecutionEvent(
            execution_id=run.id,
            entity_type="execution_approvals",
            entity_id=item.id,
            to_status="pending",
            details={"payload_hash": item.payload_hash},
        )
    )


def resolve(db, run, item, status, *, actor=None, feedback=None, request_hash=None):
    item.status = status
    item.resolved_at = runtime_now(db)
    item.decided_by_user_id = actor
    item.human_feedback = feedback if feedback is not None else item.human_feedback
    item.request_hash = request_hash
    db.add(
        ExecutionEvent(
            execution_id=run.id,
            entity_type="execution_approvals",
            entity_id=item.id,
            from_status="pending",
            to_status=status,
            details={"payload_hash": item.payload_hash},
        )
    )


def close_pending(db, run, status):
    for item in db.scalars(
        select(ExecutionApproval).where(
            ExecutionApproval.execution_id == run.id,
            ExecutionApproval.status == "pending",
        )
    ).all():
        resolve(db, run, item, status)


def queue_resume(db, run):
    from src.services.durable_queue import enqueue, jobs, settle_local_checkpoint

    if run.checkpoint_json.get("parallel_mode"):
        from src.services.parallel_runtime import schedule_parallel

        schedule_parallel(db, run)
        return
    settle_local_checkpoint(db, run)
    sequence = db.connection().scalar(
        select(func.max(jobs.c.sequence)).where(
            jobs.c.execution_id == run.id,
        )
    )
    enqueue(db, run, 0 if sequence is None else sequence + 1)


def terminate_wait(db, run, step, code, *, rejected=False):
    status = "cancelled" if rejected else "failed"
    step.error_code = run.error_code = code
    step.error_message = run.error_message = code.replace("_", " ")
    transition(db, run, step, status)
    if run.checkpoint_json.get("parallel_mode"):
        from src.services.durable_queue import terminate_jobs
        from src.services.parallel_runtime import cancel_siblings

        cancel_siblings(db, run)
        terminate_jobs(db, run, "cancelled", code)
    transition(db, run, run, status)


def expired(db, run, step, item, node, now):
    if run.deadline_at and now >= run.deadline_at:
        close_pending(db, run, "expired")
        expire_execution(db, run)
        from src.services.durable_queue import terminate_jobs

        terminate_jobs(db, run, "failed", "run_deadline")
        return True
    if item.expires_at and now >= item.expires_at:
        resolve(db, run, item, "expired")
        terminate_wait(
            db, run, step, "approval_expired", rejected=node.config.timeout_action == "reject"
        )
        return True
    return False


def decide_approval(db, identity, body):
    from src.services.graph_interpreter import graph_for, set_edges

    try:
        principal = authorize(db, "approval.decide", lock=True)
        item = db.scalar(select(ExecutionApproval).where(ExecutionApproval.id == identity))
        if item is None:
            raise HTTPException(404, "Execution approval not found")
        run = db.scalar(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.id == item.execution_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        db.refresh(item)
        step = db.scalar(
            select(StepRun)
            .where(
                StepRun.id == item.step_run_id,
                StepRun.execution_id == run.id,
            )
            .execution_options(populate_existing=True)
        )
        if step is None:
            raise HTTPException(409, "Approval step is no longer available")
        node = pinned_node(db, run, item.node_id)
        if principal.role not in node.config.reviewer_roles:
            raise HTTPException(403, "Reviewer role is not permitted by this approval")
        request_hash = digest(body.model_dump(mode="json"))
        if item.status != "pending":
            if item.request_hash == request_hash:
                db.commit()
                return item
            raise HTTPException(409, "Approval already resolved or superseded")
        if (
            run.status not in {"running", "waiting"}
            or step.status != "waiting"
            or run.cancel_requested
        ):
            raise HTTPException(409, "Execution is no longer awaiting this approval")
        if body.expected_payload_hash != item.payload_hash:
            raise HTTPException(409, "Reviewed payload changed; reload the approval")
        failure = None
        with workflow_transaction(db, run):
            if expired(db, run, step, item, node, runtime_now(db)):
                failure = "Approval expired"
            elif item.source_hash != source_hash(run, step):
                resolve(db, run, item, "invalidated")
                db.flush()
                try:
                    new_approval(db, run, step, node, expires_at=item.expires_at)
                except ExecutionError:
                    terminate_wait(db, run, step, "approval_input_invalid")
                failure = "Governed input changed; the stale approval was invalidated"
            else:
                high = any(
                    issue["severity"] in {"high", "critical"}
                    for issue in item.review_json["issues"]
                )
                if body.action == "approve" and high:
                    authorize(db, "approval.override", lock=True)
                from src.services.quality_revisions import human_retry_policy, restart

                graph = graph_for(db, run)
                quality_retry = body.action == "request_retry" and human_retry_policy(
                    run, graph, step
                )
                if (
                    body.action == "request_retry"
                    and not quality_retry
                    and step.iteration >= node.config.max_review_retries
                ):
                    raise HTTPException(
                        409, "Approval retry limit reached; approve or reject this review"
                    )
                if body.action == "edit":
                    try:
                        validate_data(body.edited_payload, node.output_schema)
                    except ValidationError as error:
                        raise HTTPException(
                            422, "Edited payload violates the pinned output schema"
                        ) from error
                    replacement_id = uuid.uuid4()
                    item.replacement_id = replacement_id
                    resolve(
                        db,
                        run,
                        item,
                        "superseded",
                        actor=principal.user_id,
                        feedback=body.human_feedback,
                        request_hash=request_hash,
                    )
                    db.flush()
                    new_approval(
                        db,
                        run,
                        step,
                        node,
                        candidate=body.edited_payload,
                        feedback=body.human_feedback,
                        expires_at=item.expires_at,
                        identity=replacement_id,
                    )
                else:
                    status = {
                        "approve": "approved",
                        "reject": "rejected",
                        "request_retry": "retry_requested",
                    }[body.action]
                    resolve(
                        db,
                        run,
                        item,
                        status,
                        actor=principal.user_id,
                        feedback=body.human_feedback,
                        request_hash=request_hash,
                    )
                    if body.action == "reject":
                        terminate_wait(db, run, step, "approval_rejected", rejected=True)
                    else:
                        step.output_json = (
                            deepcopy(item.payload_json) if body.action == "approve" else None
                        )
                        transition(db, run, step, "completed")
                        if quality_retry:
                            restart(
                                db,
                                run,
                                graph,
                                {
                                    "review": item.review_json,
                                    "human_feedback": body.human_feedback,
                                    "edited_payload": item.payload_json,
                                },
                                human=True,
                            )
                        elif body.action == "request_retry":
                            retry = {
                                "node_id": step.node_id,
                                "iteration": step.iteration + 1,
                                "payload": item.payload_json,
                                "feedback": body.human_feedback,
                            }
                            if run.checkpoint_json.get("parallel_mode"):
                                run.checkpoint_json = {
                                    **run.checkpoint_json,
                                    "parallel_approval_retries": {
                                        **run.checkpoint_json.get("parallel_approval_retries", {}),
                                        step.node_id: retry,
                                    },
                                }
                            else:
                                run.checkpoint_json = {
                                    **run.checkpoint_json,
                                    "approval_retry": retry,
                                }
                        else:
                            edges = dict(run.checkpoint_json.get("edges", {}))
                            for i, edge in enumerate(graph_for(db, run).edges):
                                if edge.source == step.node_id:
                                    edges[str(i)] = "selected"
                            set_edges(run, edges)
                        if run.status == "waiting":
                            transition(db, run, run, "running")
                        queue_resume(db, run)
                record_audit(
                    db,
                    principal,
                    f"approval.{body.action}",
                    "execution_approval",
                    item.id,
                    payload_hash=item.payload_hash,
                    high_severity_override=high and body.action == "approve",
                )
        if failure:
            raise HTTPException(409, failure)
        return item
    except BaseException:
        db.rollback()
        raise


def expire_approval_waits(engine, limit=32, *, now=None):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Approval expiry batch must be between 1 and 100")
    approvals, runs = ExecutionApproval.__table__, WorkflowExecution.__table__
    with engine.connect() as conn:
        moment = now or conn.scalar(select(func.clock_timestamp()))
        rows = conn.execute(
            select(approvals.c.id, approvals.c.organization_id, approvals.c.execution_id)
            .select_from(approvals.join(runs, approvals.c.execution_id == runs.c.id))
            .where(
                approvals.c.status == "pending",
                runs.c.status.in_(["running", "waiting"]),
                or_(
                    approvals.c.expires_at <= moment,
                    runs.c.deadline_at <= moment,
                ),
            )
            .order_by(approvals.c.expires_at, approvals.c.id)
            .limit(limit)
        ).all()
    count = 0
    for row in rows:
        with Session(engine) as db:
            bind_tenant(db, row.organization_id)
            run = execution(db, row.execution_id)
            try:
                with workflow_transaction(db, run):
                    item = db.get(ExecutionApproval, row.id)
                    if run.status not in {"running", "waiting"} or item.status != "pending":
                        raise StaleWorkflowError("Approval changed")
                    step = db.get(StepRun, item.step_run_id)
                    if not expired(
                        db,
                        run,
                        step,
                        item,
                        pinned_node(db, run, item.node_id),
                        now or runtime_now(db),
                    ):
                        raise StaleWorkflowError("Approval is not due")
                    count += 1
            except StaleWorkflowError:
                continue
    return count
