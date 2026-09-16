import hashlib
import hmac
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.main import app
from src.models.audit_event import AuditEvent
from src.models.durable_job import DurableJob
from src.models.identity import Organization, ServicePrincipal, User
from src.models.webhook import WebhookDelivery
from src.models.workflow_execution import WorkflowExecution
from src.schemas.webhook import WebhookCreate, WebhookRotate, WebhookUpdate
from src.services import execution_starts, webhooks, workflow_definitions
from src.services.tenancy import bind_tenant, tenant_id
from tests.test_execution_starts import available_code as available_code
from tests.test_execution_starts import count, definition
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_transactions_postgres import database as database

KEY = b"synthetic-webhook-fixture-key-00000001"
NEW_KEY = b"synthetic-webhook-fixture-key-00000002"


@pytest.fixture(autouse=True)
def signing_config(monkeypatch):
    monkeypatch.setattr(settings, "webhook_secret_values", {})


def setup(db, **updates):
    owner = tenant_id(db)
    settings.webhook_secret_values.update(
        {f"{owner}/old": SecretStr(KEY.decode()), f"{owner}/new": SecretStr(NEW_KEY.decode())}
    )
    user = User(issuer="fixture", subject=str(uuid.uuid4()), display_name="Hook", kind="service")
    db.add(user)
    db.flush()
    actor = ServicePrincipal(
        user_id=user.id, organization_id=owner, role="operator", scopes=["workflow.start"]
    )
    db.add(actor)
    db.flush()
    item = definition(db)
    body = WebhookCreate(
        name="Hook",
        definition_id=item.id,
        service_principal_id=actor.id,
        secret_alias="old",
        **updates,
    )
    return webhooks.create(db, body)


def signed(identity, body=b'{"value":1}', event="event-1", key=KEY, timestamp=None):
    timestamp = timestamp or str(int(time.time()))
    message = f"{identity}\n{timestamp}\n{event}\n".encode() + body
    signature = "sha256=" + hmac.new(key, message, hashlib.sha256).hexdigest()
    return timestamp, event, signature, body


def send(db, identity, **kwargs):
    return webhooks.receive(db, identity, *signed(identity, **kwargs))


def test_concurrent_replay_retains_version_and_conflicts_on_changed_bytes(database, available_code):
    with Session(database) as db:
        hook = setup(db)
        identity, definition_id = hook.id, hook.definition_id
    barrier = Barrier(3)

    def receive(_):
        with Session(database) as db:
            barrier.wait(timeout=10)
            return send(db, identity)

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(receive, range(3)))
    assert len({r["execution_id"] for r in results}) == 1
    assert sum(r["duplicate"] for r in results) == 2
    with Session(database) as db:
        item = workflow_definitions.definition(db, definition_id)
        workflow_definitions.publish(db, item.id, item.draft_revision)
        workflow_definitions.archive(db, item.id, item.draft_revision)
        assert send(db, identity)["version_id"] == results[0]["version_id"]
        with pytest.raises(HTTPException) as error:
            send(db, identity, body=b'{"value": 1}')
        assert error.value.status_code == 409
        assert (
            count(db, WebhookDelivery) == count(db, WorkflowExecution) == count(db, DurableJob) == 1
        )
        assert db.scalar(select(WebhookDelivery)).attempts == 5
        assert (
            len(db.scalars(select(AuditEvent).where(AuditEvent.action == "webhook.delivery")).all())
            == 5
        )


def test_rejected_input_can_retry_same_bytes_after_mapping_fix(database, available_code):
    with Session(database) as db:
        hook = setup(db)
        identity = hook.id
        body = b'{"nested":{"amount":3}}'
        with pytest.raises(HTTPException) as error:
            send(db, identity, body=body)
        assert error.value.status_code == 422
        assert count(db, WorkflowExecution) == count(db, DurableJob) == 0
        assert db.scalar(select(WebhookDelivery)).status == "rejected"
        config = WebhookUpdate(
            **{
                k: v
                for k, v in webhooks.public_trigger(hook).items()
                if k in WebhookUpdate.model_fields
            },
            expected_revision=1,
        )
        data = config.model_dump()
        data["input_mapping"] = {"value": {"source": "input", "path": ["nested", "amount"]}}
        config = WebhookUpdate.model_validate(data)
        db.info.pop("principal", None)  # Separate administrator request after public delivery.
        webhooks.update(db, identity, config)
        accepted = send(db, identity, body=body)
        assert db.get(WorkflowExecution, uuid.UUID(accepted["execution_id"])).input_json == {
            "value": 3
        }
        assert db.scalar(select(WebhookDelivery)).attempts == 2


