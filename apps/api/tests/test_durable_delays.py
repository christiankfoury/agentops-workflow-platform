import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from alembic import command
from src.models.durable_job import DurableJob
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.schemas.workflow_graph import DelayConfig
from src.services import delay_runtime as delays
from src.services import durable_queue as queue
from src.services import worker_leases as leases
from src.services.execution_cancellation import cancel_execution
from src.services.graph_interpreter import run_deterministic_execution
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from src.services.workflow_transactions import workflow_transaction
from src.worker import run_worker
from tests.generic_migration_fixtures import pre_deadline_execution
from tests.test_graph_interpreter import start
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_worker_leases import expire
from tests.test_workflow_graph import code, edge
from tests.test_workflow_transactions_postgres import database as database


def graph(config=None):
    return {
        "entry_node": "pause",
        "nodes": [
            {"id": "pause", "type": "delay", "config": config or {"seconds": 60}},
            code("finish"),
        ],
        "edges": [edge("pause", "finish")],
    }


def waiting(database, config=None):
    with Session(database) as db:
        identity = start(db, graph(config), {}).id
    queue.process_claim(database, queue.claim_jobs(database, "register")[0])
    with Session(database) as db:
        step = db.scalar(select(StepRun))
        return identity, step.id, step.organization_id, step.wake_at


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"seconds": -1},
        {"seconds": 604801},
        {"seconds": True},
        {"seconds": "10"},
        {"seconds": float("inf")},
        {"seconds": float("nan")},
        {"wake_at": "2026-09-15T12:00:00"},
        {"wake_at": "invalid"},
        {"wake_at": 1000},
        {"seconds": 2, "wake_at": "2026-09-15T12:00:00Z"},
    ],
)
def test_invalid_timer_contracts(config):
    with pytest.raises(ValidationError):
        DelayConfig.model_validate(config)


def test_wait_releases_worker_and_fake_clock_wakes_exactly_once(database):
    identity, step_id, owner, due = waiting(database)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        revision = run.state_revision
        step = db.get(StepRun, step_id)
        assert run.status == step.status == "waiting"
        assert step.waiting_reason == "delay" and due.utcoffset() == timedelta(0)
        assert db.scalar(select(StepAttempt)).status == "completed"
        assert db.scalar(select(DurableJob)).status == "completed"
    assert not delays.wake_delay(
        database, step_id, owner, identity, now=due - timedelta(microseconds=1)
    )
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).state_revision == revision
    barrier = Barrier(2)

    def wake(_):
        barrier.wait()
        return delays.wake_due_delays(database, now=due)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(wake, range(2))) == 1
    assert not delays.wake_delay(database, step_id, owner, identity, now=due)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"
        assert db.get(StepRun, step_id).wake_at == due
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 2
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 3


@pytest.mark.parametrize("stop", ["cancel", "deadline"])
def test_wait_cancellation_and_deadline_suppress_resume(database, stop):
    identity, step_id, owner, due = waiting(database)
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        if stop == "cancel":
            cancel_execution(db, identity)
        else:
            with workflow_transaction(db, run):
                run.deadline_at = due - timedelta(seconds=30)
    assert delays.wake_due_delays(database, now=due - timedelta(seconds=29)) == (stop == "deadline")
    assert not delays.wake_delay(database, step_id, owner, identity, now=due)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == (
            "cancelled" if stop == "cancel" else "failed"
        )
        assert db.get(StepRun, step_id).status == ("cancelled" if stop == "cancel" else "failed")
        assert db.scalar(select(StepAttempt)).status == "completed"
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1


