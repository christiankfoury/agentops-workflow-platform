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
from src.models.workflow_definition import WorkflowDefinition, WorkflowVersion
from src.schemas.workflow_definition import DefinitionCreate, DefinitionUpdate
from src.services import workflow_definitions as service
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_graph import code
from tests.test_workflow_transactions_postgres import database as database


def graph():
    return {"entry_node": "start", "nodes": [code("start")]}


def create(db):
    return service.create_definition(db, DefinitionCreate(name="Fixture", graph=graph()))


def test_drafts_publication_archive_history_and_runtime_gate(tenant_client, database, tenants):
    client = tenant_client
    item = client.post("/workflow-definitions", json={"name": "Fixture", "graph": {}}).json()
    path = f"/workflow-definitions/{item['id']}"
    assert client.post(path + "/validate").json()["valid"] is False
    assert client.post(path + "/publish", json={"expected_revision": 1}).status_code == 422
    updated = client.put(
        path + "/draft",
        json={
            "name": "Working",
            "graph": graph(),
            "expected_revision": 1,
        },
    )
    assert updated.status_code == 200 and updated.json()["draft_revision"] == 2
    result = client.post(path + "/validate").json()
    assert result["valid"] and not result["executable"] and result["runtime_errors"]
    published = client.post(path + "/publish", json={"expected_revision": 2})
    assert published.status_code == 201, published.text
    first = published.json()
    assert first["source_revision"] == 2 and first["number"] == 1
    assert client.post(path + "/publish", json={"expected_revision": 2}).status_code == 409
    assert (
        client.put(
            path + "/draft",
            json={
                "name": "Second",
                "graph": graph(),
                "expected_revision": 3,
            },
        ).status_code
        == 200
    )
    second = client.post(path + "/publish", json={"expected_revision": 4}).json()
    assert second["number"] == 2
    diff = client.get(
        path + f"/versions/{second['id']}/diff", params={"compare_to": first["id"]}
    ).json()["diff"]
    assert '"Working"' in diff and '"Second"' in diff
    assert len(client.get(path + "/versions").json()) == 2
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        with pytest.raises(HTTPException) as error:
            service.require_runnable_version(db, uuid.UUID(item["id"]), uuid.UUID(first["id"]))
        assert error.value.status_code == 409
        assert db.scalar(select(func.count()).select_from(WorkflowVersion)) == 2
        # Failed publication produced no success audit or version.
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.action == "workflow.publish",
                )
            )
            == 2
        )
    assert (
        client.post(
            path + f"/versions/{second['id']}/archive", json={"expected_revision": 5}
        ).json()["published_version_id"]
        is None
    )
    assert client.post(path + "/archive", json={"expected_revision": 6}).status_code == 200
    assert client.get(path + f"/versions/{first['id']}").json()["name"] == "Working"
    assert client.post(path + "/publish", json={"expected_revision": 7}).status_code == 409


@pytest.mark.parametrize(
    "role,can_draft,can_publish",
    [
        ("viewer", False, False),
        ("reviewer", False, False),
        ("operator", True, False),
        ("admin", True, True),
    ],
)
def test_definition_role_matrix(tenant_client, database, tenants, role, can_draft, can_publish):
    item = tenant_client.post(
        "/workflow-definitions", json={"name": "Fixture", "graph": graph()}
    ).json()
    prepare(database, tenants[0], role)
    response = tenant_client.post("/workflow-definitions", json={"name": "New", "graph": graph()})
    assert response.status_code == (201 if can_draft else 403)
    path = f"/workflow-definitions/{item['id']}"
    assert tenant_client.post(path + "/validate").status_code == 200
    response = tenant_client.post(path + "/publish", json={"expected_revision": 1})
    assert response.status_code == (201 if can_publish else 403)
    assert tenant_client.get(path).status_code == 200


