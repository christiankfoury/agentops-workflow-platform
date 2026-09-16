"""Durable schedule configuration and immutable fire receipts."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f092_workflow_schedules"
down_revision = "f091_webhook_triggers"
branch_labels = None
depends_on = None


def table(name, columns, references, constraints):
    op.create_table(
        name,
        sa.Column("id", UUID(), primary_key=True),
        sa.Column("organization_id", UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        *columns,
        sa.UniqueConstraint("id", "organization_id", name=f"uq_{name}_tenant_identity"),
        *(
            sa.ForeignKeyConstraint(
                [column, "organization_id"],
                [f"{target}.id", f"{target}.organization_id"],
                name=f"fk_{name}_{column}_tenant",
                deferrable=True,
                initially="DEFERRED",
            )
            for column, target in references.items()
        ),
        *constraints,
    )
    op.create_index(f"ix_{name}_organization_id", name, ["organization_id"])


def upgrade():
    table(
        "workflow_schedules",
        [
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("definition_id", UUID(), nullable=False),
            sa.Column("version_policy", sa.String(16), nullable=False),
            sa.Column("version_id", UUID()),
            sa.Column("service_principal_id", UUID(), nullable=False),
            sa.Column("cron", sa.String(160), nullable=False),
            sa.Column("timezone", sa.String(100), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("input", JSONB(), nullable=False),
            sa.Column("concurrency_policy", sa.String(16), nullable=False),
            sa.Column("missed_run_policy", sa.String(16), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("next_fire_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_fire_at", sa.DateTime(timezone=True)),
            sa.Column("last_status", sa.String(16)),
            sa.Column("last_error_code", sa.String(80)),
            sa.Column("active_execution_id", UUID()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        ],
        {
            "definition_id": "workflow_definitions",
            "service_principal_id": "service_principals",
            "active_execution_id": "workflow_executions",
        },
        [
            sa.ForeignKeyConstraint(
                ["version_id", "definition_id", "organization_id"],
                [
                    "workflow_versions.id",
                    "workflow_versions.definition_id",
                    "workflow_versions.organization_id",
                ],
                name="fk_schedule_version_definition",
                deferrable=True,
                initially="DEFERRED",
            ),
            sa.CheckConstraint("revision >= 1"),
            sa.CheckConstraint(
                "(version_policy = 'published' AND version_id IS NULL) OR "
                "(version_policy = 'pinned' AND version_id IS NOT NULL)"
            ),
            sa.CheckConstraint("concurrency_policy = 'forbid' AND missed_run_policy = 'coalesce'"),
        ],
    )
    op.create_index("ix_schedule_due", "workflow_schedules", ["enabled", "next_fire_at"])
    table(
        "schedule_fires",
        [
            sa.Column("schedule_id", UUID(), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("coalesced", sa.Boolean(), nullable=False),
            sa.Column("error_code", sa.String(80)),
            sa.Column("execution_id", UUID()),
            sa.Column("version_id", UUID()),
            sa.Column("service_principal_id", UUID(), nullable=False),
        ],
        {
            "schedule_id": "workflow_schedules",
            "execution_id": "workflow_executions",
            "version_id": "workflow_versions",
            "service_principal_id": "service_principals",
        },
        [
            sa.UniqueConstraint("schedule_id", "scheduled_at"),
            sa.CheckConstraint("revision >= 1"),
            sa.CheckConstraint("status IN ('accepted', 'rejected', 'skipped')"),
            sa.CheckConstraint(
                "status != 'accepted' OR (execution_id IS NOT NULL "
                "AND version_id IS NOT NULL AND error_code IS NULL)"
            ),
        ],
    )
    op.create_index("ix_schedule_fires_schedule_id", "schedule_fires", ["schedule_id"])
    op.execute("""
    CREATE FUNCTION preserve_schedule_history() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME = 'schedule_fires' THEN
        RAISE EXCEPTION 'Schedule fire outcomes are immutable';
      END IF;
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Retain schedule configuration and fire history'; END IF;
      IF (NEW.id, NEW.organization_id, NEW.created_at) IS DISTINCT FROM
         (OLD.id, OLD.organization_id, OLD.created_at) THEN
        RAISE EXCEPTION 'Schedule identity is immutable';
      END IF;
      RETURN NEW;
    END $$;
    """)
    for name in ["workflow_schedules", "schedule_fires"]:
        op.execute(
            f"CREATE TRIGGER schedule_history BEFORE UPDATE OR DELETE ON {name} "
            "FOR EACH ROW EXECUTE FUNCTION preserve_schedule_history()"
        )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM workflow_schedules)")):
        raise RuntimeError("Retain schedule configuration and fire history")
    op.drop_table("schedule_fires")
    op.drop_table("workflow_schedules")
    op.execute("DROP FUNCTION preserve_schedule_history()")
