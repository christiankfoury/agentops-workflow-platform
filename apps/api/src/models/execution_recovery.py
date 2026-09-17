"""One immutable, auditable recovery child per terminal source execution."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class ExecutionRecovery(TenantOwned, Base):
    __tablename__ = "execution_recoveries"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "source_id": "workflow_executions",
                "execution_id": "workflow_executions",
            },
        ),
        UniqueConstraint("source_id"),
        UniqueConstraint("execution_id"),
        CheckConstraint("source_id != execution_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID())
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID())
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(Session, "before_flush")
def retain_recovery(db, _context, _instances):
    for row in db.dirty | db.deleted:
        if isinstance(row, ExecutionRecovery) and (row in db.deleted or db.is_modified(row)):
            raise ValueError("Recovery receipts are immutable")
