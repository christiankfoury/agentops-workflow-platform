import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from alembic import command
from src.models.durable_job import DurableJob
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.schemas.workflow_graph import RetryPolicy
from src.services import durable_queue as queue
from src.services.execution_deadlines import enforce_deadlines
from src.services.execution_registry import ExecutorRegistry
from src.services.graph_expressions import ExecutionError
from src.services.retry_runtime import retry_decision
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction
from src.worker import run_worker
from tests.generic_migration_fixtures import pre_deadline_execution
from tests.test_graph_interpreter import branching_graph, start
from tests.test_workflow_transactions_postgres import database as database


def graph(*, attempts=3, delay=0, timeout=60):
    payload = branching_graph()
    payload["nodes"][0]["retry"] = {
        "max_attempts": attempts,
        "retryable_errors": ["handler_failed", "attempt_timeout", "output_invalid"],
        "initial_delay_seconds": delay,
        "max_delay_seconds": delay,
        "jitter_fraction": 0,
    }
    payload["nodes"][0]["timeout_seconds"] = timeout
    return payload


def failure_registry(invalid=False):
    registry = ExecutorRegistry()

    def handler(_):
        if invalid:
            return {"value": "wrong"}
        raise RuntimeError("temporary fixture failure")

    registry.handlers[("builtin.identity", 1)] = handler
    return registry


def test_fake_clock_backoff_jitter_exhaustion_and_deadline_bounds():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    policy = RetryPolicy(
        max_attempts=5,
        retryable_errors=["handler_failed", "input_invalid"],
        initial_delay_seconds=10,
        max_delay_seconds=60,
        backoff_factor=2,
        jitter_fraction=0.25,
    )
    for number, sample, seconds in [(1, 0, 7.5), (1, 1, 12.5), (3, 0.5, 40), (4, 1, 60)]:
        kind, due, _ = retry_decision(policy, number, "handler_failed", now, sample=sample)
        assert kind == "retryable" and due == now + timedelta(seconds=seconds)
    assert retry_decision(policy, 5, "handler_failed", now)[1:] == (None, "retry_exhausted")
    assert retry_decision(policy, 1, "input_invalid", now) == ("permanent", None, "input_invalid")
    assert retry_decision(policy, 1, "handler_failed", now, now)[1:] == (None, "run_deadline")
    assert retry_decision(policy, 1, "handler_failed", now, now + timedelta(seconds=5))[1:] == (
        None,
        "run_deadline",
    )


def test_retry_due_time_and_attempt_history_survive_worker_process_restart(database):
    with Session(database) as db:
        identity = start(db, graph(delay=1)).id
    queue.process_claim(database, queue.claim_jobs(database, "first")[0], failure_registry())
    with Session(database) as db:
        step = db.scalar(select(StepRun))
        attempt = db.scalar(select(StepAttempt))
        due = db.scalar(select(DurableJob).where(DurableJob.status == "queued"))
        assert step.status == "retrying" and step.next_attempt_at == due.due_at
        assert attempt.number == 1 and attempt.error_classification == "retryable"
        assert attempt.error_code == "handler_failed" and step.iteration == 0
        assert step.idempotency_key == attempt.idempotency_key
        assert due.due_at > db.scalar(select(func.clock_timestamp()))
    assert queue.claim_jobs(database, "early") == []
    schema = database.get_execution_options()["schema_translate_map"][None]
    env = {
        **os.environ,
        "DATABASE_URL": os.environ["WORKFLOW_TEST_DATABASE_URL"],
        "PGOPTIONS": f"-c search_path={schema}",
        "IDENTITY_ENABLED": "false",
        "WORKER_CONCURRENCY": "1",
        "WORKER_POLL_SECONDS": "0.02",
    }
    result = subprocess.run(
        [sys.executable, "-m", "src.worker", "--drain"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"
        attempts = db.scalars(
            select(StepAttempt)
            .where(
                StepAttempt.step_run_id == step.id,
            )
            .order_by(StepAttempt.number)
        ).all()
        assert [item.status for item in attempts] == ["failed", "completed"]
        assert attempts[0].idempotency_key == attempts[1].idempotency_key
        assert db.get(StepRun, step.id).next_attempt_at is None


@pytest.mark.parametrize(
    "invalid,expected,count", [(False, "retry_exhausted", 2), (True, "output_invalid", 1)]
)
def test_permanent_and_exhausted_failures_do_not_leave_runnable_jobs(
    database, invalid, expected, count
):
    with Session(database) as db:
        identity = start(db, graph(attempts=2)).id
    for _ in range(count):
        queue.process_claim(
            database, queue.claim_jobs(database, "worker")[0], failure_registry(invalid)
        )
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == "failed" and run.error_code == expected
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == count
        assert db.scalar(select(func.count()).select_from(DurableJob)) == count
        assert all(job.status == "failed" for job in db.scalars(select(DurableJob)))
    assert queue.claim_jobs(database, "late") == []


def prepared(database, monkeypatch, payload=None):
    with Session(database) as db:
        identity = start(db, payload or graph()).id
    claim = queue.claim_jobs(database, "prepared")[0]
    captured = []

    def dropped(work, _registry):
        captured.append(work)
        raise RuntimeError("delivery fixture interrupted")

    with monkeypatch.context() as patch:
        patch.setattr(queue, "execute_work", dropped)
        with pytest.raises(RuntimeError, match="interrupted"):
            queue.process_claim(database, claim)
    return identity, claim, captured[0]


def test_concurrent_failure_delivery_schedules_one_retry(database, monkeypatch):
    identity, claim, work = prepared(database, monkeypatch)
    barrier = Barrier(2)

    def deliver(_):
        with Session(database) as db:
            barrier.wait()
            try:
                return queue.commit_result(
                    db, claim, work, error=ExecutionError("handler_failed", "failed")
                )
            except StaleWorkflowError:
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(deliver, range(2))) == 1
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).state_revision == work.revision + 1
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 2
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 1


