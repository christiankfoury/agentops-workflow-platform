"""Persist deterministic graph edge checkpoints on generic executions."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "f074_execution_checkpoints"
down_revision = "f073_execution_starts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workflow_executions",
        sa.Column("checkpoint_json", JSONB(), nullable=False, server_default="{}"),
    )


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS(SELECT 1 FROM workflow_executions "
                "WHERE checkpoint_json != '{}'::jsonb)"
            )
        )
        .scalar()
    ):
        raise RuntimeError("Retain execution checkpoints before downgrading")
    op.drop_column("workflow_executions", "checkpoint_json")
