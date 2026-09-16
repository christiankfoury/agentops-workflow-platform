"""Signed, scoped delivery acceptance over the shared durable start contract."""

import hashlib
import hmac
import json
import re
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select

from src.config import settings
from src.models.identity import Organization, ServicePrincipal, User
from src.models.webhook import WebhookDelivery, WebhookTrigger
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.workflow_graph import Expression, Reference, WorkflowGraph
from src.services.audit import record_audit
from src.services.execution_starts import start_execution
from src.services.graph_expressions import ExecutionError, evaluate
from src.services.identity import Principal
from src.services.permissions import authorize, permits
from src.services.retry_runtime import runtime_now
from src.services.tenancy import bind_tenant, tenant_id
from src.services.workflow_definitions import definition, require_runnable_version, version


def get_trigger(db, identity, *, lock=False):
    query = select(WebhookTrigger).where(WebhookTrigger.id == identity)
    if lock:
        query = query.with_for_update()
    item = db.scalar(query.execution_options(populate_existing=True))
    if item is None:
        raise HTTPException(404, "Webhook trigger not found")
    return item


def principal_for(db, identity, *, active=True):
    query = (
        select(ServicePrincipal.role, ServicePrincipal.scopes, ServicePrincipal.user_id)
        .join(User, User.id == ServicePrincipal.user_id)
        .join(Organization, Organization.id == ServicePrincipal.organization_id)
        .where(
            ServicePrincipal.id == identity,
            ServicePrincipal.organization_id == tenant_id(db),
            User.kind == "service",
        )
    )
    if active:
        query = query.where(
            ServicePrincipal.active.is_(True), User.active.is_(True), Organization.active.is_(True)
        )
    row = db.execute(query.with_for_update(read=True)).one_or_none()
    if row is None:
        raise HTTPException(403, "Webhook service principal is unavailable")
    principal = Principal(row.role, row.user_id, tenant_id(db), identity, frozenset(row.scopes))
    if active and not permits(principal, "workflow.start"):
        raise HTTPException(403, "Webhook principal lacks workflow.start permission")
    return principal


def secret_for(organization_id, alias):
    value = settings.webhook_secret_values.get(f"{organization_id}/{alias}")
    if value is None or len(value.get_secret_value().encode()) < 32:
        raise HTTPException(503, "Webhook signing key is unavailable")
    return value.get_secret_value().encode()


def validate_config(db, body, alias):
    item = definition(db, body.definition_id)
    principal_for(db, body.service_principal_id, active=body.enabled)
    if body.version_id:
        version(db, item.id, body.version_id)
    if body.enabled:
        selected = body.version_id or item.published_version_id
        if selected is None:
            raise HTTPException(409, "Webhook requires a published workflow version")
        require_runnable_version(db, item.id, selected)
        secret_for(tenant_id(db), alias)


def public_trigger(item):
    return {
        column.key: getattr(item, column.key)
        for column in item.__table__.columns
        if column.key not in {"secret_alias", "previous_secret_alias"}
    }


def create(db, body):
    actor = authorize(db, "trigger.manage", lock=True)
    validate_config(db, body, body.secret_alias)
    item = WebhookTrigger(**body.model_dump())
    db.add(item)
    db.flush()
    record_audit(db, actor, "webhook.create", "webhook_trigger", item.id, revision=item.revision)
    db.commit()
    return item


def check_revision(item, expected):
    if item.revision != expected:
        raise HTTPException(409, "Webhook configuration changed; reload before editing")


def update(db, identity, body):
    actor = authorize(db, "trigger.manage", lock=True)
    item = get_trigger(db, identity, lock=True)
    check_revision(item, body.expected_revision)
    validate_config(db, body, item.secret_alias)
    for key, value in body.model_dump(exclude={"expected_revision"}).items():
        setattr(item, key, value)
    item.revision += 1
    record_audit(
        db,
        actor,
        "webhook.update",
        "webhook_trigger",
        item.id,
        revision=item.revision,
        enabled=item.enabled,
    )
    db.commit()
    return item


def rotate(db, identity, body):
    actor = authorize(db, "trigger.manage", lock=True)
    item = get_trigger(db, identity, lock=True)
    check_revision(item, body.expected_revision)
    if body.secret_alias == item.secret_alias:
        raise HTTPException(409, "Rotation requires a different signing-key alias")
    secret_for(item.organization_id, body.secret_alias)
    item.previous_secret_alias = item.secret_alias if body.grace_seconds else None
    item.previous_secret_until = (
        runtime_now(db) + timedelta(seconds=body.grace_seconds) if body.grace_seconds else None
    )
    item.secret_alias = body.secret_alias
    item.revision += 1
    record_audit(
        db,
        actor,
        "webhook.rotate",
        "webhook_trigger",
        item.id,
        revision=item.revision,
        grace_seconds=body.grace_seconds,
    )
    db.commit()
    return item


def signed_message(trigger_id, timestamp, event_id, body):
    return f"{trigger_id}\n{timestamp}\n{event_id}\n".encode() + body


