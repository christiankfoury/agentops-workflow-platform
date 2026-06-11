"""agent_review_thresholds

Revision ID: d6e7f8a9b012
Revises: c5d4e7f8a901
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b012"
down_revision: str | Sequence[str] | None = "c5d4e7f8a901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_settings",
        sa.Column("reviewer_approval_threshold", sa.Float(), nullable=True),
    )
    op.add_column(
        "agent_settings",
        sa.Column("human_approval_threshold", sa.Float(), nullable=True),
    )
    op.create_check_constraint(
        "ck_agent_settings_reviewer_threshold_range",
        "agent_settings",
        "reviewer_approval_threshold IS NULL OR "
        "(reviewer_approval_threshold >= 0 AND reviewer_approval_threshold <= 1)",
    )
    op.create_check_constraint(
        "ck_agent_settings_human_threshold_range",
        "agent_settings",
        "human_approval_threshold IS NULL OR "
        "(human_approval_threshold >= 0 AND human_approval_threshold <= 1)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_agent_settings_human_threshold_range",
        "agent_settings",
        type_="check",
    )
    op.drop_constraint(
        "ck_agent_settings_reviewer_threshold_range",
        "agent_settings",
        type_="check",
    )
    op.drop_column("agent_settings", "human_approval_threshold")
    op.drop_column("agent_settings", "reviewer_approval_threshold")
