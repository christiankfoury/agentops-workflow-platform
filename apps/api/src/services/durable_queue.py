"""Trusted worker queue authority. Global claims use Core; execution work is scoped."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.models.durable_job import DurableJob
from src.models.workflow_execution import TERMINAL, ExecutionEvent, WorkflowExecution
from src.services.execution_records import execution
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.graph_expressions import ExecutionError
from src.services.graph_interpreter import complete_work, execute_work, prepare_next
from src.services.tenancy import bind_tenant, tenant_id
from src.services.workflow_transactions import workflow_transaction

jobs = DurableJob.__table__


@dataclass(frozen=True)
class Claim:
    id: UUID
    organization_id: UUID
    execution_id: UUID
    sequence: int
    token: UUID


def enqueue(db, run, sequence):
    job = DurableJob(execution_id=run.id, sequence=sequence)
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
    # This is the sole cross-tenant scan: trusted infrastructure, never an API input.
    with engine.begin() as conn:
        due = conn.execute(
            select(jobs)
            .where(
                jobs.c.status == "queued",
                jobs.c.due_at <= func.now(),
            )
            .order_by(jobs.c.due_at, jobs.c.id)
            .limit(capacity)
            .with_for_update(skip_locked=True)
        )
        for row in due.mappings().all():
            token = uuid4()
            conn.execute(
                update(jobs)
                .where(jobs.c.id == row["id"])
                .values(
                    status="running",
                    claim_token=token,
                    worker_id=worker_id,
                    claimed_at=func.now(),
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


def locked_claim(db, claim):
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
            )
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    return row


def finish_job(db, run, claim, status, error_code=None):
    if run.id != claim.execution_id or db.info.get("workflow_transaction") != (
        WorkflowExecution,
        run.id,
    ):
        raise ValueError("Job completion requires its execution transaction")
    if status not in {"completed", "failed"} or locked_claim(db, claim) is None:
        raise ValueError("Job is not owned by this running claim")
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


def commit_result(db, claim, work, *, result=None, error=None):
    if work.execution_id != claim.execution_id:
        raise ValueError("Work does not belong to the claimed execution")
    run = execution(db, claim.execution_id)
    with workflow_transaction(db, run, expected_revision=work.revision):
        row = locked_claim(db, claim)
        if row is None:
            return False
        if row["attempt_id"] != work.attempt_id or row["dispatched_at"] is None:
            raise ValueError("Work does not belong to the dispatched job")
        complete_work(db, work, result=result, error=error)
        finish_job(
            db, run, claim, "failed" if error else "completed", error.code if error else None
        )
        if run.status not in TERMINAL:
            enqueue(db, run, claim.sequence + 1)
    return True


def process_claim(engine, claim, registry=DEFAULT_REGISTRY):
    with Session(engine) as db:
        bind_tenant(db, claim.organization_id)
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
                    "completed" if run.status == "completed" else "failed",
                    run.error_code,
                )

        work = prepare_next(db, claim.execution_id, registry, on_checkpoint=record_preparation)
        if work is None:
            if not prepared:
                run = execution(db, claim.execution_id)
                with workflow_transaction(db, run):
                    finish_job(
                        db,
                        run,
                        claim,
                        "completed" if run.status == "completed" else "failed",
                        None
                        if run.status == "completed"
                        else (run.error_code or "checkpoint_not_ready"),
                    )
            return True
        try:
            result = execute_work(work, registry)
        except ExecutionError as error:
            return commit_result(db, claim, work, error=error)
        return commit_result(db, claim, work, result=result)
