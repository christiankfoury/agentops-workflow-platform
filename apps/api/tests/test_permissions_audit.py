import os
import uuid

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from src.main import app
from src.models.audit_event import AuditEvent
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.identity import Membership, ServicePrincipal, User
from src.models.workflow_run import WorkflowRun, WorkflowStatus
from src.services import human_approvals
from src.services.identity import Principal
from src.services.permissions import PERMISSIONS, permits
from src.services.tenancy import bind_tenant
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_transactions_postgres import database as database


def prepare(database, owner, role="admin", high=False):
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        member = db.scalar(select(Membership).where(Membership.organization_id == owner["org"]))
        member.role = role
        run = db.get(WorkflowRun, owner["run"])
        run.status = WorkflowStatus.waiting_for_human
        approval = db.get(HumanApproval, owner["approval"])
        approval.issues_json = (
            [{"severity": "high", "message": "Unverified amount"}] if high else []
        )
        db.commit()
        return member.user_id


def audits(database, org):
    with Session(database) as db:
        bind_tenant(db, org)
        return db.scalars(select(AuditEvent)).all()


@pytest.mark.parametrize("role", ["viewer", "operator", "reviewer", "admin"])
@pytest.mark.parametrize("action", ["approve", "request-retry", "reject", "edit"])
def test_approval_role_matrix_and_actor_forgery(tenant_client, tenants, database, role, action):
    owner = tenants[0]
    actor = prepare(database, owner, role)
    response = tenant_client.post(
        f"/human-approvals/{owner['approval']}/{action}",
        json={
            "human_feedback": "verified decision",
            "approved_by_user_id": str(uuid.uuid4()),
        },
    )
    allowed = role in {"reviewer", "admin"}
    assert response.status_code == (200 if allowed else 403), response.text
    evidence = audits(database, owner["org"])
    assert len(evidence) == (1 if allowed else 0)
    if allowed:
        assert evidence[0].actor_user_id == actor
        assert evidence[0].organization_id == owner["org"]
        assert evidence[0].target_id == str(owner["approval"])
        if action != "edit":
            assert response.json()["approved_by_user_id"] == str(actor)


@pytest.mark.parametrize("role", ["viewer", "operator", "reviewer", "admin"])
def test_workflow_and_configuration_role_matrix(tenant_client, tenants, database, role):
    actor = prepare(database, tenants[0], role)
    assert tenant_client.get("/workflow-runs").status_code == 200
    start = tenant_client.post(
        "/workflow-runs",
        json={
            "workflow_type": "sales_report",
            "input_id": str(tenants[0]["input"]),
            "created_by_user_id": str(uuid.uuid4()),
        },
    )
    assert start.status_code == (201 if role in {"operator", "admin"} else 403)
    if start.status_code == 201:
        assert start.json()["created_by_user_id"] == str(actor)
    prompt = tenant_client.post(
        "/prompt-versions",
        json={
            "agent_type": "analyst",
            "name": "Permission test",
            "version": 1,
            "template": "safe",
            "created_by_user_id": str(uuid.uuid4()),
        },
    )
    assert prompt.status_code == (201 if role == "admin" else 403)
    if role == "admin":
        assert prompt.json()["created_by_user_id"] == str(actor)
    settings = tenant_client.put(
        "/agent-settings/analyst",
        json={
            "model": "gpt-4.1-mini",
            "max_tokens": 100,
            "max_retries": 0,
        },
    )
    assert settings.status_code == (200 if role == "admin" else 403)
    assert tenant_client.get("/access/members").status_code == (200 if role == "admin" else 403)
    permissions = tenant_client.get("/access/permissions").json()
    assert permissions["role"] == role
    assert ("approval.decide" in permissions["actions"]) == (role in {"reviewer", "admin"})
    assert tenant_client.get("/evaluation-results/export/json").status_code == 200
    evidence = audits(database, tenants[0]["org"])
    expected = {"export"}
    if role in {"operator", "admin"}:
        expected.add("workflow.start")
    if role == "admin":
        expected |= {"prompt.create", "settings.update"}
    assert {entry.action for entry in evidence} == expected
    assert len(evidence) == len(expected)
    assert all(entry.actor_user_id == actor for entry in evidence)


def test_high_severity_requires_admin_but_allows_reviewer_retry(tenant_client, tenants, database):
    owner = tenants[0]
    prepare(database, owner, "reviewer", high=True)
    path = f"/human-approvals/{owner['approval']}"
    assert tenant_client.post(path + "/approve").status_code == 403
    assert audits(database, owner["org"]) == []
    prepare(database, owner, "admin", high=True)
    assert tenant_client.post(path + "/approve").status_code == 200
    assert audits(database, owner["org"])[0].details_json["high_severity_override"] is True


def test_revocation_between_request_and_decision_is_rechecked(
    tenant_client, tenants, database, monkeypatch
):
    owner = tenants[0]
    prepare(database, owner, "reviewer")
    original = human_approvals._get_run

    def revoke_then_return(db, run_id):
        run = original(db, run_id)
        with Session(database) as admin:
            member = admin.scalar(
                select(Membership).where(Membership.organization_id == owner["org"])
            )
            member.active = False
            admin.commit()
        return run

    monkeypatch.setattr(human_approvals, "_get_run", revoke_then_return)
    assert tenant_client.post(f"/human-approvals/{owner['approval']}/approve").status_code == 403
    assert audits(database, owner["org"]) == []
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        assert db.get(HumanApproval, owner["approval"]).status == ApprovalStatus.pending


