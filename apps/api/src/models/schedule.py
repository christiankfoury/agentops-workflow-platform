"""Retained schedule identities and immutable per-fire outcomes."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
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


class WorkflowSchedule(TenantOwned, Base):
    __tablename__ = "workflow_schedules"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "definition_id": "workflow_definitions",
                "service_principal_id": "service_principals",
                "active_execution_id": "workflow_executions",
            },
        ),
        ForeignKeyConstraint(
            ["version_id", "definition_id", "organization_id"],
            [
                "workflow_versions.id",
                "workflow_versions.definition_id",
                "workflow_versions.organization_id",
            ],
            name="fk_schedule_version_definition",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("revision >= 1"),
        CheckConstraint(
            "(version_policy = 'published' AND version_id IS NULL) OR "
            "(version_policy = 'pinned' AND version_id IS NOT NULL)"
        ),
        CheckConstraint("concurrency_policy = 'forbid' AND missed_run_policy = 'coalesce'"),
        Index("ix_schedule_due", "enabled", "next_fire_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    definition_id: Mapped[uuid.UUID] = mapped_column(UUID())
    version_policy: Mapped[str] = mapped_column(String(16), default="published")
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    service_principal_id: Mapped[uuid.UUID] = mapped_column(UUID())
    cron: Mapped[str] = mapped_column(String(160))
    timezone: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    concurrency_policy: Mapped[str] = mapped_column(String(16), default="forbid")
    missed_run_policy: Mapped[str] = mapped_column(String(16), default="coalesce")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    next_fire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_fire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(16))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    active_execution_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScheduleFire(TenantOwned, Base):
    __tablename__ = "schedule_fires"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "schedule_id": "workflow_schedules",
                "execution_id": "workflow_executions",
                "version_id": "workflow_versions",
                "service_principal_id": "service_principals",
            },
        ),
        UniqueConstraint("schedule_id", "scheduled_at"),
        CheckConstraint("revision >= 1"),
        CheckConstraint("status IN ('accepted', 'rejected', 'skipped')"),
        CheckConstraint(
            "status != 'accepted' OR (execution_id IS NOT NULL "
            "AND version_id IS NOT NULL AND error_code IS NULL)"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID] = mapped_column(UUID(), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    coalesced: Mapped[bool] = mapped_column(Boolean)
    error_code: Mapped[str | None] = mapped_column(String(80))
    execution_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    service_principal_id: Mapped[uuid.UUID] = mapped_column(UUID())


@event.listens_for(Session, "before_flush")
def retain_schedule_history(db, _context, _instances):
    for item in db.dirty | db.deleted:
        if isinstance(item, ScheduleFire):
            raise ValueError("Schedule fire outcomes are immutable")
        if isinstance(item, WorkflowSchedule):
            if item in db.deleted:
                raise ValueError("Retain schedule configuration and fire history")
            if any(inspect(item).attrs[key].history.has_changes() for key in ["id", "created_at"]):
                raise ValueError("Schedule identity is immutable")
