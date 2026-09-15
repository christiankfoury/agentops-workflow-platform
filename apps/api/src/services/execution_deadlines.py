"""Deadline watchdog: fence timed-out work without creating extra executor threads."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.workflow_execution import TERMINAL, StepAttempt, StepRun, WorkflowExecution
from src.services.durable_queue import Claim, commit_result, fail_queued_job, finish_job, jobs
from src.services.execution_records import execution, pinned_node
from src.services.graph_expressions import ExecutionError
from src.services.graph_interpreter import WorkItem
from src.services.retry_runtime import expire_execution, runtime_now
from src.services.tenancy import bind_tenant
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction


class NoDeadline(Exception):
    pass


def enforce_job_deadline(engine, identity, owner, execution_id, *, now=None):
    with Session(engine) as db:
        bind_tenant(db, owner)
        run = execution(db, execution_id)
        try:
            with workflow_transaction(db, run):
                row = (
                    db.connection()
                    .execute(
                        select(jobs)
                        .where(
                            jobs.c.id == identity,
                            jobs.c.organization_id == owner,
                            jobs.c.execution_id == run.id,
                            jobs.c.status.in_(["queued", "running"]),
                        )
                        .with_for_update()
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None or run.status in TERMINAL:
                    raise NoDeadline()
                now = now or runtime_now(db)
                claim = Claim(row["id"], owner, run.id, row["sequence"], row["claim_token"])
                if run.deadline_at and now >= run.deadline_at:
                    expire_execution(db, run)
                    if row["status"] == "queued":
                        fail_queued_job(db, run, row, "run_deadline")
                    else:
                        finish_job(db, run, claim, "failed", "run_deadline", allow_expired=True)
                    return True
                attempt = db.get(StepAttempt, row["attempt_id"]) if row["attempt_id"] else None
                if (
                    attempt is None
                    or attempt.status != "running"
                    or attempt.deadline_at is None
                    or now < attempt.deadline_at
                ):
                    raise NoDeadline()
                step = db.get(StepRun, attempt.step_run_id)
                work = WorkItem(
                    run.id,
                    step.id,
                    attempt.id,
                    run.state_revision,
                    pinned_node(db, run, step.node_id),
                    attempt.input_json,
                    ({}, {}),
                    attempt.deadline_at,
                )
                commit_result(
                    db,
                    claim,
                    work,
                    error=ExecutionError(
                        "attempt_timeout",
                        "Step attempt deadline expired",
                    ),
                    now=now,
                    allow_expired=True,
                )
            return True
        except (NoDeadline, StaleWorkflowError):
            return False


def enforce_deadlines(engine, limit=32, *, now=None):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Deadline batch must be between 1 and 100")
    runs, attempts = WorkflowExecution.__table__, StepAttempt.__table__
    with engine.connect() as conn:
        now = now or conn.scalar(select(func.clock_timestamp()))
        rows = conn.execute(
            select(jobs.c.id, jobs.c.organization_id, jobs.c.execution_id)
            .select_from(
                jobs.join(runs, jobs.c.execution_id == runs.c.id).outerjoin(
                    attempts,
                    jobs.c.attempt_id == attempts.c.id,
                )
            )
            .where(
                jobs.c.status.in_(["queued", "running"]),
                runs.c.status.not_in(TERMINAL),
                or_(
                    runs.c.deadline_at <= now,
                    attempts.c.deadline_at <= now,
                ),
            )
            .order_by(jobs.c.due_at, jobs.c.id)
            .limit(limit)
        ).all()
    return sum(
        enforce_job_deadline(engine, row.id, row.organization_id, row.execution_id, now=now)
        for row in rows
    )
