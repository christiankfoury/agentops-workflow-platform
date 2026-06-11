import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.workflow_run import RunMode


class EvaluationRunStatus(StrEnum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    evaluation_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_mode: Mapped[RunMode] = mapped_column(Enum(RunMode, name="runmode"), nullable=False)
    status: Mapped[EvaluationRunStatus] = mapped_column(
        Enum(EvaluationRunStatus), nullable=False, server_default=EvaluationRunStatus.pending.value
    )
    prompt_version_summary_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    factual_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    unsupported_claim_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_approval_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    human_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
