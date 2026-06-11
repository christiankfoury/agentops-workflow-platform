"""workflow_events

Revision ID: 9f4d8a7c6b21
Revises: 5c2c102f9f2e
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "9f4d8a7c6b21"
down_revision: str | Sequence[str] | None = "5c2c102f9f2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

workflow_event_type_enum = postgresql.ENUM(
    "workflow_started",
    "workflow_completed",
    "workflow_failed",
    "agent_started",
    "agent_completed",
    "agent_failed",
    "reviewer_rejected_output",
    "retry_triggered",
    "human_approval_required",
    "human_approved",
    "human_rejected",
    "human_requested_retry",
    name="workfloweventtype",
)
workflow_event_type_existing_enum = postgresql.ENUM(
    name="workfloweventtype",
    create_type=False,
)


def upgrade() -> None:
    workflow_event_type_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "workflow_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", workflow_event_type_existing_enum, nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_step_id"], ["agent_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_events_run_created_at",
        "workflow_events",
        ["workflow_run_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_events_run_created_at", table_name="workflow_events")
    op.drop_table("workflow_events")
    workflow_event_type_enum.drop(op.get_bind(), checkfirst=True)
