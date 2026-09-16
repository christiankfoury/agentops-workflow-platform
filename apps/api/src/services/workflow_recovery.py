from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import WorkflowRun, WorkflowStatus
from src.services.audit import record_audit
from src.services.permissions import authorize
from src.services.workflow_events import log_workflow_event
from src.services.workflow_state import transition, transition_step
from src.services.workflow_transactions import commit_workflow, workflow_transaction

CANCELLED_STEP_MESSAGE = "Workflow was cancelled before this step completed."


def cancel_workflow_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    from src.services.business_projection import execution_for
    from src.services.execution_cancellation import cancel_execution

    execution = execution_for(db, run.id)
    if execution is not None:
        cancel_execution(db, execution.id)
        db.refresh(run)
        return run
    with workflow_transaction(db, run):
        principal = authorize(db, "workflow.control", lock=True)
        record_audit(db, principal, "workflow.cancel", "workflow_run", run.id)
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
        transition_step(step, AgentStepStatus.failed)
        step.error_message = CANCELLED_STEP_MESSAGE
        step.completed_at = datetime.now(UTC)
    commit_workflow(db)
