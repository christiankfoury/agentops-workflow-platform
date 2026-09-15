"""Persist cancellation and stop all runnable work in one authorized transaction."""

from fastapi import HTTPException
from sqlalchemy import select, update

from src.models.workflow_execution import (
    TERMINAL,
    ExecutionEvent,
    StepAttempt,
    StepRun,
    WorkflowExecution,
)
from src.services.audit import record_audit
from src.services.durable_queue import jobs
from src.services.permissions import authorize
from src.services.retry_runtime import runtime_now
from src.services.tenancy import tenant_id
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import workflow_transaction


def cancel_execution(db, identity, reason=None):
    try:
        principal = authorize(db, "workflow.control", lock=True)
        run = db.scalar(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.id == identity,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if run is None:
            raise HTTPException(404, "Workflow execution not found")
        if run.status in TERMINAL:
            db.commit()
            return run
        with workflow_transaction(db, run):
            from src.services.approval_runtime import close_pending

            close_pending(db, run, "cancelled")
            run.cancel_requested = True
            run.cancel_requested_at = runtime_now(db)
            run.cancel_requested_by_user_id = principal.user_id
            run.cancel_reason = reason
            for step in db.scalars(
                select(StepRun).where(
                    StepRun.execution_id == run.id,
                    StepRun.status.not_in(TERMINAL),
                )
            ).all():
                for attempt in db.scalars(
                    select(StepAttempt).where(
                        StepAttempt.step_run_id == step.id,
                        StepAttempt.status.not_in(TERMINAL),
                    )
                ).all():
                    attempt.error_code = "cancelled"
                    attempt.error_message = "Execution cancellation requested"
                    transition(db, run, attempt, "cancelled")
                step.next_attempt_at = None
                step.error_code = "cancelled"
                step.error_message = "Execution cancellation requested"
                transition(db, run, step, "cancelled")
            rows = (
                db.connection()
                .execute(
                    select(jobs)
                    .where(
                        jobs.c.execution_id == run.id,
                        jobs.c.organization_id == tenant_id(db),
                        jobs.c.status.in_(["queued", "running"]),
                    )
                    .with_for_update()
                )
                .mappings()
                .all()
            )
            for row in rows:
                db.connection().execute(
                    update(jobs)
                    .where(jobs.c.id == row["id"])
                    .values(
                        status="cancelled",
                        completed_at=runtime_now(db),
                        error_code="cancelled",
                    )
                )
                db.add(
                    ExecutionEvent(
                        execution_id=run.id,
                        entity_type="durable_jobs",
                        entity_id=row["id"],
                        from_status=row["status"],
                        to_status="cancelled",
                        details={"reason": "cancel_requested"},
                    )
                )
            run.error_code = "cancelled"
            run.error_message = "Execution cancellation requested"
            transition(db, run, run, "cancelled")
            record_audit(
                db, principal, "workflow.cancel", "workflow_execution", run.id, reason=reason
            )
        return run
    except BaseException:
        db.rollback()
        raise
