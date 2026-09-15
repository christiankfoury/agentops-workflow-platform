"""Add a fencing revision for legacy workflow transactions."""

import sqlalchemy as sa
from alembic import op

revision = "f066_state_revision"
down_revision = "e7f8a9b0c123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column(
        "state_revision", sa.Integer(), nullable=False, server_default="0",
    ))
    op.execute("ALTER TYPE workfloweventtype ADD VALUE IF NOT EXISTS 'state_transition'")


def downgrade() -> None:
    op.drop_column("workflow_runs", "state_revision")
    # Retain the additive PostgreSQL enum label for historical event readability.
