from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import WorkflowRun, WorkflowStatus
from src.services.workflow_events import log_workflow_event
from src.services.workflow_state import transition

CANCELLED_STEP_MESSAGE = "Workflow was cancelled before this step completed."


def cancel_workflow_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    _mark_running_steps_failed(db, run)
    cancelled = transition(run, WorkflowStatus.cancelled, db)
    log_workflow_event(
        db,
        cancelled,
        WorkflowEventType.workflow_cancelled,
        "Workflow run cancelled.",
        metadata={"status": cancelled.status.value},
    )
    return cancelled


def _mark_running_steps_failed(db: Session, run: WorkflowRun) -> None:
    running_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run.id,
            AgentStep.status == AgentStepStatus.running,
        )
        .all()
    )
    if not running_steps:
        return
    for step in running_steps:
        step.status = AgentStepStatus.failed
        step.error_message = CANCELLED_STEP_MESSAGE
        step.completed_at = datetime.now(UTC)
    db.commit()
