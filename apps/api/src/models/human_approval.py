import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base


class ApprovalStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    retry_requested = "retry_requested"


class HumanApproval(Base):
    __tablename__ = "human_approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    issues_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), nullable=False, server_default=ApprovalStatus.pending.value
    )
    human_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_analysis_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