def test_watchdog_times_out_active_work_and_fences_its_late_result(database):
    with Session(database) as db:
        identity = start(db, graph(timeout=0.1)).id
    claim = queue.claim_jobs(database, "slow")[0]
    entered, release = Event(), Event()
    registry = ExecutorRegistry()

    def slow(_):
        entered.set()
        assert release.wait(15)
        return {"value": 999}

    registry.handlers[("builtin.identity", 1)] = slow
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(queue.process_claim, database, claim, registry)
        assert entered.wait(10)
        with Session(database) as db:
            deadline = db.scalar(select(StepAttempt.deadline_at))
        now = deadline + timedelta(milliseconds=1)
        assert enforce_deadlines(database, now=now) == 1
        assert enforce_deadlines(database, now=now) == 0
        release.set()
        with pytest.raises(StaleWorkflowError):
            future.result(timeout=10)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"result": 3}
        first = db.scalar(select(StepAttempt).where(StepAttempt.error_code == "attempt_timeout"))
        assert first.error_classification == "retryable" and first.output_json is None


@pytest.mark.parametrize("mode", ["normal", "max_jobs", "stop"])
def test_worker_watchdog_keeps_physical_concurrency_bounded(database, monkeypatch, mode):
    with Session(database) as db:
        slow_id = start(db, graph(attempts=1, timeout=0.1)).id
        next_id = start(db).id
    entered, release = Event(), Event()
    stop = Event()
    registry = ExecutorRegistry()
    calls = []

    def slow(value):
        calls.append(value)
        entered.set()
        assert release.wait(15)
        return value

    registry.handlers[("builtin.identity", 1)] = slow
    monkeypatch.setattr(
        "src.worker.process_claim",
        lambda engine, claim: queue.process_claim(
            engine,
            claim,
            registry,
        ),
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            run_worker,
            database,
            capacity=1,
            drain=True,
            poll_seconds=0.01,
            stop=stop,
            max_jobs=1 if mode == "max_jobs" else None,
        )
        try:
            assert entered.wait(10)
            if mode == "stop":
                stop.set()
            end = time.monotonic() + 5
            while time.monotonic() < end:
                with Session(database) as db:
                    if db.get(WorkflowExecution, slow_id).status == "failed":
                        break
                time.sleep(0.02)
            with Session(database) as db:
                assert db.get(WorkflowExecution, slow_id).status == "failed"
                assert db.get(WorkflowExecution, next_id).status == "pending"
            assert len(calls) == 1
        finally:
            release.set()
        assert future.result(timeout=15) == 0
    if mode != "normal":
        assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, next_id).status == "completed"


def test_run_deadline_expires_queued_work_and_terminal_cancel_wins_failure_race(
    database, monkeypatch
):
    with Session(database) as db:
        run = start(db)
        identity, deadline = run.id, run.deadline_at
    assert enforce_deadlines(database, now=deadline + timedelta(seconds=1)) == 1
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).error_code == "run_deadline"
        assert db.scalar(select(StepAttempt)) is None
    identity, claim, work = prepared(database, monkeypatch)
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        with workflow_transaction(db, run):
            transition(db, run, db.get(StepAttempt, work.attempt_id), "cancelled")
            transition(db, run, db.get(StepRun, work.step_id), "cancelled")
            transition(db, run, run, "cancelled")
        with pytest.raises(StaleWorkflowError):
            queue.commit_result(db, claim, work, error=ExecutionError("handler_failed", "late"))
        assert (
            db.scalar(
                select(func.count())
                .select_from(DurableJob)
                .where(
                    DurableJob.execution_id == identity,
                )
            )
            == 1
        )
        assert db.get(WorkflowExecution, identity).status == "cancelled"


def test_deadline_migration_backfills_active_records_and_guards_retention():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration77_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f076_worker_leases")
            with Session(conn) as db:
                identity = pre_deadline_execution(db)
            conn.execute(
                text("""
                UPDATE workflow_executions SET status='running', started_at=now() WHERE id=:id;
                INSERT INTO step_runs
                  (id,organization_id,execution_id,node_id,step_type,branch,iteration,
                   idempotency_key,status,input_json,started_at)
                SELECT gen_random_uuid(),organization_id,id,'start','code','main',0,
                       repeat('a',64),'running',jsonb_build_object('value',2),now()
                FROM workflow_executions WHERE id=:id;
                INSERT INTO step_attempts
                  (id,organization_id,step_run_id,number,idempotency_key,status,input_json,started_at)
                SELECT gen_random_uuid(),organization_id,id,1,idempotency_key,
                       'running',input_json,now()
                FROM step_runs WHERE execution_id=:id;
            """),
                {"id": identity},
            )
            conn.commit()
            command.upgrade(config, "head")
            with Session(conn) as db:
                run = db.get(WorkflowExecution, identity)
                assert run.deadline_at > run.created_at
                attempt = db.scalar(select(StepAttempt))
                assert attempt.deadline_at > attempt.started_at
                assert attempt.error_classification is None
                queue.enqueue(db, run, 0)
                db.commit()
                deadline = run.deadline_at
            scoped = engine.execution_options(schema_translate_map={None: schema})
            assert enforce_deadlines(scoped, now=deadline + timedelta(seconds=1)) == 1
            with pytest.raises(RuntimeError, match="Retain execution"):
                command.downgrade(config, "f076_worker_leases")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
