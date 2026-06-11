import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import WorkflowRun, WorkflowStatus
from src.services.human_feedback import get_edited_fields
from src.services.workflow_events import log_workflow_event
from src.services.workflow_state import transition


class HumanApprovalError(Exception):
    pass


def create_pending_human_approval(db: Session, run: WorkflowRun) -> HumanApproval:
    if run.status != WorkflowStatus.waiting_for_human:
        raise HumanApprovalError("Workflow run must be waiting for human approval")

    existing = _get_pending_approval_for_run(db, run.id)
    if existing is not None:
        return existing

    reviewer_output = _get_latest_reviewer_output(db, run.id)
    approval = HumanApproval(
        workflow_run_id=run.id,
        reviewer_score=_safe_float(reviewer_output.get("quality_score")),
        issues_json=reviewer_output.get("issues", []),
        status=ApprovalStatus.pending,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    log_workflow_event(
        db,
        run,
        WorkflowEventType.human_approval_required,
        "Human approval required.",
        metadata={
            "human_approval_id": approval.id,
            "reviewer_score": approval.reviewer_score,
            "issue_count": len(approval.issues_json or []),
        },
    )
    return approval


def approve_human_approval(
    db: Session,
    approval: HumanApproval,
    human_feedback: str | None = None,
    approved_by_user_id: uuid.UUID | None = None,
) -> HumanApproval:
    run = _get_run(db, approval.workflow_run_id)
    _ensure_pending(approval)
    _ensure_waiting_for_human(run)
    approval.status = ApprovalStatus.approved
    approval.human_feedback = _coalesce_feedback(human_feedback, approval.human_feedback)
    approval.approved_by_user_id = approved_by_user_id
    approval.resolved_at = datetime.now(UTC)
    transition(run, WorkflowStatus.writer_running, db)
    log_workflow_event(
        db,
        run,
        WorkflowEventType.human_approved,
        "Human approved workflow output.",
        metadata={
            "human_approval_id": approval.id,
            "approved_by_user_id": approved_by_user_id,
            "has_feedback": bool(approval.human_feedback),
            "has_edited_analysis": approval.edited_analysis_json is not None,
        },
    )
    db.refresh(approval)
    return approval


def request_human_approval_retry(
    db: Session,
    approval: HumanApproval,
    human_feedback: str | None = None,
    approved_by_user_id: uuid.UUID | None = None,
) -> HumanApproval:
    run = _get_run(db, approval.workflow_run_id)
    _ensure_pending(approval)
    _ensure_waiting_for_human(run)
    approval.status = ApprovalStatus.retry_requested
    approval.human_feedback = _coalesce_feedback(human_feedback, approval.human_feedback)
    approval.approved_by_user_id = approved_by_user_id
    approval.resolved_at = datetime.now(UTC)
    transition(run, WorkflowStatus.retrying, db)
    log_workflow_event(
        db,
        run,
        WorkflowEventType.human_requested_retry,
        "Human requested workflow retry.",
        metadata={
            "human_approval_id": approval.id,
            "approved_by_user_id": approved_by_user_id,
            "has_feedback": bool(approval.human_feedback),
        },
    )
    db.refresh(approval)
    return approval


def reject_human_approval(
    db: Session,
    approval: HumanApproval,
    human_feedback: str | None = None,
    approved_by_user_id: uuid.UUID | None = None,
) -> HumanApproval:
    run = _get_run(db, approval.workflow_run_id)
    _ensure_pending(approval)
    _ensure_waiting_for_human(run)
    approval.status = ApprovalStatus.rejected
    approval.human_feedback = _coalesce_feedback(human_feedback, approval.human_feedback)
    approval.approved_by_user_id = approved_by_user_id
    approval.resolved_at = datetime.now(UTC)
    transition(run, WorkflowStatus.cancelled, db)
    log_workflow_event(
        db,
        run,
        WorkflowEventType.human_rejected,
        "Human rejected workflow output.",
        metadata={
            "human_approval_id": approval.id,
            "approved_by_user_id": approved_by_user_id,
            "has_feedback": bool(approval.human_feedback),
        },
    )
    db.refresh(approval)
    return approval


def edit_human_approval(
    db: Session,
    approval: HumanApproval,
    human_feedback: str | None = None,
    edited_analysis_json: dict[str, Any] | None = None,
) -> HumanApproval:
    run = _get_run(db, approval.workflow_run_id)
    _ensure_pending(approval)
    _ensure_waiting_for_human(run)
    if human_feedback is not None:
        approval.human_feedback = human_feedback
    if edited_analysis_json is not None:
        approval.edited_analysis_json = edited_analysis_json
    db.commit()
    db.refresh(approval)
    log_workflow_event(
        db,
        run,
        WorkflowEventType.human_edited_analysis,
        "Human edited structured analysis.",
        metadata={
            "human_approval_id": approval.id,
            "has_feedback": bool(approval.human_feedback),
            "edited_fields": get_edited_fields(approval.edited_analysis_json),
            "reviewer_issue_count": len(approval.issues_json or []),
        },
    )
    return approval


def _get_pending_approval_for_run(db: Session, run_id: uuid.UUID) -> HumanApproval | None:
    return (
        db.query(HumanApproval)
        .filter(
            HumanApproval.workflow_run_id == run_id,
            HumanApproval.status == ApprovalStatus.pending,
        )
        .first()
    )


def _get_latest_reviewer_output(db: Session, run_id: uuid.UUID) -> dict[str, Any]:
    reviewer_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == AgentType.reviewer.value,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    if not reviewer_steps:
        raise HumanApprovalError("Completed reviewer step not found")
    latest_review = max(reviewer_steps, key=lambda step: step.step_order)
    if latest_review.output_json is None:
        raise HumanApprovalError("Completed reviewer step has no output")
    return latest_review.output_json


def _get_run(db: Session, run_id: uuid.UUID) -> WorkflowRun:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HumanApprovalError("Workflow run not found")
    return run


def _ensure_pending(approval: HumanApproval) -> None:
    if approval.status != ApprovalStatus.pending:
        raise HumanApprovalError("Human approval is already resolved")


def _ensure_waiting_for_human(run: WorkflowRun) -> None:
    if run.status != WorkflowStatus.waiting_for_human:
        raise HumanApprovalError("Workflow run is not waiting for human approval")


def _coalesce_feedback(new_feedback: str | None, current_feedback: str | None) -> str | None:
    return new_feedback if new_feedback is not None else current_feedback


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
