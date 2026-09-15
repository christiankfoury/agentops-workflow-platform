"""Persist cancel intent and cancelled jobs without changing completed history."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "f078_execution_cancellation"
down_revision = "f077_execution_deadlines"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET CONSTRAINTS ALL IMMEDIATE")
    op.add_column(
        "workflow_executions",
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "workflow_executions", sa.Column("cancel_requested_at", sa.DateTime(timezone=True))
    )
    op.add_column("workflow_executions", sa.Column("cancel_requested_by_user_id", UUID()))
    op.add_column("workflow_executions", sa.Column("cancel_reason", sa.String(1000)))
    op.create_foreign_key(
        "fk_execution_cancel_actor",
        "workflow_executions",
        "users",
        ["cancel_requested_by_user_id"],
        ["id"],
    )
    op.drop_constraint("durable_jobs_status_check", "durable_jobs", type_="check")
    op.create_check_constraint(
        "durable_jobs_status_check",
        "durable_jobs",
        "status IN ('queued','running','completed','failed','cancelled')",
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
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM workflow_executions)")).scalar():
        raise RuntimeError("Retain execution cancellation history before downgrading")
    op.execute("""
        DO $$ DECLARE body text;
        BEGIN
          SELECT pg_get_functiondef(oid) INTO body FROM pg_proc
          WHERE proname='preserve_durable_job' AND pronamespace=current_schema()::regnamespace;
          body := replace(body, ', ''cancelled''', '');
          body := replace(body, ',''cancelled''', '');
          body := replace(body,
            '(OLD.status=''queued'' AND NEW.status IN (''running'',''completed'',''failed''))',
            '(OLD.status=''queued'' AND NEW.status IN (''running'', ''failed''))');
          EXECUTE body;
        END $$;
    """)
    op.drop_constraint("durable_jobs_status_check", "durable_jobs", type_="check")
    op.create_check_constraint(
        "durable_jobs_status_check",
        "durable_jobs",
        "status IN ('queued','running','completed','failed')",
    )
    op.drop_constraint("fk_execution_cancel_actor", "workflow_executions", type_="foreignkey")
    for column in [
        "cancel_reason",
        "cancel_requested_by_user_id",
        "cancel_requested_at",
        "cancel_requested",
    ]:
        op.drop_column("workflow_executions", column)
