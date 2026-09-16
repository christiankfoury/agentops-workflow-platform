"""Scoped webhook configuration and retained delivery receipts."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f091_webhook_triggers"
down_revision = "f090_llm_conversations"
branch_labels = None
depends_on = None


def table(name, columns, references, constraints=()):
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
    op.execute(
        f"CREATE TRIGGER webhook_history BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION preserve_webhook_history()"
    )


def upgrade():
    op.create_unique_constraint(
        "uq_service_principal_tenant_identity", "service_principals", ["id", "organization_id"]
    )
    op.execute("""
    CREATE FUNCTION preserve_webhook_history() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE field text; frozen text[];
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Retain webhook configuration and delivery history'; END IF;
      frozen := ARRAY['id','organization_id','created_at'];
      IF TG_TABLE_NAME = 'webhook_deliveries' THEN
        frozen := frozen || ARRAY['trigger_id','event_id','payload_fingerprint'];
        IF to_jsonb(OLD)->>'status' = 'accepted' THEN
          frozen := frozen || ARRAY['status','execution_id','version_id','service_principal_id','accepted_revision','error_code'];
        END IF;
      END IF;
      FOREACH field IN ARRAY frozen LOOP
        IF to_jsonb(NEW)->field IS DISTINCT FROM to_jsonb(OLD)->field THEN
          RAISE EXCEPTION 'Webhook identity and accepted outcomes are immutable'; END IF;
      END LOOP;
      RETURN NEW;
    END $$;
    """)
    table(
        "webhook_triggers",
        [
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("definition_id", UUID(), nullable=False),
            sa.Column("version_policy", sa.String(16), nullable=False),
            sa.Column("version_id", UUID()),
            sa.Column("service_principal_id", UUID(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("input_mapping", JSONB()),
            sa.Column("max_payload_bytes", sa.Integer(), nullable=False),
            sa.Column("freshness_seconds", sa.Integer(), nullable=False),
            sa.Column("secret_alias", sa.String(100), nullable=False),
            sa.Column("previous_secret_alias", sa.String(100)),
            sa.Column("previous_secret_until", sa.DateTime(timezone=True)),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        ],
        {"definition_id": "workflow_definitions", "service_principal_id": "service_principals"},
        [
            sa.ForeignKeyConstraint(
                ["version_id", "definition_id", "organization_id"],
                [
                    "workflow_versions.id",
                    "workflow_versions.definition_id",
                    "workflow_versions.organization_id",
                ],
                name="fk_webhook_version_definition",
                deferrable=True,
                initially="DEFERRED",
            ),
            sa.CheckConstraint("revision >= 1"),
            sa.CheckConstraint(
                "(version_policy = 'published' AND version_id IS NULL) OR (version_policy = 'pinned' AND version_id IS NOT NULL)"
            ),
            sa.CheckConstraint(
                "max_payload_bytes BETWEEN 1024 AND 262144 AND freshness_seconds BETWEEN 30 AND 600"
            ),
        ],
    )
    table(
        "webhook_deliveries",
        [
            sa.Column("trigger_id", UUID(), nullable=False),
            sa.Column("event_id", sa.String(128), nullable=False),
            sa.Column("payload_fingerprint", sa.String(64), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("execution_id", UUID()),
            sa.Column("version_id", UUID()),
            sa.Column("service_principal_id", UUID()),
            sa.Column("accepted_revision", sa.Integer()),
            sa.Column("error_code", sa.String(80)),
            *(
                sa.Column(
                    name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
                )
                for name in ["created_at", "last_attempt_at"]
            ),
        ],
        {
            "trigger_id": "webhook_triggers",
            "execution_id": "workflow_executions",
            "version_id": "workflow_versions",
            "service_principal_id": "service_principals",
        },
        [
            sa.UniqueConstraint("trigger_id", "event_id"),
            sa.CheckConstraint("attempts >= 1"),
            sa.CheckConstraint("status IN ('pending','accepted','rejected')"),
            sa.CheckConstraint(
                "status != 'accepted' OR (execution_id IS NOT NULL AND version_id IS NOT NULL AND service_principal_id IS NOT NULL AND accepted_revision IS NOT NULL AND error_code IS NULL)"
            ),
        ],
    )
    op.create_index("ix_webhook_deliveries_trigger_id", "webhook_deliveries", ["trigger_id"])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM webhook_triggers)")):
        raise RuntimeError("Retain webhook configuration and delivery history")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_triggers")
    op.drop_constraint("uq_service_principal_tenant_identity", "service_principals", type_="unique")
    op.execute("DROP FUNCTION preserve_webhook_history()")
