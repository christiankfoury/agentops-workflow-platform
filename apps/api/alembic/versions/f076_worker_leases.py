"""Lease checkpoint ownership and retain bounded recovery history."""

import sqlalchemy as sa

from alembic import op

revision = "f076_worker_leases"
down_revision = "f075_durable_jobs"
branch_labels = None
depends_on = None


def upgrade():
    # A batched upgrade may follow Phase 75's backfill in this same transaction.
    op.execute("SET CONSTRAINTS ALL IMMEDIATE")
    op.add_column("durable_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.add_column("durable_jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True)))
    op.add_column(
        "durable_jobs",
        sa.Column("recovery_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint("ck_job_recovery_count", "durable_jobs", "recovery_count >= 0")
    op.create_index(
        "ix_durable_jobs_expired",
        "durable_jobs",
        ["lease_expires_at", "id"],
        postgresql_where=sa.text("status = 'running'"),
    )
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
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
             OR OLD.status IN ('completed', 'failed') THEN
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
            (OLD.status='queued' AND NEW.status='running') OR reclaim OR
            (OLD.status='running' AND NEW.status IN ('completed', 'failed'))
          ) THEN RAISE EXCEPTION 'Invalid durable job transition'; END IF;
          RETURN NEW;
        END $$;
        UPDATE durable_jobs SET lease_expires_at=clock_timestamp()
        WHERE status='running';
    """)
    op.create_check_constraint(
        "ck_running_job_lease",
        "durable_jobs",
        "status != 'running' OR lease_expires_at IS NOT NULL",
    )
    op.execute("SET CONSTRAINTS ALL DEFERRED")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM durable_jobs)")).scalar():
        raise RuntimeError("Retain job lease history before downgrading")
    op.execute("""
        CREATE OR REPLACE FUNCTION preserve_durable_job() RETURNS trigger LANGUAGE plpgsql AS $$
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
    """)
    op.drop_index("ix_durable_jobs_expired", "durable_jobs")
    op.drop_constraint("ck_running_job_lease", "durable_jobs", type_="check")
    op.drop_constraint("ck_job_recovery_count", "durable_jobs", type_="check")
    for name in ["recovery_count", "heartbeat_at", "lease_expires_at"]:
        op.drop_column("durable_jobs", name)
