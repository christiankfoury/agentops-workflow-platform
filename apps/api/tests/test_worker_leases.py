import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from threading import Barrier, Event

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.orm import Session

from alembic import command
from src.config import settings
from src.models.durable_job import DurableJob
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.services import durable_queue as queue
from src.services import execution_starts
from src.services import worker_leases as leases
from src.services.execution_registry import ExecutorRegistry
from src.services.workflow_transactions import StaleWorkflowError
from src.worker import run_worker
from tests.test_graph_interpreter import branching_graph, start
from tests.test_workflow_transactions_postgres import database as database


def retry_graph():
    graph = branching_graph()
    graph["nodes"][0]["retry"] = {"max_attempts": 3}
    return graph


def expire(database, claim):
    with database.begin() as conn:
        conn.execute(
            update(queue.jobs)
            .where(queue.jobs.c.id == claim.id)
            .values(
                lease_expires_at=func.clock_timestamp() - text("interval '1 second'"),
            )
        )


def test_competing_reclaimers_rotate_one_owner_without_duplicate_work(database):
    with Session(database) as db:
        identity = start(db).id
    original = queue.claim_jobs(database, "old")[0]
    expire(database, original)
    barrier = Barrier(2)

    def recover(_):
        barrier.wait()
        return leases.recover_claim(database, original)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(recover, range(2))) == 1
    new = queue.claim_jobs(database, "new")[0]
    assert new.id == original.id and new.token != original.token
    assert not leases.renew_lease(database, original)
    assert not queue.process_claim(database, original)
    assert queue.process_claim(database, new)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"
        assert db.get(DurableJob, original.id).recovery_count == 1
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 4


def test_delayed_old_worker_cannot_commit_after_reassignment(database, monkeypatch):
    with Session(database) as db:
        identity = start(db, retry_graph()).id
    old = queue.claim_jobs(database, "old")[0]
    entered, release = Event(), Event()
    registry = ExecutorRegistry()

    def delayed(value):
        entered.set()
        assert release.wait(15)
        return {"value": 999}

    registry.handlers[("builtin.identity", 1)] = delayed
    monkeypatch.setattr(leases, "maintain_lease", lambda *_: nullcontext())
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(queue.process_claim, database, old, registry)
        assert entered.wait(10)
        expire(database, old)
        assert leases.recover_expired(database) == 1
        assert run_worker(database, drain=True, poll_seconds=0.01) == 0
        release.set()
        with pytest.raises(StaleWorkflowError):
            future.result(timeout=10)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"result": 3}
        attempts = db.scalars(select(StepAttempt).order_by(StepAttempt.created_at)).all()
        assert len(attempts) == 5 and attempts[0].error_code == "worker_abandoned"
        assert attempts[0].output_json is None
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 5


def test_heartbeat_extends_live_lease_and_expired_lease_cannot_renew(database, monkeypatch):
    monkeypatch.setattr(settings, "worker_lease_seconds", 0.4)
    monkeypatch.setattr(settings, "worker_heartbeat_seconds", 0.05)
    with Session(database) as db:
        start(db)
    claim = queue.claim_jobs(database, "heartbeat")[0]
    with leases.maintain_lease(database, claim):
        time.sleep(0.7)
        assert leases.recover_expired(database) == 0
        with Session(database) as db:
            job = db.get(DurableJob, claim.id)
            assert job.heartbeat_at > job.claimed_at
    expire(database, claim)
    assert not leases.renew_lease(database, claim)
    assert leases.recover_expired(database) == 1


def test_recovery_exhaustion_preserves_abandoned_attempt(database, monkeypatch):
    with Session(database) as db:
        identity = start(db).id  # Default node allows exactly one attempt.
    claim = queue.claim_jobs(database, "abandoned")[0]

    def crash(*_):
        raise RuntimeError("simulated process interruption")

    monkeypatch.setattr(queue, "execute_work", crash)
    with pytest.raises(RuntimeError, match="interruption"):
        queue.process_claim(database, claim)
    expire(database, claim)
    assert leases.recover_expired(database) == 1
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).error_code == "recovery_exhausted"
        assert db.get(DurableJob, claim.id).status == "failed"
        assert db.scalar(select(StepAttempt)).error_code == "worker_abandoned"
    assert queue.claim_jobs(database, "later") == []


