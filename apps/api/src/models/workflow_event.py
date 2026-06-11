import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base


class WorkflowEventType(StrEnum):
    workflow_started = "workflow_started"
    workflow_completed = "workflow_completed"
    workflow_failed = "workflow_failed"
    workflow_cancelled = "workflow_cancelled"
    agent_started = "agent_started"
    agent_completed = "agent_completed"
    agent_failed = "agent_failed"
    reviewer_rejected_output = "reviewer_rejected_output"
    retry_triggered = "retry_triggered"
    human_approval_required = "human_approval_required"
    human_edited_analysis = "human_edited_analysis"
    human_approved = "human_approved"
    human_rejected = "human_rejected"
    human_requested_retry = "human_requested_retry"


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_steps.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[WorkflowEventType] = mapped_column(Enum(WorkflowEventType), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
