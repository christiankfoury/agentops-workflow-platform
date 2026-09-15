import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from alembic import command
from src.models.durable_job import DurableJob
from src.models.execution_start import ExecutionStart
from src.models.workflow_execution import StepAttempt, WorkflowExecution
from src.services import durable_queue as queue
from src.services import execution_starts
from src.services.execution_registry import ExecutorRegistry
from src.services.graph_interpreter import execute_work, run_deterministic_execution
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from src.worker import run_worker
from tests.generic_migration_fixtures import pre_deadline_execution
from tests.test_graph_interpreter import start
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_graph import code
from tests.test_workflow_transactions_postgres import database as database


def test_acceptance_is_atomic_and_does_not_execute(database, monkeypatch):
    def unexpected(*_):
        pytest.fail("Start acceptance must not execute a handler")

    monkeypatch.setattr(queue, "execute_work", unexpected)
    with Session(database) as db:
        run = start(db)
        job = db.scalar(select(DurableJob))
        assert run.status == "pending" and job.status == "queued" and job.execution_id == run.id
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 0
    original = execution_starts.enqueue

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("injected enqueue failure")

    monkeypatch.setattr(execution_starts, "enqueue", interrupted)
    with Session(database) as db, pytest.raises(RuntimeError, match="injected"):
        start(db)
    with Session(database) as db:
        for model in [WorkflowExecution, DurableJob, ExecutionStart]:
            assert db.scalar(select(func.count()).select_from(model)) == 1


