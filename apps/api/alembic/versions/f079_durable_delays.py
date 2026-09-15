"""Persist delay waits independently of worker leases."""

import sqlalchemy as sa

from alembic import op

revision = "f079_durable_delays"
down_revision = "f078_execution_cancellation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET CONSTRAINTS ALL IMMEDIATE")
    op.add_column("step_runs", sa.Column("waiting_reason", sa.String(40)))
    op.add_column("step_runs", sa.Column("wake_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_step_delay_wake",
        "step_runs",
        ["wake_at", "id"],
        postgresql_where=sa.text("status = 'waiting'"),
    )
    op.execute("SET CONSTRAINTS ALL DEFERRED")


def downgrade():
    if (
        op.get_bind()
        .execute(sa.text("SELECT EXISTS(SELECT 1 FROM step_runs WHERE waiting_reason IS NOT NULL)"))
        .scalar()
    ):
        raise RuntimeError("Retain execution wait history before downgrading")
    op.drop_index("ix_step_delay_wake", "step_runs")
    op.drop_column("step_runs", "wake_at")
    op.drop_column("step_runs", "waiting_reason")
