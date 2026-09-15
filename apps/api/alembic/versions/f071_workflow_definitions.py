"""Tenant definitions, immutable publications and retained prompt references."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f071_workflow_definitions"
down_revision = "f069_audit_events"
branch_labels = None
depends_on = None


def ownership(table):
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
    ]


def reference(table, column, target):
    return sa.ForeignKeyConstraint(
        [column, "organization_id"],
        [f"{target}.id", f"{target}.organization_id"],
        name=f"fk_{table}_{column}_tenant",
        deferrable=True,
        initially="DEFERRED",
    )


def upgrade():
    op.create_table(
        "workflow_definitions",
        *ownership("workflow_definitions"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("draft_graph", JSONB(), nullable=False),
        sa.Column("draft_revision", sa.Integer(), nullable=False),
        sa.Column("published_version_id", UUID()),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", UUID(), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("draft_revision >= 1"),
    )
    op.create_table(
        "workflow_versions",
        *ownership("workflow_versions"),
        sa.Column("definition_id", UUID(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("graph", JSONB(), nullable=False),
        sa.Column("graph_hash", sa.String(64), nullable=False),
        sa.Column("prompt_snapshots", JSONB(), nullable=False),
        sa.Column("created_by_user_id", UUID(), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        reference("workflow_versions", "definition_id", "workflow_definitions"),
        sa.UniqueConstraint("definition_id", "number", name="uq_workflow_version_number"),
        sa.UniqueConstraint(
            "id", "definition_id", "organization_id", name="uq_workflow_version_definition"
        ),
        sa.CheckConstraint("number >= 1 AND source_revision >= 1"),
    )
    op.create_foreign_key(
        "fk_definition_published_version",
        "workflow_definitions",
        "workflow_versions",
        ["published_version_id", "id", "organization_id"],
        ["id", "definition_id", "organization_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_table(
        "workflow_version_prompts",
        *ownership("workflow_version_prompts"),
        sa.Column("version_id", UUID(), nullable=False),
        sa.Column("prompt_id", UUID(), nullable=False),
        reference("workflow_version_prompts", "version_id", "workflow_versions"),
        reference("workflow_version_prompts", "prompt_id", "prompt_versions"),
        sa.UniqueConstraint("version_id", "prompt_id"),
    )
    for table in ["workflow_definitions", "workflow_versions", "workflow_version_prompts"]:
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
    op.execute("""
        CREATE FUNCTION reject_workflow_version_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE'
          THEN RAISE EXCEPTION 'Published workflow versions are immutable'; END IF;
          IF (to_jsonb(NEW) - 'archived_at') IS DISTINCT FROM (to_jsonb(OLD) - 'archived_at')
          THEN RAISE EXCEPTION 'Published workflow versions are immutable'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER workflow_versions_immutable BEFORE UPDATE OR DELETE ON workflow_versions
        FOR EACH ROW EXECUTE FUNCTION reject_workflow_version_mutation();
        CREATE FUNCTION reject_workflow_prompt_link_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Published prompt links are immutable'; END $$;
        CREATE TRIGGER workflow_prompt_links_immutable BEFORE UPDATE OR DELETE
        ON workflow_version_prompts
        FOR EACH ROW EXECUTE FUNCTION reject_workflow_prompt_link_mutation();
        CREATE FUNCTION protect_published_prompt() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF EXISTS (SELECT 1 FROM workflow_version_prompts WHERE prompt_id = OLD.id)
             AND (NEW.template, NEW.agent_type, NEW.name, NEW.version)
                 IS DISTINCT FROM (OLD.template, OLD.agent_type, OLD.name, OLD.version)
          THEN RAISE EXCEPTION 'Published prompt content is immutable'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER published_prompt_content BEFORE UPDATE ON prompt_versions
        FOR EACH ROW EXECUTE FUNCTION protect_published_prompt();
    """)


def downgrade():
    # Never silently destroy version history during a rollback.
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM workflow_definitions)")).scalar():
        raise RuntimeError("Export and retain workflow definitions before downgrading")
    op.execute("DROP TRIGGER published_prompt_content ON prompt_versions")
    op.execute("DROP FUNCTION protect_published_prompt()")
    op.drop_table("workflow_version_prompts")
    op.drop_constraint(
        "fk_definition_published_version", "workflow_definitions", type_="foreignkey"
    )
    op.drop_table("workflow_versions")
    op.drop_table("workflow_definitions")
    op.execute("DROP FUNCTION reject_workflow_version_mutation()")
    op.execute("DROP FUNCTION reject_workflow_prompt_link_mutation()")