def test_failed_decision_rolls_back_its_audit(tenant_client, tenants, database, monkeypatch):
    owner = tenants[0]
    prepare(database, owner)

    def fail(*_args, **_kwargs):
        raise RuntimeError("Injected audit rollback")

    monkeypatch.setattr(human_approvals, "log_workflow_event", fail)
    with pytest.raises(RuntimeError, match="Injected audit rollback"):
        tenant_client.post(f"/human-approvals/{owner['approval']}/approve")
    assert audits(database, owner["org"]) == []
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        assert db.get(HumanApproval, owner["approval"]).status == ApprovalStatus.pending


def test_scoped_service_cannot_invent_roles_or_approval_scope(tenant_client, tenants, database):
    owner = tenants[0]
    actor = prepare(database, owner)
    with Session(database) as db:
        db.get(User, actor).kind = "service"
        db.add(
            ServicePrincipal(
                user_id=actor,
                organization_id=owner["org"],
                role="operator",
                scopes=["read", "workflow.start", "approval.decide"],
            )
        )
        db.commit()
    tenant_client.headers["x-agentops-role"] = "admin"
    assert tenant_client.get("/workflow-runs").status_code == 200
    assert tenant_client.post(f"/human-approvals/{owner['approval']}/approve").status_code == 403
    start = tenant_client.post("/workflow-runs", json={"workflow_type": "sales_report"})
    assert start.status_code == 201
    assert tenant_client.get("/evaluation-results/export/json").status_code == 403
    event = audits(database, owner["org"])[0]
    assert event.actor_kind == "service" and event.service_principal_id is not None


def test_membership_changes_and_audit_are_scoped_and_immutable(tenant_client, tenants, database):
    owner = tenants[0]
    actor = prepare(database, owner)
    assert tenant_client.put(f"/access/members/{actor}", json={"role": "viewer"}).status_code == 409
    with Session(database) as db:
        target = User(
            issuer="https://fixture.test", subject="new-member", display_name="New member"
        )
        db.add(target)
        db.commit()
        target_id = target.id
    response = tenant_client.put(f"/access/members/{target_id}", json={"role": "reviewer"})
    assert response.status_code == 200
    evidence = tenant_client.get("/access/audit").json()
    assert len(evidence) == 1 and evidence[0]["actor_user_id"] == str(actor)
    assert evidence[0]["details_json"]["role"] == "reviewer"
    assert audits(database, tenants[1]["org"]) == []
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        entry = db.scalars(select(AuditEvent)).one()
        entry.action = "tampered"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()


def test_reserved_admin_permissions_and_unknown_actions_are_closed():
    for action in ["workflow.publish", "credentials.manage", "approval.override"]:
        assert PERMISSIONS[action] == {"admin"}
    assert permits(Principal("admin"), "invented.permission") is False


def test_membership_lock_refreshes_cached_role_before_last_admin_check(database, tenants):
    from fastapi import HTTPException

    from src.routers.access import MembershipUpdate, update_membership

    owner = tenants[0]
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        member = db.scalar(select(Membership).where(Membership.organization_id == owner["org"]))
        member.role = "viewer"
        db.commit()
        actor = member.user_id
        assert member.role == "viewer"
        db.info["principal"] = Principal("viewer", actor, owner["org"])
        # Another administrator promotes this user after this session cached it.
        with Session(database) as admin:
            changed = admin.get(Membership, member.id)
            changed.role = "admin"
            admin.commit()
        with pytest.raises(HTTPException) as error:
            update_membership(actor, MembershipUpdate(role="viewer"), db)
        assert error.value.status_code == 409


def test_generic_status_endpoint_cannot_bypass_approval(tenant_client, tenants, database):
    owner = tenants[0]
    prepare(database, owner, "operator", high=True)
    response = tenant_client.patch(
        f"/workflow-runs/{owner['run']}/status", json={"status": "writer_running"}
    )
    assert response.status_code == 422
    assert audits(database, owner["org"]) == []
    assert (
        tenant_client.post(f"/workflow-runs/{owner['run']}/evaluation-comparison").status_code
        == 403
    )


def test_configured_public_identity_startup(auth_config, monkeypatch):
    from src.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/workflow-runs").status_code == 401


def test_service_entry_points_reject_viewer_without_provider_work(database, tenants):
    from fastapi import HTTPException

    from src.services.sales_baseline import run_sales_baseline

    owner = tenants[0]
    actor = prepare(database, owner, "viewer")
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        db.info["principal"] = Principal("viewer", actor, owner["org"])
        with pytest.raises(HTTPException) as error:
            run_sales_baseline(db, db.get(WorkflowRun, owner["run"]), object())
        assert error.value.status_code == 403


def test_audit_migration_prevents_database_mutation_and_rolls_back():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration69_" + uuid.uuid4().hex
    with engine.begin() as admin:
        admin.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f069_audit_events")
            conn.execute(
                text(
                    "INSERT INTO audit_events "
                    "(id, actor_kind, action, target_type, target_id, details_json) "
                    "VALUES (:id, 'local', 'fixture', 'fixture', 'test', '{}')"
                ),
                {"id": uuid.uuid4()},
            )
            conn.commit()
            for statement in [
                "UPDATE audit_events SET action = 'tampered'",
                "DELETE FROM audit_events",
            ]:
                with pytest.raises(DBAPIError, match="immutable"):
                    conn.execute(text(statement))
                conn.rollback()
            assert conn.execute(text("SELECT count(*) FROM audit_events")).scalar_one() == 1
            conn.commit()
            command.downgrade(config, "f068_tenant_ownership")
            command.upgrade(config, "f069_audit_events")
    finally:
        with engine.begin() as admin:
            admin.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
