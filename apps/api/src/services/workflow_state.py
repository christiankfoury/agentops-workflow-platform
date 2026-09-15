from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.models.workflow_run import WorkflowRun, WorkflowStatus
from src.observability.platform_telemetry import emit_workflow_summary_telemetry
from src.services.workflow_transactions import (
    after_workflow_commit,
    commit_workflow,
    workflow_transaction,
)

VALID_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
    WorkflowStatus.created: {
        WorkflowStatus.running,
        WorkflowStatus.cancelled,
    },
    WorkflowStatus.running: {
        WorkflowStatus.routing,
        WorkflowStatus.analyst_running,
        WorkflowStatus.completed,
        WorkflowStatus.failed,
        WorkflowStatus.cancelled,
    },
    WorkflowStatus.routing: {
        WorkflowStatus.analyst_running,
        WorkflowStatus.failed,
        WorkflowStatus.cancelled,
    },
    WorkflowStatus.analyst_running: {
        WorkflowStatus.reviewer_running,
        WorkflowStatus.retrying,
        WorkflowStatus.failed,
        WorkflowStatus.cancelled,
    },
    WorkflowStatus.reviewer_running: {
        WorkflowStatus.waiting_for_human,
        WorkflowStatus.writer_running,
        WorkflowStatus.retrying,
        WorkflowStatus.failed,
        WorkflowStatus.cancelled,
    },
    WorkflowStatus.retrying: {
        WorkflowStatus.analyst_running,
        WorkflowStatus.failed,
        WorkflowStatus.cancelled,
    },
    WorkflowStatus.waiting_for_human: {
        WorkflowStatus.writer_running,
        WorkflowStatus.analyst_running,
        WorkflowStatus.retrying,
        WorkflowStatus.cancelled,
    },
    WorkflowStatus.writer_running: {
        WorkflowStatus.completed,
        WorkflowStatus.failed,
        WorkflowStatus.cancelled,
    },
    WorkflowStatus.completed: set(),
    WorkflowStatus.failed: set(),
    WorkflowStatus.cancelled: set(),
}

_TERMINAL = {WorkflowStatus.completed, WorkflowStatus.failed, WorkflowStatus.cancelled}


class InvalidTransitionError(Exception):
    def __init__(self, from_status: WorkflowStatus, to_status: WorkflowStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        allowed = sorted(s.value for s in VALID_TRANSITIONS[from_status]) or ["none (terminal)"]
        super().__init__(
            f"Cannot transition from '{from_status}' to '{to_status}'. "
            f"Allowed next states: {allowed}"
        )


def transition(run: WorkflowRun, new_status: WorkflowStatus, db: Session) -> WorkflowRun:
    with workflow_transaction(db, run):
        old_status = run.status
        if new_status not in VALID_TRANSITIONS[old_status]:
            raise InvalidTransitionError(old_status, new_status)
        run.status = new_status
        if new_status in _TERMINAL:
            run.completed_at = datetime.now(UTC)
        if hasattr(db, "add"):
            db.add(WorkflowEvent(
                workflow_run_id=run.id,
                event_type=WorkflowEventType.state_transition,
                message=f"Workflow transitioned from {old_status} to {new_status}.",
                metadata_json={"from_status": old_status.value, "to_status": new_status.value},
            ))
        commit_workflow(db)
        db.refresh(run)
        if new_status in _TERMINAL:
            after_workflow_commit(db, lambda: emit_workflow_summary_telemetry(run))
    return run


def transition_step(step: AgentStep, new_status: AgentStepStatus) -> None:
    """Mutate a step only inside its caller-owned workflow transaction."""
    allowed = {
        AgentStepStatus.pending: {AgentStepStatus.running, AgentStepStatus.failed},
        AgentStepStatus.running: {AgentStepStatus.completed, AgentStepStatus.failed},
        AgentStepStatus.completed: set(),
        AgentStepStatus.failed: set(),
    }
    if new_status not in allowed[step.status]:
        raise ValueError(f"Cannot transition step from {step.status} to {new_status}")
    step.status = new_status
    if new_status in {AgentStepStatus.completed, AgentStepStatus.failed}:
        step.completed_at = datetime.now(UTC)
