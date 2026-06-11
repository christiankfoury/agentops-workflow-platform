import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.workflow_run import WorkflowType


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    workflow_type: Mapped[WorkflowType] = mapped_column(
        Enum(WorkflowType, name="workflowtype"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_facts_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    expected_risks_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    expected_recommendations_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    expected_themes_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    expected_timeline_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    expected_output_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
