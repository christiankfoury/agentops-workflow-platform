"""Renew live ownership and recover expired checkpoints through the run fence."""

from contextlib import contextmanager
from datetime import timedelta
from threading import Event, Thread
from time import monotonic

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from src.config import settings
from src.models.workflow_execution import (
    TERMINAL,
    ExecutionEvent,
    StepAttempt,
    StepRun,
    WorkflowExecution,
)
from src.services.durable_queue import Claim, finish_job, jobs, locked_claim, terminal_job_status
from src.services.execution_records import execution, pinned_node
from src.services.retry_runtime import retry_decision, runtime_now
from src.services.tenancy import bind_tenant
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction


def renew_lease(engine, claim):
    with engine.begin() as conn:
        result = conn.execute(
            update(jobs)
            .where(
                jobs.c.id == claim.id,
                jobs.c.organization_id == claim.organization_id,
                jobs.c.execution_id == claim.execution_id,
                jobs.c.claim_token == claim.token,
                jobs.c.status == "running",
                jobs.c.lease_expires_at > func.clock_timestamp(),
            )
            .values(
                heartbeat_at=func.clock_timestamp(),
                lease_expires_at=func.clock_timestamp()
                + timedelta(
                    seconds=settings.worker_lease_seconds,
                ),
            )
        )
        return result.rowcount == 1


@contextmanager
def maintain_lease(engine, claim, control=None):
    stop = Event()

    def is_live():
        with engine.connect() as conn:
            runs = WorkflowExecution.__table__
            return (
                conn.execute(
                    select(jobs.c.id)
                    .select_from(jobs.join(runs, jobs.c.execution_id == runs.c.id))
                    .where(
                        jobs.c.id == claim.id,
                        jobs.c.organization_id == claim.organization_id,
                        jobs.c.claim_token == claim.token,
                        jobs.c.status == "running",
                        runs.c.status.not_in(TERMINAL),
                        runs.c.cancel_requested.is_(False),
                        jobs.c.lease_expires_at > func.clock_timestamp(),
                    )
                ).first()
                is not None
            )

    # A committed cancel between preparation and dispatch must suppress I/O immediately.
    # Read failure propagates before invocation; lease recovery retains the checkpoint.
    if not is_live() and control:
        control.abort()

    def heartbeat():
        last_renewal = monotonic()
        interval = min(settings.worker_control_poll_seconds, settings.worker_heartbeat_seconds)
        while not stop.wait(interval):
            try:
                if not is_live():
                    if control:
                        control.abort()
                    return
                if monotonic() - last_renewal >= settings.worker_heartbeat_seconds:
                    if not renew_lease(engine, claim):
                        if control:
                            control.abort()
                        return
                    last_renewal = monotonic()
            except Exception:
                # Retry transient reads, but never assume ownership beyond an unrenewed lease.
                if monotonic() - last_renewal >= settings.worker_lease_seconds:
                    if control:
                        control.abort()
                    return

    thread = Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5)


class NoRecovery(Exception):
    pass


def recover_claim(engine, claim):
    with Session(engine) as db:
        bind_tenant(db, claim.organization_id)
        run = execution(db, claim.execution_id)
        try:
            with workflow_transaction(db, run):
                row = locked_claim(db, claim, allow_expired=True)
                if row is None or row["lease_expires_at"] > db.scalar(
                    select(func.clock_timestamp())
                ):
                    raise NoRecovery()
                if run.status in TERMINAL:
                    finish_job(
                        db,
                        run,
                        claim,
                        terminal_job_status(run.status),
                        run.error_code,
                        allow_expired=True,
                    )
                    return True
                now = runtime_now(db)
                retry = row["recovery_count"] < settings.worker_max_recoveries
                exhausted_code = "recovery_exhausted"
                next_due = now
                if run.deadline_at and now >= run.deadline_at:
                    retry = False
                    exhausted_code = "run_deadline"
                active = db.scalars(
                    select(StepRun).where(
                        StepRun.execution_id == run.id,
                        StepRun.status.not_in(TERMINAL),
                    )
                ).all()
                for step in active:
                    attempts = db.scalars(
                        select(StepAttempt)
                        .where(
                            StepAttempt.step_run_id == step.id,
                        )
                        .order_by(StepAttempt.number)
                    ).all()
                    for attempt in attempts:
                        if attempt.status not in TERMINAL:
                            attempt.error_classification = "retryable"
                            attempt.error_code = "worker_abandoned"
                            attempt.error_message = "Worker lease expired before completion"
                            transition(db, run, attempt, "failed")
                    _, due, code = retry_decision(
                        pinned_node(db, run, step.node_id).retry,
                        len(attempts),
                        "worker_abandoned",
                        now,
                        run.deadline_at,
                        abandoned=True,
                    )
                    retry = retry and due is not None and step.status in {"running", "retrying"}
                    if code == "run_deadline":
                        exhausted_code = code
                    if due is not None:
                        next_due = max(next_due, due)
                for step in active:
                    if retry:
                        step.next_attempt_at = next_due
                        if step.status == "running":
                            transition(db, run, step, "retrying")
                    else:
                        step.next_attempt_at = None
                        step.error_code = exhausted_code
                        step.error_message = "Worker recovery or pinned attempt budget exhausted"
                        transition(db, run, step, "failed")
                if not retry:
                    run.error_code = exhausted_code
                    run.error_message = "Worker recovery or pinned attempt budget exhausted"
                    transition(db, run, run, "failed")
                    finish_job(db, run, claim, "failed", run.error_code, allow_expired=True)
                    return True
                db.connection().execute(
                    update(jobs)
                    .where(jobs.c.id == claim.id)
                    .values(
                        status="queued",
                        claim_token=None,
                        worker_id=None,
                        claimed_at=None,
                        dispatched_at=None,
                        attempt_id=None,
                        lease_expires_at=None,
                        heartbeat_at=None,
                        recovery_count=row["recovery_count"] + 1,
                        due_at=next_due,
                    )
                )
                db.add(
                    ExecutionEvent(
                        execution_id=run.id,
                        entity_type="durable_jobs",
                        entity_id=claim.id,
                        from_status="running",
                        to_status="queued",
                        details={
                            "reason": "lease_expired",
                            "recovery_count": row["recovery_count"] + 1,
                            "abandoned_attempt_id": str(row["attempt_id"])
                            if row["attempt_id"]
                            else None,
                        },
                    )
                )
            return True
        except (NoRecovery, StaleWorkflowError):
            return False


def recover_expired(engine, limit=32):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Recovery batch must be between 1 and 100")
    with engine.connect() as conn:
        rows = (
            conn.execute(
                select(jobs)
                .where(
                    jobs.c.status == "running",
                    jobs.c.lease_expires_at <= func.clock_timestamp(),
                )
                .order_by(jobs.c.lease_expires_at, jobs.c.id)
                .limit(limit)
            )
            .mappings()
            .all()
        )
    # Do not lock jobs before executions: dispatch and completion use the same lock order.
    return sum(
        recover_claim(
            engine,
            Claim(
                row["id"],
                row["organization_id"],
                row["execution_id"],
                row["sequence"],
                row["claim_token"],
            ),
        )
        for row in rows
    )
