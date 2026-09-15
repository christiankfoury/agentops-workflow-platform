import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.agent_type import AgentType
from src.models.tenant import TenantOwned, tenant_constraints


class PromptVersion(TenantOwned, Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        *tenant_constraints(__tablename__),
        UniqueConstraint(
            "organization_id",
            "agent_type",
            "name",
            "version",
            name="uq_prompt_versions_agent_name_version",
        ),
        Index(
            "ix_prompt_versions_active_agent_name",
            "organization_id",
            "agent_type",
            "name",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType, name="agenttype"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
