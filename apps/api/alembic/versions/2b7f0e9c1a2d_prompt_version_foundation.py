"""prompt_version_foundation

Revision ID: 2b7f0e9c1a2d
Revises: 8bc7538ec824
Create Date: 2026-06-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "2b7f0e9c1a2d"
down_revision: str | Sequence[str] | None = "8bc7538ec824"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

agent_type_enum = postgresql.ENUM(
    "analyst",
    "reviewer",
    "writer",
    "router",
    "timeline",
    "root_cause",
    "classifier",
    "insight",
    name="agenttype",
)


def upgrade() -> None:
    op.execute(
        """
        UPDATE prompt_versions
        SET agent_type = CASE
            WHEN lower(agent_type) IN (
                'analyst',
                'analyst agent',
                'sales analyst',
                'sales analyst agent'
            ) THEN 'analyst'
            WHEN lower(agent_type) IN (
                'reviewer',
                'reviewer agent'
            ) THEN 'reviewer'
            WHEN lower(agent_type) IN (
                'writer',
                'writer agent',
                'executive writer',
                'executive writer agent'
            ) THEN 'writer'
            WHEN lower(agent_type) IN (
                'router',
                'router agent'
            ) THEN 'router'
            WHEN lower(agent_type) IN (
                'timeline',
                'timeline agent'
            ) THEN 'timeline'
            WHEN lower(agent_type) IN (
                'root_cause',
                'root cause',
                'root cause agent'
            ) THEN 'root_cause'
            WHEN lower(agent_type) IN (
                'classifier',
                'classifier agent'
            ) THEN 'classifier'
            WHEN lower(agent_type) IN (
                'insight',
                'insight agent',
                'insight analyst',
                'insight analyst agent'
            ) THEN 'insight'
            ELSE agent_type
        END
        """
    )
    op.execute(
        """
        DO $$
        DECLARE
            invalid_agent_type text;
        BEGIN
            SELECT agent_type
            INTO invalid_agent_type
            FROM prompt_versions
            WHERE agent_type NOT IN (
                'analyst',
                'reviewer',
                'writer',
                'router',
                'timeline',
                'root_cause',
                'classifier',
                'insight'
            )
            LIMIT 1;

            IF invalid_agent_type IS NOT NULL THEN
                RAISE EXCEPTION
                    'Cannot migrate prompt_versions.agent_type value "%". '
                    'Normalize it before applying this migration.',
                    invalid_agent_type;
            END IF;
        END $$;
        """
    )
    agent_type_enum.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "prompt_versions",
        "agent_type",
        existing_type=sa.String(length=100),
        type_=agent_type_enum,
        postgresql_using="agent_type::agenttype",
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_prompt_versions_agent_name_version",
        "prompt_versions",
        ["agent_type", "name", "version"],
    )
    op.create_index(
        "ix_prompt_versions_active_agent_name",
        "prompt_versions",
        ["agent_type", "name"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_prompt_versions_active_agent_name", table_name="prompt_versions")
    op.drop_constraint(
        "uq_prompt_versions_agent_name_version",
        "prompt_versions",
        type_="unique",
    )
    op.alter_column(
        "prompt_versions",
        "agent_type",
        existing_type=agent_type_enum,
        type_=sa.String(length=100),
        postgresql_using="agent_type::text",
        nullable=False,
    )
    agent_type_enum.drop(op.get_bind(), checkfirst=True)
