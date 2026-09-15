"""Freeze run-start LLM configuration without rewriting deterministic history."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "f082_execution_config"
down_revision = "f081_parallel_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workflow_executions",
        sa.Column("runtime_config", JSONB(), nullable=False, server_default="{}"),
    )
    op.execute("""DO $$ DECLARE body text; BEGIN
        SELECT pg_get_functiondef(oid) INTO body FROM pg_proc
        WHERE proname='preserve_execution_identity' AND pronamespace=current_schema()::regnamespace;
        body := replace(body, '''business_type'',''run_mode''',
                        '''business_type'',''run_mode'',''runtime_config''');
        EXECUTE body;
    END $$;""")


def downgrade():
    if op.get_bind().scalar(
        sa.text("""SELECT EXISTS(SELECT 1 FROM workflow_executions
        WHERE runtime_config<>'{}'::jsonb)""")
    ):
        raise RuntimeError("Retain execution LLM configuration and history before downgrading")
    op.execute("""DO $$ DECLARE body text; BEGIN
        SELECT pg_get_functiondef(oid) INTO body FROM pg_proc
        WHERE proname='preserve_execution_identity' AND pronamespace=current_schema()::regnamespace;
        body := replace(body, ',''runtime_config''', '');
        EXECUTE body;
    END $$;""")
    op.drop_column("workflow_executions", "runtime_config")
