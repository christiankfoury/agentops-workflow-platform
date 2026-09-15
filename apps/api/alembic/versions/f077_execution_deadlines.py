"""Persist execution/attempt deadlines and durable retry visibility."""

import sqlalchemy as sa

from alembic import op

revision = "f077_execution_deadlines"
down_revision = "f076_worker_leases"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET CONSTRAINTS ALL IMMEDIATE")
    op.add_column("workflow_executions", sa.Column("deadline_at", sa.DateTime(timezone=True)))
    op.add_column("step_runs", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("step_attempts", sa.Column("deadline_at", sa.DateTime(timezone=True)))
    op.add_column("step_attempts", sa.Column("error_classification", sa.String(20)))
    op.create_check_constraint(
        "ck_attempt_error_classification",
        "step_attempts",
        "error_classification IS NULL OR error_classification IN ('retryable','permanent')",
    )
    op.execute("""
        UPDATE workflow_executions e SET deadline_at=e.created_at + make_interval(
          secs=>COALESCE((v.graph->>'overall_timeout_seconds')::double precision, 86400))
        FROM workflow_versions v WHERE v.id=e.version_id
        AND e.status NOT IN ('completed','failed','cancelled');
        UPDATE step_attempts a SET deadline_at=LEAST(e.deadline_at,
          COALESCE(a.started_at,a.created_at) + make_interval(
            secs=>COALESCE((node->>'timeout_seconds')::double precision,60)))
        FROM step_runs s JOIN workflow_executions e ON e.id=s.execution_id
        JOIN workflow_versions v ON v.id=e.version_id,
        LATERAL jsonb_array_elements(v.graph->'nodes') node
        WHERE a.step_run_id=s.id AND node->>'id'=s.node_id
          AND a.status IN ('pending','running');
    """)
    # Extend only the existing queued -> terminal path; retain all ownership guards.
    op.execute("""
        DO $$ DECLARE body text;
        BEGIN
          SELECT pg_get_functiondef(oid) INTO body FROM pg_proc
          WHERE proname='preserve_durable_job' AND pronamespace=current_schema()::regnamespace;
          body := replace(body,
            '(OLD.status=''queued'' AND NEW.status=''running'')',
            '(OLD.status=''queued'' AND NEW.status IN (''running'', ''failed''))');
          EXECUTE body;
        END $$;
    """)
    op.execute("SET CONSTRAINTS ALL DEFERRED")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM workflow_executions)")).scalar():
        raise RuntimeError("Retain execution retry/deadline history before downgrading")
    op.execute("""
        DO $$ DECLARE body text;
        BEGIN
          SELECT pg_get_functiondef(oid) INTO body FROM pg_proc
          WHERE proname='preserve_durable_job' AND pronamespace=current_schema()::regnamespace;
          body := replace(body,
            '(OLD.status=''queued'' AND NEW.status IN (''running'', ''failed''))',
            '(OLD.status=''queued'' AND NEW.status=''running'')');
          EXECUTE body;
        END $$;
    """)
    op.drop_constraint("ck_attempt_error_classification", "step_attempts", type_="check")
    op.drop_column("step_attempts", "error_classification")
    op.drop_column("step_attempts", "deadline_at")
    op.drop_column("step_runs", "next_attempt_at")
    op.drop_column("workflow_executions", "deadline_at")
