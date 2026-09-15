import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
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
from src.models.workflow_execution import WorkflowExecution


class ExecutionApproval(TenantOwned, Base):
    __tablename__ = "execution_approvals"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "execution_id": "workflow_executions",
                "step_run_id": "step_runs",
                "version_id": "workflow_versions",
            },
        ),
        UniqueConstraint("step_run_id", "revision", name="uq_approval_snapshot_revision"),
        CheckConstraint("revision >= 1 AND iteration >= 0"),
        CheckConstraint(
            "status IN ('pending','approved','rejected','retry_requested',"
            "'superseded','invalidated','cancelled','expired')"
        ),
        Index(
            "uq_pending_execution_approval",
            "step_run_id",
            unique=True,
            postgresql_where="status = 'pending'",
        ),
        Index("ix_approval_expiry", "expires_at", "id", postgresql_where="status = 'pending'"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID())
    step_run_id: Mapped[uuid.UUID] = mapped_column(UUID())
    version_id: Mapped[uuid.UUID] = mapped_column(UUID())
    node_id: Mapped[str] = mapped_column(String(64))
    iteration: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    source_hash: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict] = mapped_column(JSONB)
    review_json: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    human_feedback: Mapped[str | None] = mapped_column(String(4000))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    replacement_id: Mapped[uuid.UUID | None] = mapped_column(UUID())


@event.listens_for(Session, "before_flush")
def preserve_approvals(db, _context, _instances):
    fixed = {
        "id",
        "execution_id",
        "step_run_id",
        "version_id",
        "node_id",
        "iteration",
        "revision",
        "source_hash",
        "payload_hash",
        "payload_json",
        "review_json",
        "expires_at",
        "created_at",
    }
    for item in db.new | db.dirty | db.deleted:
        if not isinstance(item, ExecutionApproval):
            continue
        if db.info.get("workflow_transaction") != (WorkflowExecution, item.execution_id):
            raise ValueError("Approval changes require their execution transaction")
        if item in db.new:
            if item.status not in {None, "pending"}:
                raise ValueError("Approvals must begin pending")
            continue
        state = inspect(item)
        prior = state.attrs.status.history.deleted
        if item in db.deleted or (
            db.is_modified(item)
            and (
                (prior[0] if prior else item.status) != "pending"
                or any(state.attrs[key].history.has_changes() for key in fixed)
            )
        ):
            raise ValueError("Approval snapshots and resolved history are immutable")
