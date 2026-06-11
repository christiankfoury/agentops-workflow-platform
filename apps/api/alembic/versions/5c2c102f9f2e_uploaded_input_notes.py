"""uploaded_input_notes

Revision ID: 5c2c102f9f2e
Revises: 2b7f0e9c1a2d
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5c2c102f9f2e"
down_revision: str | Sequence[str] | None = "2b7f0e9c1a2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("uploaded_inputs", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("uploaded_inputs", "notes")
