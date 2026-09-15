import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class WorkflowDefinition(TenantOwned, Base):
    __tablename__ = "workflow_definitions"
    __table_args__ = (
        *tenant_constraints(__tablename__),
        CheckConstraint("draft_revision >= 1"),
        ForeignKeyConstraint(
            ["published_version_id", "id", "organization_id"],
            [
                "workflow_versions.id",
                "workflow_versions.definition_id",
                "workflow_versions.organization_id",
            ],
            name="fk_definition_published_version",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    draft_graph: Mapped[dict] = mapped_column(JSONB)
    draft_revision: Mapped[int] = mapped_column(Integer, default=1)
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class WorkflowVersion(TenantOwned, Base):
    __tablename__ = "workflow_versions"
    __table_args__ = (
        *tenant_constraints(__tablename__, {"definition_id": "workflow_definitions"}),
        UniqueConstraint("definition_id", "number", name="uq_workflow_version_number"),
        UniqueConstraint(
            "id", "definition_id", "organization_id", name="uq_workflow_version_definition"
        ),
        CheckConstraint("number >= 1 AND source_revision >= 1"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(UUID())
    number: Mapped[int] = mapped_column(Integer)
    source_revision: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    graph: Mapped[dict] = mapped_column(JSONB)
    graph_hash: Mapped[str] = mapped_column(String(64))
    prompt_snapshots: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowVersionPrompt(TenantOwned, Base):
    """Retain source prompts as well as their immutable publication snapshot."""

    __tablename__ = "workflow_version_prompts"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "version_id": "workflow_versions",
                "prompt_id": "prompt_versions",
            },
        ),
        UniqueConstraint("version_id", "prompt_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID())
    prompt_id: Mapped[uuid.UUID] = mapped_column(UUID())


@event.listens_for(Session, "before_flush")
def immutable_versions(db, _context, _instances):
    for item in db.dirty | db.deleted:
        if isinstance(item, WorkflowVersionPrompt):
            raise ValueError("Published prompt links are immutable")
        if isinstance(item, WorkflowVersion):
            if item in db.deleted or any(
                attr.history.has_changes()
                for attr in inspect(item).attrs
                if attr.key != "archived_at"
            ):
                raise ValueError("Published workflow versions are immutable")
