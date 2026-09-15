import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from alembic import command
from src.models.audit_event import AuditEvent
from src.models.durable_job import DurableJob
from src.models.identity import ServicePrincipal, User
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.services import durable_queue as queue
from src.services import execution_cancellation as cancellation
from src.services import worker_leases as leases
from src.services.execution_control import AbortSignal
from src.services.execution_registry import ExecutorRegistry
from src.services.graph_interpreter import prepare_next
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction
from tests.generic_migration_fixtures import pre_deadline_execution
from tests.test_graph_interpreter import start
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_retry_runtime import failure_registry, graph
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_worker_leases import expire
from tests.test_workflow_graph import code
from tests.test_workflow_transactions_postgres import database as database


def cancel(database, identity, reason="Fixture cancellation"):
    with Session(database) as db:
        return cancellation.cancel_execution(db, identity, reason)


def test_queued_cancel_is_atomic_idempotent_and_retained(database):
    with Session(database) as db:
        identity = start(db).id
    cancel(database, identity)
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        revision = run.state_revision
        assert run.cancel_requested and run.cancel_requested_at
        assert run.cancel_reason == "Fixture cancellation"
        assert run.status == "cancelled" and run.output_json is None
        assert db.scalar(select(DurableJob)).status == "cancelled"
    cancel(database, identity, "Repeated request must not rewrite history")
    assert queue.claim_jobs(database, "worker") == []
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).state_revision == revision
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "workflow.cancel")
            )
            == 1
        )


def test_cancel_retry_backoff_preserves_failed_attempt(database):
    with Session(database) as db:
        identity = start(db, graph(delay=60)).id
    queue.process_claim(database, queue.claim_jobs(database, "worker")[0], failure_registry())
    cancel(database, identity)
    assert queue.claim_jobs(database, "worker") == []
    with Session(database) as db:
        step = db.scalar(select(StepRun))
        attempt = db.scalar(select(StepAttempt))
        assert step.status == "cancelled" and step.next_attempt_at is None
        assert attempt.status == "failed" and attempt.error_code == "handler_failed"
        assert [j.status for j in db.scalars(select(DurableJob).order_by(DurableJob.sequence))] == [
            "failed",
            "cancelled",
        ]


def test_cancel_wait_preserves_completed_attempt_and_partial_output(database):
    with Session(database) as db:
        run = start(db)
        identity = run.id
        work = prepare_next(db, identity)
        with workflow_transaction(db, run):
            attempt = db.get(StepAttempt, work.attempt_id)
            attempt.output_json = {"value": 2}
            transition(db, run, attempt, "completed")
            transition(db, run, db.get(StepRun, work.step_id), "waiting")
            transition(db, run, run, "waiting")
    cancel(database, identity)
    with Session(database) as db:
        attempt = db.get(StepAttempt, work.attempt_id)
        assert attempt.status == "completed" and attempt.output_json == {"value": 2}
        assert db.get(StepRun, work.step_id).status == "cancelled"
        assert db.get(WorkflowExecution, identity).status == "cancelled"


def test_running_io_aborts_and_late_result_cannot_publish_or_schedule(database):
    with Session(database) as db:
        identity = start(db).id
    entered, release, aborted = Event(), Event(), Event()
    registry = ExecutorRegistry()

    def handler(inputs, control):
        def abort():
            aborted.set()
            release.set()

        unregister = control.on_abort(abort)
        entered.set()
        try:
            assert release.wait(10)
            # Deliberately return a late value even after abort: the DB fence must reject it.
            return {"value": 999}
        finally:
            unregister()

    registry.controlled_handlers[("builtin.identity", 1)] = handler
    claim = queue.claim_jobs(database, "worker")[0]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(queue.process_claim, database, claim, registry)
        try:
            assert entered.wait(10)
            cancel(database, identity)
            assert aborted.wait(3)
            with pytest.raises(StaleWorkflowError):
                future.result(timeout=10)
        finally:
            release.set()
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "cancelled"
        attempt = db.scalar(select(StepAttempt))
        assert attempt.status == "cancelled" and attempt.output_json is None
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1
        assert db.get(DurableJob, claim.id).status == "cancelled"
    assert not leases.renew_lease(database, claim)
    assert not queue.process_claim(database, claim)


def test_cancel_audit_failure_rolls_back_intent_children_and_job(database, monkeypatch):
    with Session(database) as db:
        identity = start(db).id
        work = prepare_next(db, identity)

    def fail(*args, **kwargs):
        raise RuntimeError("audit fixture failure")

    monkeypatch.setattr(cancellation, "record_audit", fail)
    with pytest.raises(RuntimeError, match="audit fixture"):
        cancel(database, identity)
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert not run.cancel_requested and run.status == "running"
        assert db.get(StepAttempt, work.attempt_id).status == "running"
        assert db.scalar(select(DurableJob)).status == "queued"


