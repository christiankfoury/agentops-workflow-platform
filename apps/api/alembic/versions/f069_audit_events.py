"""Persist immutable tenant audit evidence for authenticated sensitive actions."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f069_audit_events"
down_revision = "f068_tenant_ownership"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_events",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        sa.Column("actor_user_id", UUID(), sa.ForeignKey("users.id")),
        sa.Column("service_principal_id", UUID(), sa.ForeignKey("service_principals.id")),
        sa.Column("actor_kind", sa.String(16), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=False),
        sa.Column("details_json", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("actor_kind IN ('user', 'service', 'local')"),
        sa.UniqueConstraint("id", "organization_id", name="uq_audit_events_tenant_identity"),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.execute("""
        CREATE FUNCTION reject_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Audit events are immutable'; END $$;
        CREATE TRIGGER audit_events_immutable BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
    """)


def downgrade():
    op.drop_table("audit_events")
    op.execute("DROP FUNCTION reject_audit_mutation()")
