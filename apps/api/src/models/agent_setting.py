import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.agent_type import AgentType


class AgentSetting(Base):
    __tablename__ = "agent_settings"
    __table_args__ = (
        UniqueConstraint("agent_type", name="uq_agent_settings_agent_type"),
        CheckConstraint(
            "temperature IS NULL OR (temperature >= 0 AND temperature <= 2)",
            name="ck_agent_settings_temperature_range",
        ),
        CheckConstraint("max_tokens > 0", name="ck_agent_settings_max_tokens_positive"),
        CheckConstraint(
            "timeout_seconds IS NULL OR timeout_seconds > 0",
            name="ck_agent_settings_timeout_positive",
        ),
        CheckConstraint("max_retries >= 0", name="ck_agent_settings_max_retries_nonnegative"),
        CheckConstraint(
            "reviewer_approval_threshold IS NULL OR "
            "(reviewer_approval_threshold >= 0 AND reviewer_approval_threshold <= 1)",
            name="ck_agent_settings_reviewer_threshold_range",
        ),
        CheckConstraint(
            "human_approval_threshold IS NULL OR "
            "(human_approval_threshold >= 0 AND human_approval_threshold <= 1)",
            name="ck_agent_settings_human_threshold_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    agent_type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, name="agenttype"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewer_approval_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_approval_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
