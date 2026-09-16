"""Tenant-owned webhook routing and retained delivery identities."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class WebhookTrigger(TenantOwned, Base):
    __tablename__ = "webhook_triggers"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {"definition_id": "workflow_definitions", "service_principal_id": "service_principals"},
        ),
        ForeignKeyConstraint(
            ["version_id", "definition_id", "organization_id"],
            [
                "workflow_versions.id",
                "workflow_versions.definition_id",
                "workflow_versions.organization_id",
            ],
            name="fk_webhook_version_definition",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("revision >= 1"),
        CheckConstraint(
            "(version_policy = 'published' AND version_id IS NULL) OR "
            "(version_policy = 'pinned' AND version_id IS NOT NULL)"
        ),
        CheckConstraint(
            "max_payload_bytes BETWEEN 1024 AND 262144 AND freshness_seconds BETWEEN 30 AND 600"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    definition_id: Mapped[uuid.UUID] = mapped_column(UUID())
    version_policy: Mapped[str] = mapped_column(String(16), default="published")
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    service_principal_id: Mapped[uuid.UUID] = mapped_column(UUID())
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    input_mapping: Mapped[dict | None] = mapped_column(JSONB)
    max_payload_bytes: Mapped[int] = mapped_column(Integer, default=65536)
    freshness_seconds: Mapped[int] = mapped_column(Integer, default=300)
    secret_alias: Mapped[str] = mapped_column(String(100))
    previous_secret_alias: Mapped[str | None] = mapped_column(String(100))
    previous_secret_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookDelivery(TenantOwned, Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "trigger_id": "webhook_triggers",
                "execution_id": "workflow_executions",
                "version_id": "workflow_versions",
                "service_principal_id": "service_principals",
            },
        ),
        UniqueConstraint("trigger_id", "event_id"),
        CheckConstraint("attempts >= 1"),
        CheckConstraint("status IN ('pending','accepted','rejected')"),
        CheckConstraint(
            "status != 'accepted' OR (execution_id IS NOT NULL AND version_id IS NOT NULL "
            "AND service_principal_id IS NOT NULL AND accepted_revision IS NOT NULL "
            "AND error_code IS NULL)"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    trigger_id: Mapped[uuid.UUID] = mapped_column(UUID(), index=True)
    event_id: Mapped[str] = mapped_column(String(128))
    payload_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    execution_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    service_principal_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    accepted_revision: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


@event.listens_for(Session, "before_flush")
def retain_webhook_history(db, _context, _instances):
    for item in db.dirty | db.deleted:
        if not isinstance(item, (WebhookTrigger, WebhookDelivery)):
            continue
        if item in db.deleted:
            raise ValueError("Retain webhook configuration and delivery history")
        frozen = ["id", "created_at"]
        if isinstance(item, WebhookDelivery):
            frozen += ["trigger_id", "event_id", "payload_fingerprint"]
            history = inspect(item).attrs.status.history
            old = history.deleted[0] if history.deleted else item.status
            if old == "accepted":
                frozen += [
                    "status",
                    "execution_id",
                    "version_id",
                    "service_principal_id",
                    "accepted_revision",
                    "error_code",
                ]
        if any(inspect(item).attrs[key].history.has_changes() for key in frozen):
            raise ValueError("Webhook identity and accepted outcomes are immutable")
