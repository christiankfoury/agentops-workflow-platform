"""Backfill legacy business data and enforce tenant ownership without changing IDs."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "f068_tenant_ownership"
down_revision = "f067_identity"
branch_labels = None
depends_on = None

DEFAULT_ORG = "00000000-0000-0000-0000-000000000001"
REFERENCES = {
    "uploaded_inputs": {},
    "workflow_runs": {"input_id": "uploaded_inputs"},
    "prompt_versions": {},
    "agent_steps": {"workflow_run_id": "workflow_runs", "prompt_version_id": "prompt_versions"},
    "human_approvals": {"workflow_run_id": "workflow_runs"},
    "workflow_events": {"workflow_run_id": "workflow_runs", "agent_step_id": "agent_steps"},
    "cost_events": {"workflow_run_id": "workflow_runs", "agent_step_id": "agent_steps"},
    "evaluation_cases": {},
    "evaluation_results": {
        "evaluation_case_id": "evaluation_cases",
        "workflow_run_id": "workflow_runs",
    },
    "agent_settings": {"active_prompt_version_id": "prompt_versions"},
}
LEGACY_OWNERS = {"uploaded_inputs", "workflow_runs"}


def upgrade() -> None:
    conn = op.get_bind()
    op.create_table(
        "legacy_tenant_owners",
        sa.Column("table_name", sa.String(64), primary_key=True),
        sa.Column("record_id", UUID(), primary_key=True),
        sa.Column("original_organization_id", UUID(), nullable=True),
    )
    op.create_table(
        "tenant_backfill_counts",
        sa.Column("table_name", sa.String(64), primary_key=True),
        sa.Column("record_count", sa.BigInteger(), nullable=False),
    )
    existed = conn.execute(
        sa.text("SELECT count(*) FROM organizations WHERE id = :org"), {"org": DEFAULT_ORG}
    ).scalar_one()
    conn.execute(
        sa.text("INSERT INTO tenant_backfill_counts VALUES (:name, :count)"),
        {"name": "__default_organization_existed__", "count": existed},
    )
    conn.execute(
        sa.text(
            "INSERT INTO organizations (id, name) VALUES (:org, 'Legacy default organization') "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"org": DEFAULT_ORG},
    )
    for table in REFERENCES:
        count = conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one()
        conn.execute(
            sa.text("INSERT INTO tenant_backfill_counts VALUES (:name, :count)"),
            {"name": table, "count": count},
        )
        if table in LEGACY_OWNERS:
            conn.execute(
                sa.text(
                    "INSERT INTO legacy_tenant_owners "
                    f"SELECT :name, id, organization_id FROM {table}"
                ),
                {"name": table},
            )
        else:
            op.add_column(table, sa.Column("organization_id", UUID(), nullable=True))
        conn.execute(sa.text(f"UPDATE {table} SET organization_id = :org"), {"org": DEFAULT_ORG})
        op.alter_column(table, "organization_id", nullable=False, server_default=DEFAULT_ORG)
        op.create_foreign_key(
            f"fk_{table}_organization", table, "organizations", ["organization_id"], ["id"]
        )
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
        op.create_unique_constraint(f"uq_{table}_tenant_identity", table, ["id", "organization_id"])
        after = conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one()
        if count != after:
            raise RuntimeError(f"Tenant backfill changed row count for {table}")
    for table, references in REFERENCES.items():
        for column, target in references.items():
            op.create_foreign_key(
                f"fk_{table}_{column}_tenant",
                table,
                target,
                [column, "organization_id"],
                ["id", "organization_id"],
                deferrable=True,
                initially="DEFERRED",
            )
    op.drop_constraint("uq_agent_settings_agent_type", "agent_settings", type_="unique")
    op.create_unique_constraint(
        "uq_agent_settings_agent_type", "agent_settings", ["organization_id", "agent_type"]
    )
    op.drop_constraint("uq_prompt_versions_agent_name_version", "prompt_versions", type_="unique")
    op.create_unique_constraint(
        "uq_prompt_versions_agent_name_version",
        "prompt_versions",
        ["organization_id", "agent_type", "name", "version"],
    )
    op.drop_index("ix_prompt_versions_active_agent_name", table_name="prompt_versions")
    op.create_index(
        "ix_prompt_versions_active_agent_name",
        "prompt_versions",
        ["organization_id", "agent_type", "name"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    conn = op.get_bind()
    # Never discard ownership of subsequently created tenant data during rollback.
    for table in REFERENCES:
        if conn.execute(
            sa.text(f"SELECT 1 FROM {table} WHERE organization_id <> :org LIMIT 1"),
            {"org": DEFAULT_ORG},
        ).first():
            raise RuntimeError(
                "Tenant rollback requires exporting/migrating non-default data first"
            )
    for table, references in REFERENCES.items():
        for column in references:
            op.drop_constraint(f"fk_{table}_{column}_tenant", table, type_="foreignkey")
    op.drop_constraint("uq_agent_settings_agent_type", "agent_settings", type_="unique")
    op.create_unique_constraint("uq_agent_settings_agent_type", "agent_settings", ["agent_type"])
    op.drop_constraint("uq_prompt_versions_agent_name_version", "prompt_versions", type_="unique")
    op.create_unique_constraint(
        "uq_prompt_versions_agent_name_version",
        "prompt_versions",
        ["agent_type", "name", "version"],
    )
    op.drop_index("ix_prompt_versions_active_agent_name", table_name="prompt_versions")
    op.create_index(
        "ix_prompt_versions_active_agent_name",
        "prompt_versions",
        ["agent_type", "name"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )
    for table in REFERENCES:
        op.drop_constraint(f"fk_{table}_organization", table, type_="foreignkey")
        op.drop_constraint(f"uq_{table}_tenant_identity", table, type_="unique")
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        if table in LEGACY_OWNERS:
            op.alter_column(table, "organization_id", nullable=True, server_default=None)
            conn.execute(
                sa.text(
                    f"UPDATE {table} AS resource "
                    "SET organization_id = ledger.original_organization_id "
                    "FROM legacy_tenant_owners AS ledger "
                    "WHERE ledger.table_name = :name AND ledger.record_id = resource.id"
                ),
                {"name": table},
            )
        else:
            op.drop_column(table, "organization_id")
    # Keep the organization: memberships created after migration may reference it.
    op.drop_table("legacy_tenant_owners")
    op.drop_table("tenant_backfill_counts")