def test_concurrent_claims_are_bounded_and_duplicate_delivery_is_inert(database):
    with Session(database) as db:
        for _ in range(4):
            start(db)
    barrier = Barrier(2)

    def claim(worker):
        barrier.wait()
        return queue.claim_jobs(database, worker, 2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        batches = list(pool.map(claim, ["worker-a", "worker-b"]))
    claims = [item for batch in batches for item in batch]
    assert len(claims) == len({item.id for item in claims}) == 4
    assert queue.claim_jobs(database, "worker-c") == []
    target = claims[0]
    registry = ExecutorRegistry()
    entered, release = Event(), Event()

    def slow_identity(value):
        entered.set()
        assert release.wait(10)
        return value

    registry.handlers[("builtin.identity", 1)] = slow_identity
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(queue.process_claim, database, target, registry)
        assert entered.wait(10)
        assert queue.process_claim(database, target, registry) is False
        release.set()
        assert running.result(timeout=10) is True
    assert queue.process_claim(database, target, registry) is False
    with Session(database) as db:
        jobs = db.scalars(
            select(DurableJob)
            .where(
                DurableJob.execution_id == target.execution_id,
            )
            .order_by(DurableJob.sequence)
        ).all()
        assert [item.status for item in jobs] == ["completed", "queued"]
        assert len(db.scalars(select(StepAttempt)).all()) == 1
        assert jobs[0].attempt_id is not None
    with pytest.raises(ValueError, match="capacity"):
        queue.claim_jobs(database, "worker", 33)


def test_completion_and_downstream_enqueue_roll_back_together(database, monkeypatch):
    with Session(database) as db:
        start(db)
    claim = queue.claim_jobs(database, "worker")[0]
    captured = []
    original = queue.enqueue

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("injected next job failure")

    def capture(work, registry):
        captured.append(work)
        return execute_work(work, registry)

    with monkeypatch.context() as patch:
        patch.setattr(queue, "enqueue", interrupted)
        patch.setattr(queue, "execute_work", capture)
        with pytest.raises(RuntimeError, match="injected"):
            queue.process_claim(database, claim)
    work = captured[0]
    result = execute_work(work)
    with Session(database) as db:
        assert db.get(StepAttempt, work.attempt_id).status == "running"
        assert db.get(DurableJob, claim.id).status == "running"
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1
        assert queue.commit_result(db, claim, work, result=result)
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 2


def test_worker_process_restart_drains_persisted_queue(database):
    with Session(database) as db:
        identity = start(db).id
    schema = database.get_execution_options()["schema_translate_map"][None]
    env = {
        **os.environ,
        "DATABASE_URL": os.environ["WORKFLOW_TEST_DATABASE_URL"],
        "PGOPTIONS": f"-c search_path={schema}",
        "WORKER_CONCURRENCY": "1",
        "WORKER_POLL_SECONDS": "0.05",
        "IDENTITY_ENABLED": "false",
    }
    first = subprocess.run(
        [sys.executable, "-m", "src.worker", "--max-jobs", "1"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert first.returncode == 0, first.stderr
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "running"
        assert (
            db.scalar(
                select(func.count()).select_from(DurableJob).where(DurableJob.status == "queued")
            )
            == 1
        )
    restarted = subprocess.run(
        [sys.executable, "-m", "src.worker", "--drain"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert restarted.returncode == 0, restarted.stderr
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == "completed" and run.output_json == {"result": 3}
        assert all(job.status == "completed" for job in db.scalars(select(DurableJob)))
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 4


def test_final_output_and_job_completion_are_atomic(database, monkeypatch):
    with Session(database) as db:
        identity = start(db, {"entry_node": "start", "nodes": [code("start")]}, {}).id
    queue.process_claim(database, queue.claim_jobs(database, "worker")[0])
    claim = queue.claim_jobs(database, "worker")[0]
    original = queue.finish_job

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("injected finalization failure")

    with monkeypatch.context() as patch:
        patch.setattr(queue, "finish_job", interrupted)
        with pytest.raises(RuntimeError, match="injected"):
            queue.process_claim(database, claim)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "running"
        assert db.get(WorkflowExecution, identity).output_json is None
        assert db.get(DurableJob, claim.id).status == "running"
        assert db.get(DurableJob, claim.id).dispatched_at is None
    assert queue.process_claim(database, claim)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"
        assert db.get(DurableJob, claim.id).status == "completed"


def test_failed_handler_completes_job_and_execution_without_downstream_work(database):
    with Session(database) as db:
        identity = start(db).id
    registry = ExecutorRegistry()

    def failing(_):
        raise RuntimeError("private diagnostic")

    registry.handlers[("builtin.identity", 1)] = failing
    assert queue.process_claim(database, queue.claim_jobs(database, "worker")[0], registry)
    with Session(database) as db:
        job = db.scalar(select(DurableJob))
        assert job.status == "failed" and job.error_code == "handler_failed"
        assert db.get(WorkflowExecution, identity).status == "failed"
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1


def test_queued_job_for_locally_completed_run_has_no_false_error(database):
    with Session(database) as db:
        run = start(db, {"entry_node": "start", "nodes": [code("start")]}, {})
        run_deterministic_execution(db, run.id)
    assert queue.process_claim(database, queue.claim_jobs(database, "worker")[0])
    with Session(database) as db:
        job = db.scalar(select(DurableJob))
        assert job.status == "completed" and job.error_code is None
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 1


def test_graceful_stop_drains_current_work_without_more_claims(database, monkeypatch):
    with Session(database) as db:
        start(db)
    stop = Event()
    original = queue.process_claim

    def stopping(*args):
        stop.set()
        return original(*args)

    monkeypatch.setattr("src.worker.process_claim", stopping)
    assert run_worker(database, stop=stop, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert [
            job.status for job in db.scalars(select(DurableJob).order_by(DurableJob.sequence))
        ] == ["completed", "queued"]


def test_job_reads_are_scoped_and_do_not_expose_claim_tokens(tenant_client, tenants, database):
    client = tenant_client
    actor = prepare(database, tenants[0])
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        db.info["principal"] = Principal("admin", actor, tenants[0]["org"])
        own = start(db).id
    actor = prepare(database, tenants[1])
    with Session(database) as db:
        bind_tenant(db, tenants[1]["org"])
        db.info["principal"] = Principal("admin", actor, tenants[1]["org"])
        foreign = start(db).id
    response = client.get(f"/workflow-executions/{own}/jobs")
    assert response.status_code == 200 and len(response.json()) == 1
    assert "claim_token" not in response.json()[0]
    assert client.get(f"/workflow-executions/{foreign}/jobs").status_code == 404


def test_job_migration_backfill_and_history_retention():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration75_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f074_execution_checkpoints")
            with Session(conn) as db:
                identity = pre_deadline_execution(db)
            command.upgrade(config, "head")
            row = conn.execute(text("SELECT execution_id,status FROM durable_jobs")).one()
            assert row.execution_id == identity and row.status == "queued"
            conn.commit()
            with pytest.raises(RuntimeError, match="Retain (execution|.*job)"):
                command.downgrade(config, "f074_execution_checkpoints")
            conn.rollback()
            scoped = engine.execution_options(schema_translate_map={None: schema})
            assert run_worker(scoped, poll_seconds=0.01, drain=True) == 0
            assert (
                conn.execute(
                    text("SELECT count(*) FROM durable_jobs WHERE status != 'completed'")
                ).scalar()
                == 0
            )
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