def verify(item, timestamp, event_id, signature, body, now):
    if not item.enabled:
        raise HTTPException(403, "Webhook trigger is disabled")
    if len(body) > item.max_payload_bytes:
        raise HTTPException(413, "Webhook payload is too large")
    if (
        not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", event_id)
        or not re.fullmatch(r"(?:0|[1-9][0-9]{0,11})", timestamp)
        or not re.fullmatch(r"sha256=[0-9a-f]{64}", signature)
    ):
        raise HTTPException(401, "Invalid webhook authentication")
    if abs(now.timestamp() - int(timestamp)) > item.freshness_seconds:
        raise HTTPException(401, "Webhook timestamp is outside the freshness window")
    keys = [("current", secret_for(item.organization_id, item.secret_alias))]
    if (
        item.previous_secret_alias
        and item.previous_secret_until
        and now < item.previous_secret_until
    ):
        keys.append(("previous", secret_for(item.organization_id, item.previous_secret_alias)))
    message = signed_message(item.id, timestamp, event_id, body)
    matches = [
        name
        for name, secret in keys
        if hmac.compare_digest(
            signature, "sha256=" + hmac.new(secret, message, hashlib.sha256).hexdigest()
        )
    ]
    if not matches:
        raise HTTPException(401, "Invalid webhook authentication")
    return matches[0]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def map_input(item, body):
    payload = json.loads(body.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object")
    WorkflowGraph.payload_bounds({"input": payload})
    if item.input_mapping is None:
        return payload
    result = {}
    for key, raw in item.input_mapping.items():
        ref = Reference.model_validate(raw)
        if ref.source != "input":
            raise ValueError("Webhook mappings require payload references")
        result[key] = evaluate(Expression(op="ref", ref=ref), payload, {})
        WorkflowGraph.payload_bounds({"input": result})
    return result


def acknowledgement(item, duplicate):
    return {
        "delivery_id": str(item.id),
        "status": item.status,
        "execution_id": str(item.execution_id),
        "version_id": str(item.version_id),
        "duplicate": duplicate,
    }


def receive(db, identity, timestamp, event_id, signature, body):
    try:
        # Public locator reads only the server-owned organization for this opaque ID.
        table = WebhookTrigger.__table__
        owner = (
            db.connection()
            .execute(select(table.c.organization_id).where(table.c.id == identity))
            .scalar_one_or_none()
        )
        if owner is None:
            raise HTTPException(404, "Webhook trigger not found")
        bind_tenant(db, owner)
        trigger = get_trigger(db, identity, lock=True)
        now = runtime_now(db)
        key_kind = verify(trigger, timestamp, event_id, signature, body, now)
        actor = principal_for(db, trigger.service_principal_id)
        db.info["principal"] = actor
        fingerprint = hashlib.sha256(body).hexdigest()
        delivery = db.scalar(
            select(WebhookDelivery).where(
                WebhookDelivery.trigger_id == identity, WebhookDelivery.event_id == event_id
            )
        )
        if delivery is None:
            delivery = WebhookDelivery(
                trigger_id=identity,
                event_id=event_id,
                payload_fingerprint=fingerprint,
                last_attempt_at=now,
            )
            db.add(delivery)
            db.flush()
        else:
            delivery.attempts += 1
            delivery.last_attempt_at = now
        if delivery.payload_fingerprint != fingerprint:
            record_audit(
                db,
                actor,
                "webhook.delivery",
                "webhook_delivery",
                delivery.id,
                outcome="conflict",
                trigger_id=str(identity),
                attempt=delivery.attempts,
            )
            db.commit()
            raise HTTPException(409, "Webhook event ID was already used with different bytes")
        if delivery.status == "accepted":
            result = acknowledgement(delivery, True)
            record_audit(
                db,
                actor,
                "webhook.delivery",
                "webhook_delivery",
                delivery.id,
                outcome="duplicate",
                trigger_id=str(identity),
                attempt=delivery.attempts,
            )
            db.commit()
            return result
        failure = None
        try:
            with db.begin_nested():
                payload = map_input(trigger, body)
                run = start_execution(
                    db,
                    ExecutionStartRequest(
                        definition_id=trigger.definition_id,
                        version_id=trigger.version_id,
                        input=payload,
                        idempotency_key=f"webhook:{delivery.id}",
                    ),
                    commit=False,
                )
            delivery.status, delivery.error_code = "accepted", None
            delivery.execution_id, delivery.version_id = run.id, run.version_id
            delivery.service_principal_id = actor.service_principal_id
            delivery.accepted_revision = trigger.revision
        except HTTPException as error:
            failure = error.status_code
            delivery.status = "rejected"
            delivery.error_code = "input_invalid" if failure == 422 else "workflow_unavailable"
        except (ValueError, TypeError, RecursionError, ExecutionError):
            failure = 422
            delivery.status, delivery.error_code = "rejected", "input_invalid"
        record_audit(
            db,
            actor,
            "webhook.delivery",
            "webhook_delivery",
            delivery.id,
            trigger_id=str(identity),
            outcome=delivery.status,
            error_code=delivery.error_code,
            attempt=delivery.attempts,
            signature_key=key_kind,
            trigger_revision=trigger.revision,
        )
        result = (
            acknowledgement(delivery, False)
            if not failure
            else {
                "delivery_id": str(delivery.id),
                "error_code": delivery.error_code,
            }
        )
        db.commit()
        if failure:
            raise HTTPException(failure, result)
        return result
    except BaseException:
        db.rollback()
        raise
