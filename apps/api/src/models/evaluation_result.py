import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, Text, event, inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints
from src.models.workflow_run import RunMode, WorkflowType


class EvaluationRunStatus(StrEnum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class EvaluationResult(TenantOwned, Base):
    __tablename__ = "evaluation_results"
    __table_args__ = tenant_constraints(
        __tablename__,
        {"evaluation_case_id": "evaluation_cases", "workflow_run_id": "workflow_runs"},
    )

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
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    automatic_approval: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    approval_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    derive_expected: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    prompt_version_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    factual_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    unsupported_claim_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    router_detected_workflow_type: Mapped[WorkflowType | None] = mapped_column(
        Enum(WorkflowType, name="workflowtype"), nullable=True
    )
    router_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    router_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    human_approval_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    human_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


@event.listens_for(EvaluationResult, "before_update")
def immutable_evaluation_intent(_mapper, _connection, result):
    for name in ["requested_by_user_id", "automatic_approval", "derive_expected"]:
        if inspect(result).attrs[name].history.has_changes():
            raise ValueError("Evaluation approval intent is immutable")
    for name in ["workflow_run_id", "evaluation_case_id", "run_mode"]:
        history = inspect(result).attrs[name].history
        if history.has_changes() and history.deleted and history.deleted[0] is not None:
            raise ValueError("Evaluation run binding is immutable")