def test_cancel_between_preparation_and_io_prevents_invocation(database, monkeypatch):
    with Session(database) as db:
        identity = start(db).id
    original = leases.maintain_lease

    def cancelled_before_io(engine, claim, control):
        cancel(database, identity)
        return original(engine, claim, control)

    def unexpected(_):
        pytest.fail("Cancelled checkpoint must not invoke I/O")

    registry = ExecutorRegistry()
    registry.handlers[("builtin.identity", 1)] = unexpected
    monkeypatch.setattr(leases, "maintain_lease", cancelled_before_io)
    with pytest.raises(StaleWorkflowError):
        queue.process_claim(database, queue.claim_jobs(database, "worker")[0], registry)


@pytest.mark.parametrize("competitor", ["claim", "success", "recovery"])
def test_cancellation_serializes_with_claim_success_and_recovery(database, competitor):
    with Session(database) as db:
        identity = start(db, {"entry_node": "start", "nodes": [code("start")]}, {}).id
    claim = None
    if competitor == "success":
        queue.process_claim(database, queue.claim_jobs(database, "first")[0])
        claim = queue.claim_jobs(database, "final")[0]
    elif competitor == "recovery":
        claim = queue.claim_jobs(database, "expired")[0]
        expire(database, claim)
    barrier = Barrier(2)

    def competing():
        barrier.wait()
        if competitor == "claim":
            return queue.claim_jobs(database, "racer")
        if competitor == "success":
            return queue.process_claim(database, claim)
        return leases.recover_claim(database, claim)

    def cancelling():
        barrier.wait()
        cancel(database, identity)

    with ThreadPoolExecutor(max_workers=2) as pool:
        other, stopped = pool.submit(competing), pool.submit(cancelling)
        other.result(timeout=15)
        stopped.result(timeout=15)
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status in {"completed", "cancelled"}
        assert run.cancel_requested == (run.status == "cancelled")
        assert all(j.status in {"completed", "cancelled"} for j in db.scalars(select(DurableJob)))
        if competitor == "success":
            assert db.scalar(select(StepRun)).status == "completed"
            assert db.scalar(select(StepAttempt)).output_json == {}
    assert queue.claim_jobs(database, "after") == []


def test_cancel_api_tenant_role_and_control_only_service_scope(database, tenants, tenant_client):
    client = tenant_client
    identities = []
    for tenant in tenants:
        actor = prepare(database, tenant)
        with Session(database) as db:
            bind_tenant(db, tenant["org"])
            db.info["principal"] = Principal("admin", actor, tenant["org"])
            identities.append(start(db).id)
    actor = prepare(database, tenants[0], "viewer")
    assert client.post(f"/workflow-executions/{identities[0]}/cancel", json={}).status_code == 403
    prepare(database, tenants[0], "operator")
    assert client.post(f"/workflow-executions/{identities[1]}/cancel", json={}).status_code == 404
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        db.get(User, actor).kind = "service"
        db.add(
            ServicePrincipal(
                user_id=actor,
                organization_id=tenants[0]["org"],
                role="operator",
                scopes=["workflow.control"],
            )
        )
        db.commit()
    assert client.get(f"/workflow-executions/{identities[0]}").status_code == 403
    response = client.post(f"/workflow-executions/{identities[0]}/cancel", json={"reason": "Stop"})
    assert response.status_code == 200
    assert response.json() == {
        "id": str(identities[0]),
        "status": "cancelled",
        "cancel_requested": True,
    }
    assert (
        client.post(f"/workflow-executions/{identities[0]}/cancel", json={}).json()
        == response.json()
    )
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        assert db.get(WorkflowExecution, identities[0]).cancel_requested_by_user_id == actor


def test_abort_callbacks_are_idempotent_removable_and_isolated():
    signal, calls = AbortSignal(), []
    signal.on_abort(lambda: calls.append("removed"))()
    signal.on_abort(lambda: 1 / 0)
    signal.on_abort(lambda: calls.append("active"))
    signal.abort()
    signal.abort()
    signal.on_abort(lambda: calls.append("late"))
    assert calls == ["active", "late"]


def test_cancellation_migration_preserves_old_rows_and_terminal_job_history():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration78_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f077_execution_deadlines")
            with Session(conn) as db:
                identity = pre_deadline_execution(db)
            conn.execute(
                text("""INSERT INTO durable_jobs
                (id, organization_id, execution_id, sequence, status)
                SELECT gen_random_uuid(), organization_id, id, 0, 'queued'
                FROM workflow_executions WHERE id=:id"""),
                {"id": identity},
            )
            conn.commit()
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            with Session(scoped) as db:
                assert not db.get(WorkflowExecution, identity).cancel_requested
            cancel(scoped, identity)
            assert queue.claim_jobs(scoped, "after") == []
            with pytest.raises(Exception, match="terminal history are immutable"):
                conn.execute(text("UPDATE durable_jobs SET status='queued'"))
            conn.rollback()
            with pytest.raises(RuntimeError, match="Retain execution cancellation history"):
                command.downgrade(config, "f077_execution_deadlines")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