def test_wake_enqueue_failure_rolls_back_and_retries_once(database, monkeypatch):
    identity, step_id, owner, due = waiting(database)
    original = queue.enqueue

    def failure(*args, **kwargs):
        raise RuntimeError("enqueue fixture")

    monkeypatch.setattr(queue, "enqueue", failure)
    with pytest.raises(RuntimeError, match="enqueue fixture"):
        delays.wake_delay(database, step_id, owner, identity, now=due)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "waiting"
        assert db.get(StepRun, step_id).status == "waiting"
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1
    monkeypatch.setattr(queue, "enqueue", original)
    assert delays.wake_delay(database, step_id, owner, identity, now=due)


def test_expired_registration_claim_recovers_without_duplicate_timer(database):
    with Session(database) as db:
        identity = start(db, graph({"seconds": 0}), {}).id
    claim = queue.claim_jobs(database, "crashed")[0]
    expire(database, claim)
    assert leases.recover_expired(database) == 1
    assert not queue.process_claim(database, claim)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"
        assert db.scalar(select(func.count()).select_from(StepRun)) == 2
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 2


def test_restart_process_resumes_persisted_explicit_utc_timer(database):
    # A historical timestamp is immediately due; no external clock or sleeps are needed.
    identity, _, _, due = waiting(database, {"wake_at": "2020-01-01T12:00:00-05:00"})
    schema = database.get_execution_options()["schema_translate_map"][None]
    result = subprocess.run(
        [sys.executable, "-m", "src.worker", "--drain"],
        env={
            **os.environ,
            "DATABASE_URL": os.environ["WORKFLOW_TEST_DATABASE_URL"],
            "PGOPTIONS": f"-c search_path={schema}",
            "IDENTITY_ENABLED": "false",
            "WORKER_POLL_SECONDS": "0.01",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"
        assert db.scalar(select(StepRun).where(StepRun.node_id == "pause")).wake_at == due


@pytest.mark.parametrize("timestamp", [None, "9999-12-31T23:59:59-05:00"])
def test_excessive_absolute_wake_fails_with_retained_attempt(database, timestamp):
    future = timestamp or (datetime.now(UTC) + timedelta(days=8)).isoformat()
    with Session(database) as db:
        identity = start(db, graph({"wake_at": future}), {}).id
    queue.process_claim(database, queue.claim_jobs(database, "worker")[0])
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == "failed" and run.error_code == "delay_invalid"
        assert db.scalar(select(StepRun)).status == "failed"
        assert db.scalar(select(StepAttempt)).error_classification == "permanent"


def test_local_wait_checkpoint_can_handoff_to_durable_worker(database):
    with Session(database) as db:
        identity = start(db, graph({"seconds": 0}), {}).id
        assert run_deterministic_execution(db, identity).status == "waiting"
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"
        assert all(job.error_code is None for job in db.scalars(select(DurableJob)))


def test_generic_step_reads_expose_scoped_wait_details(database, tenants, tenant_client):
    ids = []
    for tenant in tenants:
        actor = prepare(database, tenant)
        with Session(database) as db:
            bind_tenant(db, tenant["org"])
            db.info["principal"] = Principal("admin", actor, tenant["org"])
            ids.append(start(db, graph(), {}).id)
    for claim in queue.claim_jobs(database, "worker", 2):
        queue.process_claim(database, claim)
    response = tenant_client.get(f"/workflow-executions/{ids[0]}/steps")
    assert response.status_code == 200, response.text
    assert response.json()[0]["waiting_reason"] == "delay"
    assert response.json()[0]["wake_at"] is not None
    assert tenant_client.get(f"/workflow-executions/{ids[1]}/steps").status_code == 404


def test_delay_migration_old_rows_and_retention():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration79_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f078_execution_cancellation")
            with Session(conn) as db:
                pre_deadline_execution(db)
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            _, _, _, due = waiting(scoped, {"seconds": 0})
            assert delays.wake_due_delays(scoped, now=due) == 1
            assert run_worker(scoped, drain=True, poll_seconds=0.01) == 0
            with pytest.raises(RuntimeError, match="Retain execution wait history"):
                command.downgrade(config, "f078_execution_cancellation")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
