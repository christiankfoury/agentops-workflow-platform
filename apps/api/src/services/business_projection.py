"""Read compatibility projections, committed under the durable execution's lock.

The source execution owns control. Stable source IDs make projection retries
idempotent; these rows are never submitted to legacy agent execution.
"""

import uuid
from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.cost_event import CostEvent
from src.models.execution_approval import ExecutionApproval
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.models.workflow_execution import ExecutionEvent, StepAttempt, StepRun, WorkflowExecution
from src.models.workflow_run import WorkflowRun, WorkflowStatus


def execution_for(db, legacy_id):
    if not isinstance(db, Session):
        return None
    return db.scalar(select(WorkflowExecution).where(WorkflowExecution.legacy_run_id == legacy_id))


def sync(db, source):
    if source.legacy_run_id is None:
        return
    db.flush()
    run = db.get(WorkflowRun, source.legacy_run_id)
    if run is None:
        raise ValueError("Durable execution lost its business projection")
    rows = db.scalars(
        select(StepRun)
        .where(StepRun.execution_id == source.id)
        .order_by(StepRun.created_at, StepRun.id)
    ).all()
    llm_rows = [row for row in rows if row.step_type == "llm"]
    all_usage = []
    for order, row in enumerate(llm_rows, 1):
        projected = db.get(AgentStep, row.id)
        if projected is None:
            projected = AgentStep(
                id=row.id,
                workflow_run_id=run.id,
                agent_name=row.node_id.replace("_", " ").title() + " Agent",
                agent_type=row.node_id,
                step_order=order,
            )
            db.add(projected)
        attempts = db.scalars(
            select(StepAttempt)
            .where(StepAttempt.step_run_id == row.id)
            .order_by(StepAttempt.number)
        ).all()
        usage = [attempt.llm_metadata for attempt in attempts if attempt.llm_metadata]
        all_usage.extend(usage)
        projected.status = AgentStepStatus(
            {
                "pending": "pending",
                "completed": "completed",
                "failed": "failed",
                "cancelled": "failed",
                "skipped": "failed",
            }.get(row.status, "running")
        )
        projected.input_json, projected.output_json = (
            deepcopy(row.input_json),
            deepcopy(row.output_json),
        )
        projected.error_message = row.error_message
        projected.retry_count = row.iteration
        projected.created_at, projected.completed_at = row.created_at, row.completed_at
        config = source.runtime_config.get(row.node_id, {})
        projected.model = config.get("model")
        projected.prompt_version_id = uuid.UUID(config["prompt_version_id"]) if config else None
        projected.tokens_input = sum(item["input_tokens"] for item in usage) if usage else None
        projected.tokens_output = sum(item["output_tokens"] for item in usage) if usage else None
        projected.total_tokens = sum(item["total_tokens"] for item in usage) if usage else None
        projected.latency_ms = sum(item["latency_ms"] for item in usage) if usage else None
        projected.cost = total_cost(usage)
        db.flush()
        for attempt in attempts:
            item = attempt.llm_metadata
            identity = uuid.uuid5(attempt.id, "compatibility-cost")
            if not item or item["estimated_cost_usd"] is None or db.get(CostEvent, identity):
                continue
            pricing = item["pricing"]
            db.add(
                CostEvent(
                    id=identity,
                    workflow_run_id=run.id,
                    agent_step_id=projected.id,
                    model=item["model"],
                    tokens_input=item["input_tokens"],
                    tokens_output=item["output_tokens"],
                    total_tokens=item["total_tokens"],
                    cost_input=item["input_tokens"] * pricing["input_per_million"] / 1_000_000,
                    cost_output=item["output_tokens"] * pricing["output_per_million"] / 1_000_000,
                    total_cost=item["estimated_cost_usd"],
                )
            )
    for approval in db.scalars(
        select(ExecutionApproval).where(ExecutionApproval.execution_id == source.id)
    ):
        projected = db.get(HumanApproval, approval.id)
        if projected is None:
            projected = HumanApproval(id=approval.id, workflow_run_id=run.id)
            db.add(projected)
        projected.status = ApprovalStatus(approval.status)
        projected.reviewer_score = approval.review_json.get("quality_score")
        projected.issues_json = deepcopy(approval.review_json.get("issues", []))
        original = next(row for row in rows if row.id == approval.step_run_id)
        projected.edited_analysis_json = (
            deepcopy(approval.payload_json)
            if approval.payload_json != original.input_json.get("payload")
            else None
        )
        projected.human_feedback = approval.human_feedback
        projected.approved_by_user_id = approval.decided_by_user_id
        projected.created_at, projected.resolved_at = approval.created_at, approval.resolved_at
    run.status = WorkflowStatus(
        {"pending": "created", "waiting": "waiting_for_human", "retrying": "retrying"}.get(
            source.status, source.status
        )
    )
    run.final_output = (source.output_json or {}).get("final_output")
    history = source.checkpoint_json.get("quality", {}).get("history", [])
    run.quality_score = history[-1]["review"]["quality_score"] if history else None
    run.retry_count = source.checkpoint_json.get("quality", {}).get("iteration", 0)
    run.total_tokens = sum(item["total_tokens"] for item in all_usage) if all_usage else None
    run.total_cost = total_cost(all_usage)
    run.latency_ms = sum(item["latency_ms"] for item in all_usage) if all_usage else None
    run.completed_at = source.completed_at
    run.state_revision = source.state_revision + 1
    for event in db.scalars(select(ExecutionEvent).where(ExecutionEvent.execution_id == source.id)):
        if db.get(WorkflowEvent, event.id):
            continue
        kind = WorkflowEventType.state_transition
        if (
            event.entity_type == "workflow_executions"
            and event.from_status is None
            and event.to_status == "pending"
        ):
            kind = WorkflowEventType.workflow_started
        if event.entity_type == "workflow_executions" and event.to_status in {
            "completed",
            "failed",
            "cancelled",
        }:
            kind = WorkflowEventType(f"workflow_{event.to_status}")
        db.add(
            WorkflowEvent(
                id=event.id,
                workflow_run_id=run.id,
                event_type=kind,
                message=f"{event.entity_type}: {event.to_status}",
                created_at=event.created_at,
                metadata_json={
                    "execution_id": str(source.id),
                    "entity_id": str(event.entity_id),
                    **deepcopy(event.details),
                },
            )
        )


def total_cost(usage):
    if not usage or any(item["estimated_cost_usd"] is None for item in usage):
        return None
    return sum(item["estimated_cost_usd"] for item in usage)
