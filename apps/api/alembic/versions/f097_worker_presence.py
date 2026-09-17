"""Ephemeral worker presence; durable events remain the metric authority."""

import sqlalchemy as sa

from alembic import op

revision = "f097_worker_presence"
down_revision = "f096_execution_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "worker_presence",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("capacity BETWEEN 1 AND 32"),
        sa.CheckConstraint("status IN ('running', 'draining', 'stopped')"),
    )
    op.create_index("ix_worker_presence_expires_at", "worker_presence", ["expires_at"])


def downgrade():
    op.drop_table("worker_presence")
