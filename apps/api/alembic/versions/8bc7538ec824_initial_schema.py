"""initial_schema

Revision ID: 8bc7538ec824
Revises:
Create Date: 2026-06-10 13:33:57.511154

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8bc7538ec824"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "uploaded_inputs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "input_type",
            sa.Enum("sales_report", "customer_feedback", "incident_log", name="inputtype"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_type", sa.String(50), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "prompt_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "workflow_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "workflow_type",
            sa.Enum("sales_report", "customer_feedback", "incident_log", name="workflowtype"),
            nullable=False,
        ),
        sa.Column(
            "run_mode",
            sa.Enum("baseline", "multi_agent", name="runmode"),
            server_default="multi_agent",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "created",
                "running",
                "routing",
                "analyst_running",
                "reviewer_running",
                "retrying",
                "waiting_for_human",
                "writer_running",
                "completed",
                "failed",
                "cancelled",
                name="workflowstatus",
            ),
            server_default="created",
            nullable=False,
        ),
        sa.Column("input_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("final_output", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("total_cost", sa.Float(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["input_id"], ["uploaded_inputs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_steps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="agentstepstatus"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("input_json", postgresql.JSONB(), nullable=True),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "human_approvals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_score", sa.Float(), nullable=True),
        sa.Column("issues_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "approved", "rejected", "retry_requested", name="approvalstatus"
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("human_feedback", sa.Text(), nullable=True),
        sa.Column("edited_analysis_json", postgresql.JSONB(), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "cost_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=False),
        sa.Column("tokens_output", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_input", sa.Float(), nullable=False),
        sa.Column("cost_output", sa.Float(), nullable=False),
        sa.Column("total_cost", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_step_id"], ["agent_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("cost_events")
    op.drop_table("human_approvals")
    op.drop_table("agent_steps")
    op.drop_table("workflow_runs")
    op.drop_table("prompt_versions")
    op.drop_table("uploaded_inputs")
    op.execute("DROP TYPE IF EXISTS approvalstatus")
    op.execute("DROP TYPE IF EXISTS agentstepstatus")
    op.execute("DROP TYPE IF EXISTS workflowstatus")
    op.execute("DROP TYPE IF EXISTS runmode")
    op.execute("DROP TYPE IF EXISTS workflowtype")
    op.execute("DROP TYPE IF EXISTS inputtype")
