"""Target branch jobs independently while retaining existing linear receipts."""

import sqlalchemy as sa

from alembic import op

revision = "f081_parallel_jobs"
down_revision = "f080_execution_approvals"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET CONSTRAINTS ALL IMMEDIATE")
    op.add_column("durable_jobs", sa.Column("node_id", sa.String(64)))
    op.add_column(
        "durable_jobs", sa.Column("iteration", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "durable_jobs", sa.Column("branch", sa.String(256), nullable=False, server_default="main")
    )
    op.create_check_constraint("ck_job_iteration", "durable_jobs", "iteration >= 0")
    op.drop_index("uq_execution_active_job", "durable_jobs")
    op.execute("""CREATE UNIQUE INDEX uq_execution_active_job ON durable_jobs
        (execution_id, COALESCE(node_id, ''), iteration) WHERE status IN ('queued','running')""")
    op.execute("""
        CREATE OR REPLACE FUNCTION preserve_durable_job() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE reclaim boolean;
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Retain durable job history'; END IF;
          reclaim := OLD.status='running' AND NEW.status='queued'
                     AND OLD.lease_expires_at <= clock_timestamp()
                     AND NEW.recovery_count=OLD.recovery_count+1;
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.execution_id IS DISTINCT FROM OLD.execution_id
             OR NEW.sequence IS DISTINCT FROM OLD.sequence
             OR NEW.node_id IS DISTINCT FROM OLD.node_id
             OR NEW.iteration IS DISTINCT FROM OLD.iteration
             OR NEW.branch IS DISTINCT FROM OLD.branch
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
             OR OLD.status IN ('completed', 'failed', 'cancelled') THEN
            RAISE EXCEPTION 'Durable job identity and terminal history are immutable';
          END IF;
          IF NOT reclaim AND (
             (OLD.claim_token IS NOT NULL AND NEW.claim_token IS DISTINCT FROM OLD.claim_token)
             OR (OLD.attempt_id IS NOT NULL AND NEW.attempt_id IS DISTINCT FROM OLD.attempt_id)
             OR (OLD.dispatched_at IS NOT NULL
                 AND NEW.dispatched_at IS DISTINCT FROM OLD.dispatched_at)
             OR NEW.recovery_count<>OLD.recovery_count
          ) THEN RAISE EXCEPTION 'Only expired recovery may replace checkpoint ownership'; END IF;
          IF NEW.status <> OLD.status AND NOT (
            (OLD.status='queued' AND NEW.status IN ('running','completed','failed','cancelled')) OR
            reclaim OR (OLD.status='running' AND NEW.status IN ('completed','failed','cancelled'))
          ) THEN RAISE EXCEPTION 'Invalid durable job transition'; END IF;
          RETURN NEW;
        END $$;
    """)
    op.execute("SET CONSTRAINTS ALL DEFERRED")


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text("""SELECT
        EXISTS(SELECT 1 FROM durable_jobs
               WHERE node_id IS NOT NULL OR iteration<>0 OR branch<>'main')
        OR EXISTS(SELECT 1 FROM workflow_executions WHERE checkpoint_json->>'parallel_mode'='true')
    """)
        )
        .scalar()
    ):
        raise RuntimeError("Retain execution parallel history before downgrading")
    op.execute("""
        DO $$ DECLARE body text;
        BEGIN
          SELECT pg_get_functiondef(oid) INTO body FROM pg_proc
          WHERE proname='preserve_durable_job' AND pronamespace=current_schema()::regnamespace;
          body := replace(body, 'OR NEW.node_id IS DISTINCT FROM OLD.node_id', '');
          body := replace(body, 'OR NEW.iteration IS DISTINCT FROM OLD.iteration', '');
          body := replace(body, 'OR NEW.branch IS DISTINCT FROM OLD.branch', '');
          EXECUTE body;
        END $$;
    """)
    op.drop_index("uq_execution_active_job", "durable_jobs")
    op.create_index(
        "uq_execution_active_job",
        "durable_jobs",
        ["execution_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued','running')"),
    )
    op.drop_constraint("ck_job_iteration", "durable_jobs", type_="check")
    for column in ["branch", "iteration", "node_id"]:
        op.drop_column("durable_jobs", column)