def test_cross_tenant_definitions_versions_and_prompt_references(tenant_client, database, tenants):
    with Session(database) as db:
        bind_tenant(db, tenants[1]["org"])
        actor = prepare(database, tenants[1], "admin")
        db.info["principal"] = Principal("admin", actor, tenants[1]["org"])
        foreign = create(db)
        foreign_id = foreign.id
        published = service.publish(db, foreign.id, 1)
        foreign_version = published.id
    path = f"/workflow-definitions/{foreign_id}"
    for suffix in ["", "/versions", f"/versions/{foreign_version}"]:
        assert tenant_client.get(path + suffix).status_code == 404
    assert tenant_client.post(path + "/publish", json={"expected_revision": 2}).status_code == 404
    assert str(foreign_id) not in tenant_client.get("/workflow-definitions").text
    payload = {
        "entry_node": "llm",
        "nodes": [
            {
                "id": "llm",
                "type": "llm",
                "config": {
                    "prompt_version_id": str(tenants[1]["prompt"]),
                    "model": "fixture",
                },
            }
        ],
    }
    item = tenant_client.post(
        "/workflow-definitions", json={"name": "Private", "graph": payload}
    ).json()
    assert (
        tenant_client.post(
            f"/workflow-definitions/{item['id']}/publish", json={"expected_revision": 1}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("operation", ["draft", "publish"])
def test_competing_drafts_and_publications_conflict(database, operation):
    with Session(database) as db:
        identity = create(db).id
    barrier = Barrier(2)

    def compete():
        with Session(database) as db:
            barrier.wait(timeout=10)
            try:
                if operation == "publish":
                    service.publish(db, identity, 1)
                else:
                    service.update_draft(
                        db,
                        identity,
                        DefinitionUpdate(
                            name="Edited",
                            graph=graph(),
                            expected_revision=1,
                        ),
                    )
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: compete(), range(2)))
    assert sorted(results) == [200, 409]
    with Session(database) as db:
        assert db.get(WorkflowDefinition, identity).draft_revision == 2
        assert db.scalar(select(func.count()).select_from(WorkflowVersion)) == (
            operation == "publish"
        )


def test_publication_rollback_and_orm_immutability(database, monkeypatch):
    with Session(database) as db:
        item = create(db)
        identity = item.id
        original = service.record_audit

        def fail(*args, **kwargs):
            raise RuntimeError("audit failure")

        monkeypatch.setattr(service, "record_audit", fail)
        with pytest.raises(RuntimeError, match="audit failure"):
            service.publish(db, identity, 1)
        db.rollback()
        assert db.get(WorkflowDefinition, identity).draft_revision == 1
        assert db.scalar(select(func.count()).select_from(WorkflowVersion)) == 0
        monkeypatch.setattr(service, "record_audit", original)
        published = service.publish(db, identity, 1)
        published.graph = {}
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()


def test_cached_draft_cannot_overwrite_new_revision_and_pointer_cannot_cross_definition(database):
    with Session(database) as db:
        identity = create(db).id
        another = create(db).id
        other_version = service.publish(db, another, 1).id
    with Session(database) as stale, Session(database) as fresh:
        cached = stale.get(WorkflowDefinition, identity)
        service.update_draft(
            fresh,
            identity,
            DefinitionUpdate(
                name="Latest",
                graph=graph(),
                expected_revision=1,
            ),
        )
        with pytest.raises(HTTPException) as error:
            service.publish(stale, identity, 1)
        assert error.value.status_code == 409
        stale.rollback()
        assert cached.name == "Latest"
        cached.published_version_id = other_version
        with pytest.raises(DBAPIError):
            stale.commit()
        stale.rollback()


def test_migration_immutability_prompt_retention_and_rollback_guard():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration71_" + uuid.uuid4().hex
    with engine.begin() as admin:
        admin.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f071_workflow_definitions")
            command.downgrade(config, "f069_audit_events")
            command.upgrade(config, "f071_workflow_definitions")
            with Session(conn) as db:
                from src.models.agent_type import AgentType
                from src.models.prompt_version import PromptVersion

                prompt = PromptVersion(
                    agent_type=AgentType.analyst,
                    name="Pinned",
                    version=1,
                    template="Original",
                    is_active=False,
                )
                db.add(prompt)
                db.commit()
                payload = {
                    "entry_node": "llm",
                    "nodes": [
                        {
                            "id": "llm",
                            "type": "llm",
                            "config": {
                                "prompt_version_id": str(prompt.id),
                                "model": "fixture",
                            },
                        }
                    ],
                }
                item = service.create_definition(db, DefinitionCreate(name="Pinned", graph=payload))
                published = service.publish(db, item.id, 1)
                assert published.prompt_snapshots[str(prompt.id)]["template"] == "Original"
                published_id = published.id
                db.commit()
            for statement in [
                "UPDATE workflow_versions SET graph = '{}'",
                "DELETE FROM workflow_versions",
                "DELETE FROM workflow_version_prompts",
                "UPDATE prompt_versions SET template = 'changed'",
                "DELETE FROM prompt_versions",
            ]:
                with pytest.raises(DBAPIError):
                    conn.execute(text(statement))
                    conn.commit()
                conn.rollback()
            conn.execute(text("UPDATE prompt_versions SET is_active = true"))
            conn.execute(
                text("UPDATE workflow_versions SET archived_at = now() WHERE id = :id"),
                {"id": published_id},
            )
            conn.commit()
            with pytest.raises(RuntimeError, match="retain workflow definitions"):
                command.downgrade(config, "f069_audit_events")
            conn.rollback()
    finally:
        with engine.begin() as admin:
            admin.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
