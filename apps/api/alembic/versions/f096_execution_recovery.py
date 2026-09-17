"""Retained terminal recovery receipts and logical step provenance."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "f096_execution_recovery"
down_revision = "f092_workflow_schedules"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "execution_recoveries",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column("organization_id", UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("source_id", UUID(), nullable=False, unique=True),
        sa.Column("execution_id", UUID(), nullable=False, unique=True),
        sa.Column("actor_id", UUID(), sa.ForeignKey("users.id")),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "id", "organization_id", name="uq_execution_recoveries_tenant_identity"
        ),
        sa.CheckConstraint("source_id != execution_id"),
        *(
            sa.ForeignKeyConstraint(
                [column, "organization_id"],
                ["workflow_executions.id", "workflow_executions.organization_id"],
                name=f"fk_execution_recoveries_{column}_tenant",
                deferrable=True,
                initially="DEFERRED",
            )
            for column in ["source_id", "execution_id"]
        ),
    )
    op.create_index(
        "ix_execution_recoveries_organization_id", "execution_recoveries", ["organization_id"]
    )
    op.add_column("step_runs", sa.Column("recovered_from_id", UUID()))
    op.create_foreign_key(
        "fk_step_runs_recovered_from_id_tenant",
        "step_runs",
        "step_runs",
        ["recovered_from_id", "organization_id"],
        ["id", "organization_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute("""
    CREATE FUNCTION preserve_recovery_history() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME = 'execution_recoveries' THEN
        RAISE EXCEPTION 'Recovery receipts are immutable';
      END IF;
      IF NEW.recovered_from_id IS DISTINCT FROM OLD.recovered_from_id THEN
        RAISE EXCEPTION 'Recovery provenance is immutable';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER recovery_history BEFORE UPDATE OR DELETE ON execution_recoveries
      FOR EACH ROW EXECUTE FUNCTION preserve_recovery_history();
    CREATE TRIGGER recovery_provenance BEFORE UPDATE ON step_runs
      FOR EACH ROW EXECUTE FUNCTION preserve_recovery_history();
    """)


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM execution_recoveries)")):
        raise RuntimeError("Retain recovery receipts before downgrading")
    op.execute("DROP TRIGGER recovery_provenance ON step_runs")
    op.drop_constraint("fk_step_runs_recovered_from_id_tenant", "step_runs", type_="foreignkey")
    op.drop_column("step_runs", "recovered_from_id")
    op.drop_table("execution_recoveries")
    op.execute("DROP FUNCTION preserve_recovery_history()")
