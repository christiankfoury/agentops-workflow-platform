"""Durable timers: register a wait, release the worker, atomically resume when due."""

from datetime import UTC, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.workflow_execution import ExecutionEvent, StepRun, WorkflowExecution
from src.services.execution_records import execution
from src.services.graph_expressions import ExecutionError
from src.services.graph_validation import validate_data
from src.services.retry_runtime import expire_execution, runtime_now
from src.services.tenancy import bind_tenant
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction


def schedule_delay(db, run, step, attempt, node, now):
    if db.info.get("workflow_transaction") != (WorkflowExecution, run.id):
        raise ValueError("Delay registration requires its execution transaction")
    try:
        due = (
            now + timedelta(seconds=node.config.seconds)
            if node.config.seconds is not None
            else max(now, node.config.wake_at.astimezone(UTC))
        )
    except (OverflowError, ValueError) as error:
        raise ExecutionError("delay_invalid", "Delay wake time is outside the UTC range") from error
    if due - now > timedelta(days=7):
        raise ExecutionError("delay_invalid", "Delay wake time exceeds the seven-day limit")
    try:
        validate_data({}, node.output_schema)
    except ValueError as error:
        raise ExecutionError(
            "output_invalid", "Delay output must accept an empty object"
        ) from error
    step.waiting_reason = "delay"
    step.wake_at = due.astimezone(UTC)
    attempt.output_json = {}
    transition(db, run, attempt, "completed")
    transition(db, run, step, "waiting")
    if not run.checkpoint_json.get("parallel_mode"):
        transition(db, run, run, "waiting")
    db.add(
        ExecutionEvent(
            execution_id=run.id,
            entity_type="step_runs",
            entity_id=step.id,
            from_status="waiting",
            to_status="waiting",
            details={"reason": "delay_registered", "wake_at": step.wake_at.isoformat()},
        )
    )


class NoWake(Exception):
    pass


def wake_delay(engine, identity, owner, execution_id, *, now=None):
    # Local imports keep the interpreter/queue's transactional registration independent.
    from src.services.durable_queue import enqueue, jobs
    from src.services.graph_interpreter import graph_for, set_edges

    with Session(engine) as db:
        bind_tenant(db, owner)
        run = execution(db, execution_id)
        try:
            with workflow_transaction(db, run):
                step = db.scalar(
                    select(StepRun).where(
                        StepRun.id == identity,
                        StepRun.execution_id == run.id,
                        StepRun.status == "waiting",
                        StepRun.waiting_reason == "delay",
                    )
                )
                if run.status not in {"running", "waiting"} or run.cancel_requested or step is None:
                    raise NoWake()
                moment = now or runtime_now(db)
                if run.deadline_at and moment >= run.deadline_at:
                    expire_execution(db, run)
                    from src.services.durable_queue import terminate_jobs

                    terminate_jobs(db, run, "failed", "run_deadline")
                    return True
                if step.wake_at is None or moment < step.wake_at:
                    raise NoWake()
                # Local deterministic runners can leave their original queue receipt pending.
                # Let the queue consume it before resuming; never create two active jobs.
                if not run.checkpoint_json.get("parallel_mode") and (
                    db.connection()
                    .execute(
                        select(jobs.c.id).where(
                            jobs.c.execution_id == run.id,
                            jobs.c.status.in_(["queued", "running"]),
                        )
                    )
                    .first()
                ):
                    raise NoWake()
                step.output_json = {}
                transition(db, run, step, "completed")
                edges = dict(run.checkpoint_json.get("edges", {}))
                for i, edge in enumerate(graph_for(db, run).edges):
                    if edge.source == step.node_id:
                        edges[str(i)] = "selected"
                set_edges(run, edges)
                if run.status == "waiting":
                    transition(db, run, run, "running")
                if run.checkpoint_json.get("parallel_mode"):
                    from src.services.parallel_runtime import schedule_parallel

                    schedule_parallel(db, run)
                    return True
                sequence = db.connection().scalar(
                    select(func.max(jobs.c.sequence)).where(
                        jobs.c.execution_id == run.id,
                    )
                )
                enqueue(db, run, 0 if sequence is None else sequence + 1)
            return True
        except (NoWake, StaleWorkflowError):
            return False


def wake_due_delays(engine, limit=32, *, now=None):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Wake batch must be between 1 and 100")
    steps, runs = StepRun.__table__, WorkflowExecution.__table__
    with engine.connect() as conn:
        moment = now or conn.scalar(select(func.clock_timestamp()))
        rows = conn.execute(
            select(
                steps.c.id,
                steps.c.organization_id,
                steps.c.execution_id,
            )
            .select_from(steps.join(runs, steps.c.execution_id == runs.c.id))
            .where(
                steps.c.status == "waiting",
                steps.c.waiting_reason == "delay",
                runs.c.status.in_(["running", "waiting"]),
                runs.c.cancel_requested.is_(False),
                or_(steps.c.wake_at <= moment, runs.c.deadline_at <= moment),
            )
            .order_by(steps.c.wake_at, steps.c.id)
            .limit(limit)
        ).all()
    return sum(
        wake_delay(engine, row.id, row.organization_id, row.execution_id, now=now) for row in rows
    )
