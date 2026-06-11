from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.models.workflow_run import WorkflowRun, WorkflowStatus

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
    allowed = VALID_TRANSITIONS[run.status]
    if new_status not in allowed:
        raise InvalidTransitionError(run.status, new_status)
    run.status = new_status
    if new_status in _TERMINAL:
        run.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)
    return run
