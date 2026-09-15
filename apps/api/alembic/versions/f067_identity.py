"""Add verified identities, memberships, service principals and revocable sessions."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "f067_identity"
down_revision = "f066_state_revision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users", sa.Column("id", UUID(), primary_key=True),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False, server_default="user"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("issuer", "subject"),
        sa.CheckConstraint("kind IN ('user', 'service')"),
    )
    op.create_table(
        "organizations", sa.Column("id", UUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_table(
        "organization_memberships", sa.Column("id", UUID(), primary_key=True),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("organization_id", UUID(), sa.ForeignKey("organizations.id"),
                  nullable=False, index=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("user_id", "organization_id"),
        sa.CheckConstraint("role IN ('viewer', 'operator', 'reviewer', 'admin')"),
    )
    op.create_table(
        "service_principals", sa.Column("id", UUID(), primary_key=True),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("organization_id", UUID(), sa.ForeignKey("organizations.id"),
                  nullable=False, index=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("scopes", JSONB(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.CheckConstraint("role IN ('viewer', 'operator')"),
    )
    op.create_table(
        "identity_sessions", sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    for table in ["identity_sessions", "service_principals", "organization_memberships",
                  "organizations", "users"]:
        op.drop_table(table)
