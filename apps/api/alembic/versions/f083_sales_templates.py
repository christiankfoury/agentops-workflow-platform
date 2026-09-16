"""One durable owner per compatibility run; historical runs are unchanged."""

import sqlalchemy as sa

from alembic import op

revision = "f083_sales_templates"
down_revision = "f082_execution_config"
branch_labels = None
depends_on = None


def upgrade():
    for value in ["superseded", "expired", "cancelled", "invalidated"]:
        op.execute(f"ALTER TYPE approvalstatus ADD VALUE IF NOT EXISTS '{value}'")
    op.create_unique_constraint("uq_execution_legacy_run", "workflow_executions", ["legacy_run_id"])


def downgrade():
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS(SELECT 1 FROM workflow_executions WHERE legacy_run_id IS NOT NULL)")
    ):
        raise RuntimeError("Retain durable ownership of migrated business runs before downgrading")
    op.drop_constraint("uq_execution_legacy_run", "workflow_executions", type_="unique")
