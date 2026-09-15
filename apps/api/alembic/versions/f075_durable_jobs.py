"""Persist durable checkpoint jobs and enqueue existing ready executions."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "f075_durable_jobs"
down_revision = "f074_execution_checkpoints"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "durable_jobs",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        sa.Column("execution_id", UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempt_id", UUID()),
        sa.Column("claim_token", UUID()),
        sa.Column("worker_id", sa.String(128)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "due_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(80)),
        sa.UniqueConstraint("id", "organization_id", name="uq_durable_jobs_tenant_identity"),
        sa.UniqueConstraint("execution_id", "sequence", name="uq_execution_job_sequence"),
        sa.CheckConstraint("sequence >= 0"),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')"),
        *[
            sa.ForeignKeyConstraint(
                [column, "organization_id"],
                [f"{table}.id", f"{table}.organization_id"],
                name=f"fk_durable_jobs_{column}_tenant",
                deferrable=True,
                initially="DEFERRED",
            )
            for column, table in [
                ("execution_id", "workflow_executions"),
                ("attempt_id", "step_attempts"),
            ]
        ],
    )
    op.create_index("ix_durable_jobs_organization_id", "durable_jobs", ["organization_id"])
    op.create_index("ix_durable_jobs_due", "durable_jobs", ["status", "due_at", "id"])
    op.create_index(
        "uq_execution_active_job",
        "durable_jobs",
        ["execution_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.execute("""
        INSERT INTO durable_jobs (id, organization_id, execution_id, sequence, status)
        SELECT gen_random_uuid(), e.organization_id, e.id, 0, 'queued'
        FROM workflow_executions e WHERE e.status IN ('pending', 'running')
        AND NOT EXISTS (SELECT 1 FROM step_runs s WHERE s.execution_id=e.id
                        AND s.status NOT IN ('completed', 'failed', 'cancelled', 'skipped'));
        INSERT INTO execution_events
          (id, organization_id, execution_id, entity_type, entity_id, to_status, details)
        SELECT gen_random_uuid(), organization_id, execution_id, 'durable_jobs', id,
               'queued', '{"source":"migration75"}'::jsonb FROM durable_jobs;
        CREATE FUNCTION preserve_durable_job() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Retain durable job history'; END IF;
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.execution_id IS DISTINCT FROM OLD.execution_id
             OR NEW.sequence IS DISTINCT FROM OLD.sequence
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
             OR (OLD.claim_token IS NOT NULL AND NEW.claim_token IS DISTINCT FROM OLD.claim_token)
             OR (OLD.attempt_id IS NOT NULL AND NEW.attempt_id IS DISTINCT FROM OLD.attempt_id)
             OR (OLD.dispatched_at IS NOT NULL
                 AND NEW.dispatched_at IS DISTINCT FROM OLD.dispatched_at)
             OR OLD.status IN ('completed', 'failed') THEN
            RAISE EXCEPTION 'Durable job identity and terminal history are immutable';
          END IF;
          IF NEW.status <> OLD.status AND NOT (
            (OLD.status='queued' AND NEW.status='running') OR
            (OLD.status='running' AND NEW.status IN ('completed', 'failed'))
          ) THEN RAISE EXCEPTION 'Invalid durable job transition'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER durable_jobs_guard BEFORE UPDATE OR DELETE ON durable_jobs
        FOR EACH ROW EXECUTE FUNCTION preserve_durable_job();
    """)


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM durable_jobs)")).scalar():
        raise RuntimeError("Retain durable jobs before downgrading")
    op.drop_table("durable_jobs")
    op.execute("DROP FUNCTION preserve_durable_job()")
