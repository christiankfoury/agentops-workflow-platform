"""evaluation_dataset

Revision ID: 7a1d2c3e4f56
Revises: 9f4d8a7c6b21
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7a1d2c3e4f56"
down_revision: str | Sequence[str] | None = "9f4d8a7c6b21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

evaluation_run_status_enum = postgresql.ENUM(
    "pending",
    "completed",
    "failed",
    name="evaluationrunstatus",
)
workflow_type_enum = postgresql.ENUM(
    "sales_report",
    "customer_feedback",
    "incident_log",
    name="workflowtype",
    create_type=False,
)
run_mode_enum = postgresql.ENUM(
    "baseline",
    "multi_agent",
    name="runmode",
    create_type=False,
)


def upgrade() -> None:
    evaluation_run_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "evaluation_cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workflow_type", workflow_type_enum, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("expected_facts_json", postgresql.JSONB(), nullable=False),
        sa.Column("expected_risks_json", postgresql.JSONB(), nullable=False),
        sa.Column("expected_recommendations_json", postgresql.JSONB(), nullable=False),
        sa.Column("expected_themes_json", postgresql.JSONB(), nullable=True),
        sa.Column("expected_timeline_json", postgresql.JSONB(), nullable=True),
        sa.Column("expected_output_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_type", "title", name="uq_evaluation_cases_type_title"),
    )
    op.create_table(
        "evaluation_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("evaluation_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_mode", run_mode_enum, nullable=False),
        sa.Column(
            "status",
            evaluation_run_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("prompt_version_summary_json", postgresql.JSONB(), nullable=True),
        sa.Column("factual_accuracy", sa.Float(), nullable=True),
        sa.Column("unsupported_claim_rate", sa.Float(), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("human_approval_required", sa.Boolean(), nullable=True),
        sa.Column("human_approved", sa.Boolean(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("judge_notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_case_id"], ["evaluation_cases.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evaluation_results_case_mode",
        "evaluation_results",
        ["evaluation_case_id", "run_mode"],
    )


def downgrade() -> None:
    op.drop_index("ix_evaluation_results_case_mode", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_cases")
    evaluation_run_status_enum.drop(op.get_bind(), checkfirst=True)
