"""workflow_cancelled_event

Revision ID: b4e2a1c9d083
Revises: a3c9d8e7f012
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b4e2a1c9d083"
down_revision: str | Sequence[str] | None = "a3c9d8e7f012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE workfloweventtype ADD VALUE IF NOT EXISTS 'workflow_cancelled'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    pass
