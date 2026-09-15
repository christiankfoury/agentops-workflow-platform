"""Retain tenant-scoped idempotent start receipts."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "f073_execution_starts"
down_revision = "f072_execution_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "execution_starts",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("execution_id", UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_execution_starts_tenant_identity"),
        sa.UniqueConstraint("organization_id", "key", name="uq_execution_start_key"),
        sa.UniqueConstraint("execution_id", name="uq_execution_start_run"),
        sa.ForeignKeyConstraint(
            ["execution_id", "organization_id"],
            ["workflow_executions.id", "workflow_executions.organization_id"],
            name="fk_execution_starts_execution_id_tenant",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_execution_starts_organization_id", "execution_starts", ["organization_id"])
    op.execute("""
        CREATE FUNCTION preserve_start_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Execution start receipts are immutable'; END $$;
        CREATE TRIGGER execution_starts_immutable BEFORE UPDATE OR DELETE ON execution_starts
        FOR EACH ROW EXECUTE FUNCTION preserve_start_receipt();
    """)


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM execution_starts)")).scalar():
        raise RuntimeError("Retain execution start receipts before downgrading")
    op.drop_table("execution_starts")
    op.execute("DROP FUNCTION preserve_start_receipt()")
