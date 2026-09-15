import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class ExecutionStart(TenantOwned, Base):
    __tablename__ = "execution_starts"
    __table_args__ = (
        *tenant_constraints(__tablename__, {"execution_id": "workflow_executions"}),
        UniqueConstraint("organization_id", "key", name="uq_execution_start_key"),
        UniqueConstraint("execution_id", name="uq_execution_start_run"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(128))
    fingerprint: Mapped[str] = mapped_column(String(64))
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(Session, "before_flush")
def preserve_start_receipts(db, _context, _instances):
    if any(isinstance(item, ExecutionStart) for item in db.dirty | db.deleted):
        raise ValueError("Execution start receipts are immutable and cannot expire or be reused")
