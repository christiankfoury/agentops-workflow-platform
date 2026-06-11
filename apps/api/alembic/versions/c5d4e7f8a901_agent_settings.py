"""agent_settings

Revision ID: c5d4e7f8a901
Revises: b4e2a1c9d083
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5d4e7f8a901"
down_revision: str | Sequence[str] | None = "b4e2a1c9d083"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_settings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "agent_type",
            sa.Enum(
                "analyst",
                "reviewer",
                "writer",
                "router",
                "timeline",
                "root_cause",
                "classifier",
                "insight",
                name="agenttype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=True),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("active_prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["active_prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "temperature IS NULL OR (temperature >= 0 AND temperature <= 2)",
            name="ck_agent_settings_temperature_range",
        ),
        sa.CheckConstraint("max_tokens > 0", name="ck_agent_settings_max_tokens_positive"),
        sa.CheckConstraint(
            "timeout_seconds IS NULL OR timeout_seconds > 0",
            name="ck_agent_settings_timeout_positive",
        ),
        sa.CheckConstraint(
            "max_retries >= 0", name="ck_agent_settings_max_retries_nonnegative"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_type", name="uq_agent_settings_agent_type"),
    )


def downgrade() -> None:
    op.drop_table("agent_settings")
