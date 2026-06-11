"""human_edited_analysis_event

Revision ID: e7f8a9b0c123
Revises: d6e7f8a9b012
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7f8a9b0c123"
down_revision: str | Sequence[str] | None = "d6e7f8a9b012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE workfloweventtype ADD VALUE IF NOT EXISTS 'human_edited_analysis'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    pass
