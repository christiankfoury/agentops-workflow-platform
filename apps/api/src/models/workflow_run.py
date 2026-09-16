import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class WorkflowType(StrEnum):
    sales_report = "sales_report"
    customer_feedback = "customer_feedback"
    incident_log = "incident_log"


class RunMode(StrEnum):
    baseline = "baseline"
    multi_agent = "multi_agent"


class WorkflowStatus(StrEnum):
    created = "created"
    running = "running"
    routing = "routing"
    analyst_running = "analyst_running"
    reviewer_running = "reviewer_running"
    retrying = "retrying"
    waiting_for_human = "waiting_for_human"
    writer_running = "writer_running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class WorkflowRun(TenantOwned, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = tenant_constraints(__tablename__, {"input_id": "uploaded_inputs"})

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    workflow_type: Mapped[WorkflowType] = mapped_column(Enum(WorkflowType), nullable=False)
    run_mode: Mapped[RunMode] = mapped_column(
        Enum(RunMode), nullable=False, server_default=RunMode.multi_agent.value
    )
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), nullable=False, server_default=WorkflowStatus.created.value
    )
    input_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_inputs.id", ondelete="SET NULL"),
        nullable=True,
    )
    final_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    state_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    @property
    def execution_id(self):
        from sqlalchemy.orm import object_session

        from src.services.business_projection import execution_for

        db = object_session(self)
        source = execution_for(db, self.id) if db is not None else None
        return source.id if source is not None else None