@pytest.mark.parametrize("body", [b"[]", b'{"value":1,"value":2}', b"{", b'{"value":NaN}', b"\xff"])
def test_malformed_payload_is_retained_without_a_run(database, available_code, body):
    with Session(database) as db:
        identity = setup(db).id
        with pytest.raises(HTTPException) as error:
            send(db, identity, body=body)
        assert error.value.status_code == 422
        assert count(db, WorkflowExecution) == 0
        assert db.scalar(select(WebhookDelivery)).error_code == "input_invalid"


@pytest.mark.parametrize(
    "case",
    [
        "forged",
        "stale",
        "future",
        "oversized",
        "disabled",
        "scope",
        "user",
        "organization",
        "principal",
    ],
)
def test_invalid_or_revoked_deliveries_do_not_create_receipts(database, available_code, case):
    with Session(database) as db:
        hook = setup(db, max_payload_bytes=1024)
        identity = hook.id
        kwargs = {}
        if case == "forged":
            kwargs["key"] = NEW_KEY
        elif case in {"stale", "future"}:
            kwargs["timestamp"] = str(int(time.time()) + (1000 if case == "future" else -1000))
        elif case == "oversized":
            kwargs["body"] = b" " * 1025
        elif case == "disabled":
            hook.enabled = False
        else:
            actor = db.get(ServicePrincipal, hook.service_principal_id)
            if case == "scope":
                actor.scopes = []
            elif case == "user":
                db.get(User, actor.user_id).active = False
            elif case == "organization":
                db.get(Organization, hook.organization_id).active = False
            else:
                actor.active = False
        db.commit()
        with pytest.raises(HTTPException) as error:
            send(db, identity, **kwargs)
        assert error.value.status_code == (
            413 if case == "oversized" else 401 if case in {"forged", "stale", "future"} else 403
        )
        assert count(db, WebhookDelivery) == count(db, WorkflowExecution) == 0


def test_rotation_grace_revision_and_redaction(database, available_code, monkeypatch):
    with Session(database) as db:
        hook = setup(db)
        identity = hook.id
        now = webhooks.runtime_now(db)
        monkeypatch.setattr(webhooks, "runtime_now", lambda _: now)
        hook = webhooks.rotate(
            db, identity, WebhookRotate(expected_revision=1, secret_alias="new", grace_seconds=60)
        )
        assert "secret_alias" not in webhooks.public_trigger(hook)
        send(db, identity)
        send(db, identity, event="new", key=NEW_KEY)
        monkeypatch.setattr(webhooks, "runtime_now", lambda _: now + timedelta(seconds=60))
        with pytest.raises(HTTPException) as error:
            send(db, identity, event="expired")
        assert error.value.status_code == 401
        with pytest.raises(HTTPException) as error:
            db.info.pop("principal", None)
            webhooks.rotate(db, identity, WebhookRotate(expected_revision=1, secret_alias="old"))
        assert error.value.status_code == 409
        db.rollback()
        audits = db.scalars(select(AuditEvent)).all()
        assert all("synthetic-webhook" not in json.dumps(a.details_json) for a in audits)


def test_internal_failure_rolls_back_receipt_run_and_job(database, available_code, monkeypatch):
    with Session(database) as db:
        identity = setup(db).id
        enqueue = execution_starts.enqueue

        def fail(*args, **kwargs):
            enqueue(*args, **kwargs)
            raise RuntimeError("injected queue failure")

        monkeypatch.setattr(execution_starts, "enqueue", fail)
        with pytest.raises(RuntimeError, match="injected"):
            send(db, identity)
        assert (
            count(db, WebhookDelivery) == count(db, WorkflowExecution) == count(db, DurableJob) == 0
        )
        monkeypatch.setattr(execution_starts, "enqueue", enqueue)
        assert send(db, identity)["status"] == "accepted"


