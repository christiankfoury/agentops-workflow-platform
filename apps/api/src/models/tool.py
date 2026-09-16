"""Versioned tool metadata and one durable record per logical external action."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class ToolCredential(TenantOwned, Base):
    __tablename__ = "tool_credentials"
    __table_args__ = (
        *tenant_constraints(__tablename__),
        UniqueConstraint("organization_id", "source_alias"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    source_alias: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ToolDefinition(TenantOwned, Base):
    __tablename__ = "tool_definitions"
    __table_args__ = tenant_constraints(__tablename__)
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ToolVersion(TenantOwned, Base):
    __tablename__ = "tool_versions"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {"definition_id": "tool_definitions", "credential_ref": "tool_credentials"},
        ),
        UniqueConstraint("definition_id", "number"),
        CheckConstraint("number >= 1"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(UUID())
    number: Mapped[int] = mapped_column(Integer)
    credential_ref: Mapped[uuid.UUID | None] = mapped_column(UUID())
    contract: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ToolExecution(TenantOwned, Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "version_id": "tool_versions",
                "step_run_id": "step_runs",
                "attempt_id": "step_attempts",
            },
        ),
        UniqueConstraint("organization_id", "effect_key"),
        CheckConstraint("status IN ('pending','succeeded','failed','unknown','reconciled')"),
        CheckConstraint("attempts >= 0"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID())
    step_run_id: Mapped[uuid.UUID] = mapped_column(UUID(), index=True)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID())
    call_id: Mapped[str] = mapped_column(String(100))
    effect_key: Mapped[str] = mapped_column(String(64))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    credential_digest: Mapped[str | None] = mapped_column(String(64))
    request_json: Mapped[dict] = mapped_column(JSONB)
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    claim_token: Mapped[uuid.UUID | None] = mapped_column(UUID())
    reservation_token: Mapped[uuid.UUID | None] = mapped_column(UUID())
    dispatched: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(80))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    reconciliation: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


@event.listens_for(Session, "before_flush")
def preserve_tool_history(db, _context, _instances):
    for item in db.new:
        if isinstance(item, ToolExecution) and item.status not in {None, "pending"}:
            raise ValueError("New tool effects must begin pending")
    for item in db.dirty | db.deleted:
        if not isinstance(item, (ToolCredential, ToolDefinition, ToolVersion, ToolExecution)):
            continue
        if item in db.deleted:
            raise ValueError("Retain tool contracts and effect history")
        frozen = {
            ToolCredential: ("source_alias",),
            ToolDefinition: (),
            ToolVersion: tuple(inspect(ToolVersion).columns.keys()),
            ToolExecution: (
                "version_id",
                "step_run_id",
                "attempt_id",
                "call_id",
                "effect_key",
                "request_fingerprint",
                "request_json",
            ),
        }[type(item)]
        if any(inspect(item).attrs[name].history.has_changes() for name in frozen):
            raise ValueError("Tool contract and effect identity are immutable")
        if isinstance(item, ToolExecution):
            credential_history = inspect(item).attrs.credential_digest.history
            if (
                credential_history.has_changes()
                and credential_history.deleted
                and credential_history.deleted[0] is not None
            ):
                raise ValueError("Tool credential binding is immutable")
            history = inspect(item).attrs.status.history
            previous = history.deleted[0] if history.deleted else item.status
            if previous in {"succeeded", "reconciled"} and db.is_modified(item):
                raise ValueError("Confirmed tool outcomes are immutable")
