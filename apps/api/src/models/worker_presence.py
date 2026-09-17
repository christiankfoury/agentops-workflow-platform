"""Infrastructure liveness only; never exposed as tenant worker identities."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class WorkerPresence(Base):
    __tablename__ = "worker_presence"
    __table_args__ = (
        CheckConstraint("capacity BETWEEN 1 AND 32"),
        CheckConstraint("status IN ('running', 'draining', 'stopped')"),
    )
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    capacity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