def test_public_api_headers_limits_and_acknowledgement(database, available_code):
    with Session(database) as db:
        identity = setup(db).id

    def get_session():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = get_session
    try:
        with TestClient(app) as client:
            timestamp, event, signature, body = signed(identity)
            headers = {
                "content-type": "application/json",
                "x-agentops-timestamp": timestamp,
                "x-agentops-event-id": event,
                "x-agentops-signature": signature,
            }
            url = f"/webhooks/{identity}"
            accepted = client.post(url, headers=headers, content=body)
            assert accepted.status_code == 202, accepted.text
            assert "input_json" not in accepted.json()
            assert client.post(url, content=body).status_code == 415
            assert (
                client.post(
                    url, headers={"content-type": "application/json"}, content=body
                ).status_code
                == 401
            )
            duplicates = list(headers.items()) + [("x-agentops-event-id", event)]
            assert client.post(url, headers=duplicates, content=body).status_code == 401
            assert client.post(url, headers=headers, content=b"x" * 262145).status_code == 413
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_tenant_configuration_permissions_and_history(
    database, available_code, tenants, tenant_client
):
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        from src.services.identity import Principal

        actor = prepare(database, tenants[0])
        db.info["principal"] = Principal("admin", actor, tenants[0]["org"])
        hook = setup(db)
        identity = hook.id
        config = {
            k: v
            for k, v in webhooks.public_trigger(hook).items()
            if k in WebhookCreate.model_fields
        }
        config["secret_alias"] = "old"
        config = json.loads(WebhookCreate(**config).model_dump_json())
    with Session(database) as db:
        send(db, identity)
    url = f"/webhook-triggers/{identity}"
    response = tenant_client.get(url + "/deliveries")
    assert response.status_code == 200 and len(response.json()) == 1
    delivery = response.json()[0]["id"]
    assert len(tenant_client.get(url + f"/deliveries/{delivery}/events").json()) == 1
    prepare(database, tenants[0], "operator")
    assert tenant_client.post("/webhook-triggers", json=config).status_code == 403
    with Session(database) as db:
        bind_tenant(db, tenants[1]["org"])
        with pytest.raises(HTTPException) as error:
            webhooks.get_trigger(db, identity)
        assert error.value.status_code == 404
        with pytest.raises(HTTPException):
            webhooks.validate_config(db, WebhookCreate(**config), "old")


@pytest.mark.parametrize("change", ["publish", "revoke"])
def test_publication_and_revocation_races_have_serialized_outcomes(
    database, available_code, change
):
    with Session(database) as db:
        hook = setup(db)
        identity, definition_id, principal_id = (
            hook.id,
            hook.definition_id,
            hook.service_principal_id,
        )
        old_version = workflow_definitions.definition(db, definition_id).published_version_id
    barrier = Barrier(2)

    def deliver():
        with Session(database) as db:
            barrier.wait(timeout=10)
            try:
                return send(db, identity)
            except HTTPException as error:
                assert error.status_code == 403
                return None

    def edit():
        with Session(database) as db:
            barrier.wait(timeout=10)
            if change == "publish":
                item = workflow_definitions.definition(db, definition_id)
                return workflow_definitions.publish(db, item.id, item.draft_revision).id
            db.get(ServicePrincipal, principal_id).active = False
            db.commit()
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        delivery, edit_result = pool.submit(deliver), pool.submit(edit)
        accepted, new_version = delivery.result(), edit_result.result()
    with Session(database) as db:
        assert count(db, DurableJob) == count(db, WebhookDelivery) == int(accepted is not None)
        if change == "publish":
            assert accepted["version_id"] in {str(old_version), str(new_version)}
            assert send(db, identity)["version_id"] == accepted["version_id"]
        else:
            with pytest.raises(HTTPException) as error:
                send(db, identity)
            assert error.value.status_code == 403


def test_pinned_selection_mapping_defaults_and_unavailable_keys(database, available_code):
    with Session(database) as db:
        hook = setup(
            db,
            input_mapping={
                "value": {
                    "source": "input",
                    "path": ["absent"],
                    "on_missing": "default",
                    "default": 9,
                }
            },
        )
        identity = hook.id
        item = workflow_definitions.definition(db, hook.definition_id)
        old_version = item.published_version_id
        hook.version_policy, hook.version_id = "pinned", old_version
        db.commit()
        workflow_definitions.publish(db, item.id, item.draft_revision)
        response = send(db, identity, body=b"{}")
        assert response["version_id"] == str(old_version)
        assert db.get(WorkflowExecution, uuid.UUID(response["execution_id"])).input_json == {
            "value": 9
        }
        settings.webhook_secret_values.clear()
        with pytest.raises(HTTPException) as error:
            send(db, identity)
        assert error.value.status_code == 503
        db.info.pop("principal", None)
        config = {
            k: v
            for k, v in webhooks.public_trigger(hook).items()
            if k in WebhookUpdate.model_fields
        }
        config.update(enabled=False, expected_revision=1)
        assert not webhooks.update(db, identity, WebhookUpdate(**config)).enabled


def test_signature_cannot_be_moved_between_triggers(database, available_code):
    with Session(database) as db:
        first, second = setup(db).id, setup(db).id
        with pytest.raises(HTTPException) as error:
            webhooks.receive(db, second, *signed(first))
        assert error.value.status_code == 401
        assert count(db, WebhookDelivery) == 0
