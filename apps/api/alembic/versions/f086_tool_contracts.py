"""Retain versioned tool contracts, credential references and external-effect history."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f086_tool_contracts"
down_revision = "f085_durable_evaluations"
branch_labels = None
depends_on = None


def table(name, columns, references=None, constraints=()):
    op.create_table(
        name,
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        *columns,
        sa.UniqueConstraint("id", "organization_id", name=f"uq_{name}_tenant_identity"),
        *(
            sa.ForeignKeyConstraint(
                [key, "organization_id"],
                [f"{target}.id", f"{target}.organization_id"],
                name=f"fk_{name}_{key}_tenant",
                deferrable=True,
                initially="DEFERRED",
            )
            for key, target in (references or {}).items()
        ),
        *constraints,
    )
    op.create_index(f"ix_{name}_organization_id", name, ["organization_id"])
    op.execute(
        f"CREATE TRIGGER tool_history BEFORE UPDATE OR DELETE ON {name} "
        "FOR EACH ROW EXECUTE FUNCTION preserve_tool_history()"
    )


def upgrade():
    op.execute("""
    CREATE FUNCTION preserve_tool_history() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE field text;
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Retain tool history'; END IF;
      IF NEW.id<>OLD.id OR NEW.organization_id<>OLD.organization_id THEN
        RAISE EXCEPTION 'Tool identity is immutable'; END IF;
      IF TG_TABLE_NAME='tool_versions' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'Tool contract is immutable'; END IF;
      IF TG_TABLE_NAME='tool_credentials' AND
         to_jsonb(NEW)->'source_alias' IS DISTINCT FROM to_jsonb(OLD)->'source_alias' THEN
        RAISE EXCEPTION 'Credential source is immutable'; END IF;
      IF TG_TABLE_NAME='tool_executions' THEN
        IF to_jsonb(OLD)->>'credential_digest' IS NOT NULL AND
           to_jsonb(NEW)->'credential_digest' IS DISTINCT FROM
           to_jsonb(OLD)->'credential_digest' THEN
          RAISE EXCEPTION 'Tool credential binding is immutable'; END IF;
        IF to_jsonb(OLD)->>'status' IN ('succeeded','reconciled') AND NEW IS DISTINCT FROM OLD THEN
          RAISE EXCEPTION 'Confirmed tool outcomes are immutable'; END IF;
        FOREACH field IN ARRAY ARRAY['version_id','step_run_id','attempt_id','call_id',
          'effect_key','request_fingerprint','request_json','created_at'] LOOP
          IF to_jsonb(NEW)->field IS DISTINCT FROM to_jsonb(OLD)->field THEN
            RAISE EXCEPTION 'Tool effect identity is immutable'; END IF;
        END LOOP;
      END IF;
      RETURN NEW;
    END $$;
    """)
    table(
        "tool_credentials",
        [
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("source_alias", sa.String(100), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        ],
        constraints=[sa.UniqueConstraint("organization_id", "source_alias")],
    )
    table(
        "tool_definitions",
        [
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        ],
    )
    table(
        "tool_versions",
        [
            sa.Column("definition_id", UUID(), nullable=False),
            sa.Column("number", sa.Integer(), nullable=False),
            sa.Column("credential_ref", UUID()),
            sa.Column("contract", JSONB(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        ],
        {"definition_id": "tool_definitions", "credential_ref": "tool_credentials"},
        [
            sa.UniqueConstraint("definition_id", "number"),
            sa.CheckConstraint("number >= 1"),
        ],
    )
    table(
        "tool_executions",
        [
            *(
                sa.Column(key, UUID(), nullable=False)
                for key in ["version_id", "step_run_id", "attempt_id"]
            ),
            sa.Column("call_id", sa.String(100), nullable=False),
            sa.Column("effect_key", sa.String(64), nullable=False),
            sa.Column("request_fingerprint", sa.String(64), nullable=False),
            sa.Column("credential_digest", sa.String(64)),
            sa.Column("request_json", JSONB(), nullable=False),
            sa.Column("result_json", JSONB()),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("claim_token", UUID()),
            sa.Column("reservation_token", UUID()),
            sa.Column("dispatched", sa.Boolean(), nullable=False),
            sa.Column("error_code", sa.String(80)),
            sa.Column("latency_ms", sa.Integer()),
            sa.Column("reconciliation", JSONB()),
            *(
                sa.Column(
                    key, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
                )
                for key in ["created_at", "updated_at"]
            ),
        ],
        {"version_id": "tool_versions", "step_run_id": "step_runs", "attempt_id": "step_attempts"},
        [
            sa.UniqueConstraint("organization_id", "effect_key"),
            sa.CheckConstraint("status IN ('pending','succeeded','failed','unknown','reconciled')"),
            sa.CheckConstraint("attempts >= 0"),
        ],
    )
    op.create_index("ix_tool_executions_step_run_id", "tool_executions", ["step_run_id"])


def downgrade():
    tables = ["tool_executions", "tool_versions", "tool_definitions", "tool_credentials"]
    for name in tables:
        if op.get_bind().scalar(sa.text(f"SELECT EXISTS(SELECT 1 FROM {name})")):
            raise RuntimeError("Retain tool contracts, credentials and effect history")
    for name in tables:
        op.drop_table(name)
    op.execute("DROP FUNCTION preserve_tool_history()")
