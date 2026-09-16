"""Trusted worker queue authority. Global claims use Core; execution work is scoped."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.config import settings
from src.models.durable_job import DurableJob
from src.models.workflow_execution import TERMINAL, ExecutionEvent, StepRun, WorkflowExecution
from src.services.execution_records import execution
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.graph_expressions import ExecutionError
from src.services.graph_interpreter import complete_work, execute_work, prepare_next
from src.services.tenancy import bind_tenant, tenant_id
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction

jobs = DurableJob.__table__


def has_queued_jobs(engine):
    with engine.connect() as conn:
        return (
            conn.execute(select(jobs.c.id).where(jobs.c.status == "queued").limit(1)).first()
            is not None
        )


class LeaseLostError(StaleWorkflowError):
    pass


@dataclass(frozen=True)
class Claim:
    id: UUID
    organization_id: UUID
    execution_id: UUID
    sequence: int
    token: UUID


def enqueue(db, run, sequence, *, due_at=None, node_id=None, iteration=0, branch="main"):
    job = DurableJob(
        execution_id=run.id, sequence=sequence, node_id=node_id, iteration=iteration, branch=branch
    )
    if due_at is not None:
        job.due_at = due_at
    db.add(job)
    db.flush()
    db.add(
        ExecutionEvent(
            execution_id=run.id,
            entity_type="durable_jobs",
            entity_id=job.id,
            to_status="queued",
            details={"sequence": sequence},
        )
    )
    return job


def claim_jobs(engine, worker_id, capacity=1):
    if type(capacity) is not int or not 1 <= capacity <= 32:
        raise ValueError("Claim capacity must be between 1 and 32")
    if not worker_id or len(worker_id) > 128:
        raise ValueError("Worker identity must be between 1 and 128 characters")
    claimed = []
    runs = WorkflowExecution.__table__
    # Trusted infrastructure. Lock executions first, matching cancellation/completion.
    with engine.begin() as conn:
        due = conn.execute(
            select(
                jobs,
                runs.c.status.label("run_status"),
                runs.c.cancel_requested,
                runs.c.error_code.label("run_error"),
            )
            .select_from(jobs.join(runs, jobs.c.execution_id == runs.c.id))
            .where(
                jobs.c.status == "queued",
                jobs.c.due_at <= func.now(),
            )
            .order_by(jobs.c.due_at, jobs.c.id)
            .limit(capacity)
            .with_for_update(of=runs, skip_locked=True)
        )
        for row in due.mappings().all():
            ready = conn.execute(
                select(jobs.c.id)
                .where(
                    jobs.c.id == row["id"],
                    jobs.c.status == "queued",
                    jobs.c.due_at <= func.now(),
                )
                .with_for_update(skip_locked=True)
            ).first()
            if ready is None:
                continue
            if row["run_status"] in TERMINAL or row["cancel_requested"]:
                status = (
                    "cancelled"
                    if row["cancel_requested"]
                    else terminal_job_status(row["run_status"])
                )
                code = None if status == "completed" else row["run_error"] or status
                conn.execute(
                    update(jobs)
                    .where(jobs.c.id == row["id"])
                    .values(
                        status=status,
                        error_code=code,
                        completed_at=func.clock_timestamp(),
                    )
                )
                conn.execute(
                    insert(ExecutionEvent.__table__).values(
                        organization_id=row["organization_id"],
                        execution_id=row["execution_id"],
                        entity_type="durable_jobs",
                        entity_id=row["id"],
                        from_status="queued",
                        to_status=status,
                        details={"reason": "terminal_execution"},
                    )
                )
                continue
            token = uuid4()
            conn.execute(
                update(jobs)
                .where(jobs.c.id == row["id"])
                .values(
                    status="running",
                    claim_token=token,
                    worker_id=worker_id,
                    claimed_at=func.now(),
                    heartbeat_at=func.clock_timestamp(),
                    lease_expires_at=func.clock_timestamp()
                    + timedelta(
                        seconds=settings.worker_lease_seconds,
                    ),
                )
            )
            conn.execute(
                insert(ExecutionEvent.__table__).values(
                    organization_id=row["organization_id"],
                    execution_id=row["execution_id"],
                    entity_type="durable_jobs",
                    entity_id=row["id"],
                    from_status="queued",
                    to_status="running",
                    details={"worker_id": worker_id},
                )
            )
            claimed.append(
                Claim(
                    row["id"], row["organization_id"], row["execution_id"], row["sequence"], token
                )
            )
    return claimed


def locked_claim(db, claim, *, allow_expired=False):
    if tenant_id(db) != claim.organization_id:
        raise ValueError("Claim does not belong to the worker session organization")
    row = (
        db.connection()
        .execute(
            select(jobs)
            .where(
                jobs.c.id == claim.id,
                jobs.c.organization_id == claim.organization_id,
                jobs.c.execution_id == claim.execution_id,
                jobs.c.claim_token == claim.token,
                jobs.c.sequence == claim.sequence,
                jobs.c.status == "running",
                True if allow_expired else jobs.c.lease_expires_at > func.clock_timestamp(),
            )
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    return row


def terminal_job_status(status):
    return status if status in {"completed", "cancelled"} else "failed"


def settle_local_checkpoint(db, run):
    """Consume an undispatched receipt when local preparation already reached a wait."""
    if db.info.get("workflow_transaction") != (WorkflowExecution, run.id):
        raise ValueError("Receipt settlement requires its execution transaction")
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
        if row["attempt_id"] is not None or row["dispatched_at"] is not None:
            raise StaleWorkflowError("Wait registration job is still dispatched")
        db.connection().execute(
            update(jobs)
            .where(jobs.c.id == row["id"])
            .values(
                status="completed",
                completed_at=func.clock_timestamp(),
                error_code=None,
            )
        )
        db.add(
            ExecutionEvent(
                execution_id=run.id,
                entity_type="durable_jobs",
                entity_id=row["id"],
                from_status=row["status"],
                to_status="completed",
                details={"reason": "local_wait_registered"},
            )
        )


def terminate_jobs(db, run, status, code):
    if db.info.get("workflow_transaction") != (WorkflowExecution, run.id):
        raise ValueError("Job termination requires its execution transaction")
    if status not in {"cancelled", "failed"}:
        raise ValueError("Invalid terminal job status")
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
                status=status,
                error_code=code,
                completed_at=func.clock_timestamp(),
            )
        )
        db.add(
            ExecutionEvent(
                execution_id=run.id,
                entity_type="durable_jobs",
                entity_id=row["id"],
                from_status=row["status"],
                to_status=status,
                details={"reason": code},
            )
        )


def finish_job(db, run, claim, status, error_code=None, *, allow_expired=False):
    if run.id != claim.execution_id or db.info.get("workflow_transaction") != (
        WorkflowExecution,
        run.id,
    ):
        raise ValueError("Job completion requires its execution transaction")
    if (
        status not in {"completed", "failed", "cancelled"}
        or locked_claim(
            db,
            claim,
            allow_expired=allow_expired,
        )
        is None
    ):
        raise LeaseLostError("Job is not owned by this live claim")
    db.connection().execute(
        update(jobs)
        .where(jobs.c.id == claim.id)
        .values(
            status=status,
            completed_at=func.now(),
            error_code=error_code,
        )
    )
    db.add(
        ExecutionEvent(
            execution_id=run.id,
            entity_type="durable_jobs",
            entity_id=claim.id,
            from_status="running",
            to_status=status,
            details={"error_code": error_code},
        )
    )


def commit_result(db, claim, work, *, result=None, error=None, now=None, allow_expired=False):
    if work.execution_id != claim.execution_id:
        raise ValueError("Work does not belong to the claimed execution")
    run = execution(db, claim.execution_id)
    if work.parallel:
        run = db.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == run.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    with workflow_transaction(db, run, expected_revision=None if work.parallel else work.revision):
        row = locked_claim(db, claim, allow_expired=allow_expired)
        if row is None:
            raise LeaseLostError("Job lease expired or was reassigned")
        if row["attempt_id"] != work.attempt_id or row["dispatched_at"] is None:
            raise ValueError("Work does not belong to the dispatched job")
        complete_work(db, work, result=result, error=error, now=now)
        step = db.get(StepRun, work.step_id)
        failed = step.status != "completed"
        finish_job(
            db,
            run,
            claim,
            "failed" if failed else "completed",
            step.error_code if failed else None,
            allow_expired=allow_expired,
        )
        if work.parallel:
            from src.services.parallel_runtime import schedule_parallel

            schedule_parallel(db, run)
        elif run.status not in TERMINAL:
            enqueue(db, run, claim.sequence + 1, due_at=step.next_attempt_at)
    return True


def fail_queued_job(db, run, row, code):
    if db.info.get("workflow_transaction") != (WorkflowExecution, run.id):
        raise ValueError("Queued failure requires the execution transaction")
    changed = db.connection().execute(
        update(jobs)
        .where(
            jobs.c.id == row["id"],
            jobs.c.execution_id == run.id,
            jobs.c.organization_id == tenant_id(db),
            jobs.c.status == "queued",
        )
        .values(status="failed", completed_at=func.clock_timestamp(), error_code=code)
    )
    if changed.rowcount != 1:
        raise StaleWorkflowError("Queued job changed")
    db.add(
        ExecutionEvent(
            execution_id=run.id,
            entity_type="durable_jobs",
            entity_id=row["id"],
            from_status="queued",
            to_status="failed",
            details={"error_code": code},
        )
    )


def process_claim(engine, claim, registry=DEFAULT_REGISTRY):
    from src.services.worker_leases import maintain_lease

    with Session(engine) as db:
        bind_tenant(db, claim.organization_id)
        # Match completion/recovery lock order: execution first, then its job.
        run = execution(db, claim.execution_id)
        run = db.scalar(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.id == run.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        # Serialize dispatch, then commit this marker with the prepared checkpoint.
        row = locked_claim(db, claim)
        if row is None or row["dispatched_at"] is not None:
            return False
        db.connection().execute(
            update(jobs)
            .where(jobs.c.id == claim.id)
            .values(
                dispatched_at=func.now(),
            )
        )
        prepared = False

        def record_preparation(run, work):
            nonlocal prepared
            prepared = True
            if work:
                db.connection().execute(
                    update(jobs)
                    .where(jobs.c.id == claim.id)
                    .values(
                        attempt_id=work.attempt_id,
                    )
                )
            else:
                finish_job(
                    db,
                    run,
                    claim,
                    "completed"
                    if run.status == "waiting"
                    or (run.status == "running" and run.checkpoint_json.get("parallel_mode"))
                    else terminal_job_status(run.status),
                    run.error_code,
                )
                if run.checkpoint_json.get("parallel_mode"):
                    from src.services.parallel_runtime import schedule_parallel

                    schedule_parallel(db, run)

        work = prepare_next(
            db,
            claim.execution_id,
            registry,
            on_checkpoint=record_preparation,
            target_node=row["node_id"],
            target_iteration=row["iteration"],
        )
        if work is None:
            if not prepared:
                run = execution(db, claim.execution_id)
                with workflow_transaction(db, run):
                    finish_job(
                        db,
                        run,
                        claim,
                        "completed" if run.status == "waiting" else terminal_job_status(run.status),
                        None
                        if run.status in {"completed", "waiting"}
                        else (run.error_code or "checkpoint_not_ready"),
                    )
            return True
        with maintain_lease(engine, claim, work.control):
            try:
                from src.services.tool_runtime import execute_node

                result = execute_work(
                    work, registry, tool_executor=lambda item: execute_node(engine, claim, item)
                )
            except ExecutionError as error:
                return commit_result(db, claim, work, error=error)
            return commit_result(db, claim, work, result=result)
