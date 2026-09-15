import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class AuditEvent(TenantOwned, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        *tenant_constraints(__tablename__),
        CheckConstraint("actor_kind IN ('user', 'service', 'local')"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    service_principal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_principals.id")
    )
    actor_kind: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(255))
    details_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(Session, "before_flush")
def immutable_audit(db, _context, _instances):
    if any(isinstance(item, AuditEvent) for item in db.dirty | db.deleted):
        raise ValueError("Audit events are immutable")