def test_expiry_rejects_results_before_reassignment(database, monkeypatch):
    with Session(database) as db:
        start(db, retry_graph())
    claim = queue.claim_jobs(database, "expired")[0]
    original = queue.execute_work

    def expire_result(*args):
        result = original(*args)
        expire(database, claim)
        return result

    with monkeypatch.context() as patch:
        patch.setattr(queue, "execute_work", expire_result)
        with pytest.raises(queue.LeaseLostError):
            queue.process_claim(database, claim)
    with Session(database) as db:
        attempt = db.scalar(select(StepAttempt))
        assert attempt.status == "running" and attempt.output_json is None
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1
    assert leases.recover_expired(database) == 1
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0


def test_claim_crashes_without_attempts_still_have_a_recovery_bound(database, monkeypatch):
    monkeypatch.setattr(settings, "worker_max_recoveries", 1)
    with Session(database) as db:
        identity = start(db).id
    for _ in range(2):
        claim = queue.claim_jobs(database, "crashing")[0]
        expire(database, claim)
        assert leases.recover_expired(database) == 1
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).error_code == "recovery_exhausted"
        assert db.get(DurableJob, claim.id).recovery_count == 1
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 0
    assert queue.claim_jobs(database, "later") == []


@pytest.mark.parametrize("boundary", ["before", "during", "after"])
def test_killed_process_recovers_at_checkpoint_boundaries(database, tmp_path, boundary):
    with Session(database) as db:
        identity = start(db, retry_graph()).id
    ready = tmp_path / "ready"
    schema = database.get_execution_options()["schema_translate_map"][None]
    script = """
import sys, time
from pathlib import Path
from src.database import engine
from src.services.durable_queue import claim_jobs, process_claim
from src.services.execution_registry import ExecutorRegistry
ready, boundary = Path(sys.argv[1]), sys.argv[2]
claim = claim_jobs(engine, 'kill-fixture')[0]
registry = ExecutorRegistry()
def blocked(value):
    ready.write_text('ready')
    time.sleep(60)
    return value
if boundary == 'during':
    registry.handlers[('builtin.identity', 1)] = blocked
    process_claim(engine, claim, registry)
elif boundary == 'after':
    process_claim(engine, claim)
ready.write_text('ready')
time.sleep(60)
"""
    env = {
        **os.environ,
        "DATABASE_URL": os.environ["WORKFLOW_TEST_DATABASE_URL"],
        "PGOPTIONS": f"-c search_path={schema}",
        "IDENTITY_ENABLED": "false",
        "WORKER_LEASE_SECONDS": "0.5",
        "WORKER_HEARTBEAT_SECONDS": "0.05",
    }
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(ready), boundary],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 15
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.exists(), "Fixture worker did not reach its kill boundary"
        process.kill()
        process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
    if boundary != "after":
        deadline = time.monotonic() + 5
        recovered = 0
        while not recovered and time.monotonic() < deadline:
            recovered = leases.recover_expired(database)
            time.sleep(0.02)
        assert recovered == 1
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == "completed" and run.output_json == {"result": 3}
        assert db.scalar(select(func.count()).select_from(StepRun)) == 5
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == (
            5 if boundary == "during" else 4
        )
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 5


def test_lease_migration_recovers_old_running_jobs_and_retains_history(monkeypatch):
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration76_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f075_durable_jobs")
            with monkeypatch.context() as patch:
                patch.setattr(execution_starts, "enqueue", lambda *_: None)
                with Session(conn) as db:
                    identity = start(db).id
                    db.commit()
            conn.execute(
                text("""
                INSERT INTO durable_jobs
                (id, organization_id, execution_id, sequence, status, claim_token, worker_id,
                 claimed_at) SELECT gen_random_uuid(), organization_id, id, 0, 'running',
                 gen_random_uuid(), 'old-worker', now() FROM workflow_executions WHERE id=:id
            """),
                {"id": identity},
            )
            conn.commit()
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            assert leases.recover_expired(scoped) == 1
            assert run_worker(scoped, drain=True, poll_seconds=0.01) == 0
            assert (
                conn.execute(text("SELECT status FROM workflow_executions")).scalar() == "completed"
            )
            conn.rollback()
            with pytest.raises(RuntimeError, match="Retain job lease history"):
                command.downgrade(config, "f075_durable_jobs")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
