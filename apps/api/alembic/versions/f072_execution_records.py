"""Add generic execution history without rewriting legacy workflow records."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f072_execution_records"
down_revision = "f071_workflow_definitions"
branch_labels = None
depends_on = None


def identity(table, references):
    return [
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        sa.UniqueConstraint("id", "organization_id", name=f"uq_{table}_tenant_identity"),
        *(
            sa.ForeignKeyConstraint(
                [column, "organization_id"],
                [f"{target}.id", f"{target}.organization_id"],
                name=f"fk_{table}_{column}_tenant",
                deferrable=True,
                initially="DEFERRED",
            )
            for column, target in references.items()
        ),
    ]


def execution_fields(states):
    return [
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("input_json", JSONB()),
        sa.Column("output_json", JSONB()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.String(4000)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        *(
            sa.Column(name, sa.DateTime(timezone=True))
            for name in ["started_at", "heartbeat_at", "completed_at"]
        ),
        sa.CheckConstraint("status IN (" + ",".join(f"'{state}'" for state in states) + ")"),
    ]


def upgrade():
    states = ["pending", "running", "waiting", "retrying", "completed", "failed", "cancelled"]
    op.create_table(
        "workflow_executions",
        *identity(
            "workflow_executions",
            {
                "version_id": "workflow_versions",
                "legacy_run_id": "workflow_runs",
            },
        ),
        *execution_fields(states),
        sa.Column("version_id", UUID(), nullable=False),
        sa.Column("legacy_run_id", UUID()),
        sa.Column("business_type", sa.String(40)),
        sa.Column("run_mode", sa.String(40)),
        sa.Column("created_by_user_id", UUID(), sa.ForeignKey("users.id")),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("state_revision >= 0"),
    )
    op.create_table(
        "step_runs",
        *identity("step_runs", {"execution_id": "workflow_executions"}),
        *execution_fields([*states, "skipped"]),
        sa.Column("execution_id", UUID(), nullable=False),
        sa.Column("node_id", sa.String(64), nullable=False),
        sa.Column("step_type", sa.String(20), nullable=False),
        sa.Column("branch", sa.String(256), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "execution_id", "node_id", "branch", "iteration", name="uq_logical_step"
        ),
        sa.CheckConstraint("iteration >= 0"),
    )
    op.create_table(
        "step_attempts",
        *identity("step_attempts", {"step_run_id": "step_runs"}),
        *execution_fields(["pending", "running", "completed", "failed", "cancelled"]),
        sa.Column("step_run_id", UUID(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("llm_metadata", JSONB()),
        sa.UniqueConstraint("step_run_id", "number", name="uq_step_attempt_number"),
        sa.CheckConstraint("number >= 1"),
    )
    op.create_table(
        "execution_events",
        *identity("execution_events", {"execution_id": "workflow_executions"}),
        sa.Column("execution_id", UUID(), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", UUID(), nullable=False),
        sa.Column("from_status", sa.String(20)),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("details", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for table in ["workflow_executions", "step_runs", "step_attempts", "execution_events"]:
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
    op.create_index("ix_execution_events_execution_id", "execution_events", ["execution_id"])
    op.execute("""
        CREATE FUNCTION preserve_execution_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE fields text[]; field text;
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Execution history is immutable'; END IF;
          fields := CASE TG_TABLE_NAME
            WHEN 'workflow_executions' THEN ARRAY['id','organization_id','version_id',
                                                  'legacy_run_id','created_by_user_id',
                                                  'business_type','run_mode']
            WHEN 'step_runs' THEN ARRAY['id','organization_id','execution_id','node_id',
                                       'step_type','branch','iteration','idempotency_key']
            ELSE ARRAY['id','organization_id','step_run_id','number','idempotency_key'] END;
          FOREACH field IN ARRAY fields LOOP
            IF (to_jsonb(OLD)->field) IS DISTINCT FROM (to_jsonb(NEW)->field)
            THEN RAISE EXCEPTION 'Execution identity is immutable'; END IF;
          END LOOP;
          RETURN NEW;
        END $$;
    """)
    for table in ["workflow_executions", "step_runs", "step_attempts"]:
        op.execute(
            f"CREATE TRIGGER {table}_identity BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION preserve_execution_identity()"
        )


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM workflow_executions)")).scalar():
        raise RuntimeError("Retain execution history before downgrading")
    for table in ["execution_events", "step_attempts", "step_runs", "workflow_executions"]:
        op.drop_table(table)
    op.execute("DROP FUNCTION preserve_execution_identity()")
