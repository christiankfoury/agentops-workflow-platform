import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class DurableJob(TenantOwned, Base):
    __tablename__ = "durable_jobs"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "execution_id": "workflow_executions",
                "attempt_id": "step_attempts",
            },
        ),
        UniqueConstraint("execution_id", "sequence", name="uq_execution_job_sequence"),
        CheckConstraint("sequence >= 0"),
        CheckConstraint("recovery_count >= 0"),
        CheckConstraint("status != 'running' OR lease_expires_at IS NOT NULL"),
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed', 'cancelled')"),
        Index("ix_durable_jobs_due", "status", "due_at", "id"),
        Index(
            "ix_durable_jobs_expired",
            "lease_expires_at",
            "id",
            postgresql_where="status = 'running'",
        ),
        Index(
            "uq_execution_active_job",
            "execution_id",
            unique=True,
            postgresql_where="status IN ('queued', 'running')",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID())
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    claim_token: Mapped[uuid.UUID | None] = mapped_column(UUID())
    worker_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(80))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recovery_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


@event.listens_for(Session, "before_flush")
def guard_jobs(db, _context, _instances):
    for item in db.new:
        if isinstance(item, DurableJob) and item.status not in {None, "queued"}:
            raise ValueError("New jobs must be queued")
    if any(isinstance(item, DurableJob) for item in db.dirty | db.deleted):
        raise ValueError("Job updates must use the queue transition authority")
