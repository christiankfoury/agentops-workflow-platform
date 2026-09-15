import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from src.models.audit_event import AuditEvent
from src.models.execution_start import ExecutionStart
from src.models.workflow_execution import ExecutionEvent, WorkflowExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.workflow_definition import DefinitionCreate
from src.services import execution_starts, workflow_definitions
from src.services.graph_validation import ensure_executable
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_graph import NUMBER, code, obj
from tests.test_workflow_transactions_postgres import database as database


@pytest.fixture
def available_code(monkeypatch):
    # Capability fixture only: no handler dispatch exists in Phase 73.
    monkeypatch.setattr(
        workflow_definitions, "ensure_executable", lambda graph: ensure_executable(graph, {"code"})
    )


def graph():
    return {"entry_node": "start", "input_schema": obj(value=NUMBER), "nodes": [code("start")]}


def definition(db):
    item = workflow_definitions.create_definition(db, DefinitionCreate(name="Start", graph=graph()))
    workflow_definitions.publish(db, item.id, 1)
    return item


def request(identity, key="retry-key", **updates):
    return ExecutionStartRequest(
        definition_id=identity, input={"value": 1}, idempotency_key=key, **updates
    )


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_retries_pin_original_version_and_survive_publication_and_archive(database, available_code):
    with Session(database) as db:
        item = definition(db)
        body = request(item.id)
        run = execution_starts.start_execution(db, body)
        original_id, original_version = run.id, run.version_id
        assert run.status == "pending" and run.state_revision == 0
        second = workflow_definitions.publish(db, item.id, item.draft_revision)
        assert second.id != original_version
        assert execution_starts.start_execution(db, body).id == original_id
        changed = body.model_copy(update={"input": {"value": 2}})
        with pytest.raises(HTTPException) as error:
            execution_starts.start_execution(db, changed)
        assert error.value.status_code == 409
        with pytest.raises(HTTPException) as error:
            execution_starts.start_execution(db, request(item.id, version_id=original_version))
        assert error.value.status_code == 409
        workflow_definitions.archive(db, item.id, item.draft_revision)
        assert execution_starts.start_execution(db, body).id == original_id
        with pytest.raises(HTTPException, match="archived"):
            execution_starts.start_execution(
                db, request(item.id, key="new", version_id=original_version)
            )
        assert (
            count(db, WorkflowExecution)
            == count(db, ExecutionStart)
            == count(db, ExecutionEvent)
            == 1
        )
        assert (
            len(db.scalars(select(AuditEvent).where(AuditEvent.action == "workflow.start")).all())
            == 1
        )


@pytest.mark.parametrize("different_definition", [False, True])
def test_concurrent_start_keys_have_one_atomic_winner(
    database, available_code, different_definition
):
    with Session(database) as db:
        first = definition(db).id
        second = definition(db).id if different_definition else first
    barrier = Barrier(2)

    def start(identity):
        with Session(database) as db:
            barrier.wait(timeout=10)
            try:
                return str(execution_starts.start_execution(db, request(identity)).id)
            except HTTPException as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(start, [first, second]))
    if different_definition:
        assert results.count(409) == 1
    else:
        assert results[0] == results[1]
    with Session(database) as db:
        assert (
            count(db, WorkflowExecution)
            == count(db, ExecutionStart)
            == count(db, ExecutionEvent)
            == 1
        )


def test_invalid_unavailable_missing_and_rollback_starts_leave_no_receipt(database, monkeypatch):
    with Session(database) as db:
        item = definition(db)
        body = request(item.id)
        with pytest.raises(HTTPException) as error:
            execution_starts.start_execution(db, body)
        assert error.value.status_code == 409  # Real registry remains unavailable.
        monkeypatch.setattr(workflow_definitions, "ensure_executable", lambda graph: None)
        with pytest.raises(HTTPException) as error:
            execution_starts.start_execution(
                db, body.model_copy(update={"input": {"value": "bad"}})
            )
        assert error.value.status_code == 422
        with pytest.raises(HTTPException) as error:
            execution_starts.start_execution(db, request(item.id, version_id=uuid.uuid4()))
        assert error.value.status_code == 404

        def fail(*args, **kwargs):
            raise RuntimeError("injected audit failure")

        monkeypatch.setattr(execution_starts, "record_audit", fail)
        with pytest.raises(RuntimeError, match="injected"):
            execution_starts.start_execution(db, body)
        assert (
            count(db, WorkflowExecution)
            == count(db, ExecutionStart)
            == count(db, ExecutionEvent)
            == 0
        )


def test_cached_version_cannot_start_after_concurrent_archive(database, available_code):
    with Session(database) as cached, Session(database) as editor:
        item = definition(cached)
        selected = workflow_definitions.version(cached, item.id, item.published_version_id)
        selected_id = selected.id
        workflow_definitions.archive(editor, item.id, item.draft_revision, selected_id)
        with pytest.raises(HTTPException, match="archived"):
            execution_starts.start_execution(cached, request(item.id, version_id=selected_id))
        assert count(cached, WorkflowExecution) == count(cached, ExecutionStart) == 0


def test_start_api_permissions_tenant_key_scope_and_authenticated_actor(
    database,
    tenants,
    tenant_client,
    available_code,
):
    client = tenant_client
    item = client.post("/workflow-definitions", json={"name": "API", "graph": graph()}).json()
    client.post(f"/workflow-definitions/{item['id']}/publish", json={"expected_revision": 1})
    body = {"definition_id": item["id"], "input": {"value": 1}, "idempotency_key": "shared"}
    actor = prepare(database, tenants[0], "operator")
    response = client.post("/workflow-executions", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["created_by_user_id"] == str(actor)
    first_id = response.json()["id"]
    assert client.post("/workflow-executions", json=body).json()["id"] == first_id
    prepare(database, tenants[0], "viewer")
    assert client.post("/workflow-executions", json=body).status_code == 403
    # Independent tenant service calls use the same key and receive a different run.
    from src.services.identity import Principal
    from src.services.tenancy import bind_tenant

    actor = prepare(database, tenants[1])
    with Session(database) as db:
        bind_tenant(db, tenants[1]["org"])
        db.info["principal"] = Principal("admin", actor, tenants[1]["org"])
        item = definition(db)
        run = execution_starts.start_execution(db, request(item.id, key="shared"))
        assert str(run.id) != first_id


def test_start_receipt_migration_is_immutable_and_refuses_history_loss(available_code):
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration73_" + uuid.uuid4().hex
    with engine.begin() as admin:
        admin.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f073_execution_starts")
            command.downgrade(config, "f072_execution_records")
            command.upgrade(config, "f073_execution_starts")
            with Session(conn) as db:
                item = definition(db)
                run = execution_starts.start_execution(db, request(item.id))
                assert run.version_id == item.published_version_id
                db.commit()
            for statement in [
                "DELETE FROM execution_starts",
                "UPDATE execution_starts SET key = 'reuse'",
            ]:
                with pytest.raises(DBAPIError, match="immutable"):
                    conn.execute(text(statement))
                conn.rollback()
            with pytest.raises(RuntimeError, match="Retain execution start receipts"):
                command.downgrade(config, "f072_execution_records")
            conn.rollback()
    finally:
        with engine.begin() as admin:
            admin.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
