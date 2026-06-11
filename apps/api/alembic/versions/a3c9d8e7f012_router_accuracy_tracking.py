"""router_accuracy_tracking

Revision ID: a3c9d8e7f012
Revises: 7a1d2c3e4f56
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a3c9d8e7f012"
down_revision: str | Sequence[str] | None = "7a1d2c3e4f56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

workflow_type_enum = postgresql.ENUM(
    "sales_report",
    "customer_feedback",
    "incident_log",
    name="workflowtype",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "evaluation_results",
        sa.Column("router_detected_workflow_type", workflow_type_enum, nullable=True),
    )
    op.add_column("evaluation_results", sa.Column("router_confidence", sa.Float(), nullable=True))
    op.add_column("evaluation_results", sa.Column("router_correct", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluation_results", "router_correct")
    op.drop_column("evaluation_results", "router_confidence")
    op.drop_column("evaluation_results", "router_detected_workflow_type")
