"""Authorized metadata operations; never read credential values on the API path."""

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.models.tool import ToolCredential, ToolDefinition, ToolVersion
from src.services.audit import record_audit
from src.services.permissions import authorize


def get(db, model, identity, *, lock=False):
    query = select(model).where(model.id == identity).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise HTTPException(404, "Tool resource not found")
    return item


def create_credential(db, body):
    principal = authorize(db, "credentials.manage", lock=True)
    item = ToolCredential(**body.model_dump())
    db.add(item)
    try:
        db.flush()
        record_audit(db, principal, "tool.credential.create", "tool_credential", item.id)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Credential alias already exists") from error
    return item


def set_active(db, model, identity, active):
    principal = authorize(
        db, "credentials.manage" if model is ToolCredential else "tool.manage", lock=True
    )
    item = get(db, model, identity, lock=True)
    item.active = active
    record_audit(db, principal, "tool.activation", model.__tablename__, identity, active=active)
    db.commit()
    return item


def add_version(db, item, contract, number, principal):
    if contract.credential_ref:
        credential = get(db, ToolCredential, contract.credential_ref, lock=True)
        if not credential.active:
            raise HTTPException(409, "Tool credential is revoked")
    version = ToolVersion(
        definition_id=item.id,
        number=number,
        credential_ref=contract.credential_ref,
        contract=contract.model_dump(mode="json"),
    )
    db.add(version)
    db.flush()
    record_audit(db, principal, "tool.publish", "tool_version", version.id, number=number)
    db.commit()
    return version


def create(db, body):
    principal = authorize(db, "tool.manage", lock=True)
    item = ToolDefinition(name=body.name, description=body.description)
    db.add(item)
    db.flush()
    return add_version(db, item, body.contract, 1, principal)


def publish(db, identity, body):
    principal = authorize(db, "tool.manage", lock=True)
    item = get(db, ToolDefinition, identity, lock=True)
    number = db.scalar(
        select(func.max(ToolVersion.number)).where(ToolVersion.definition_id == identity)
    )
    if not item.active or number != body.expected_version:
        raise HTTPException(409, "Tool changed or is disabled; reload before publishing")
    return add_version(db, item, body.contract, number + 1, principal)


def public(item):
    hidden = {"claim_token", "reservation_token", "credential_digest"}
    return {
        column.key: getattr(item, column.key)
        for column in item.__table__.columns
        if column.key not in hidden
    }
