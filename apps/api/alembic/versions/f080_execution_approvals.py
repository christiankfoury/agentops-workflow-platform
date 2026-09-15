"""Retain immutable generic approval snapshots and decision evidence."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f080_execution_approvals"
down_revision = "f079_durable_delays"
branch_labels = None
depends_on = None


def upgrade():
    table = "execution_approvals"
    references = {
        "execution_id": "workflow_executions",
        "step_run_id": "step_runs",
        "version_id": "workflow_versions",
    }
    op.create_table(
        table,
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        *(sa.Column(key, UUID(), nullable=False) for key in references),
        sa.Column("node_id", sa.String(64), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_json", JSONB(), nullable=False),
        sa.Column("review_json", JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by_user_id", UUID(), sa.ForeignKey("users.id")),
        sa.Column("human_feedback", sa.String(4000)),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("replacement_id", UUID()),
        sa.UniqueConstraint("id", "organization_id", name=f"uq_{table}_tenant_identity"),
        sa.UniqueConstraint("step_run_id", "revision", name="uq_approval_snapshot_revision"),
        sa.CheckConstraint("revision >= 1 AND iteration >= 0"),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','retry_requested',"
            "'superseded','invalidated','cancelled','expired')"
        ),
        *(
            sa.ForeignKeyConstraint(
                [key, "organization_id"],
                [f"{target}.id", f"{target}.organization_id"],
                name=f"fk_{table}_{key}_tenant",
                deferrable=True,
                initially="DEFERRED",
            )
            for key, target in references.items()
        ),
    )
    op.create_index("ix_execution_approvals_organization_id", table, ["organization_id"])
    op.create_index(
        "uq_pending_execution_approval",
        table,
        ["step_run_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_approval_expiry",
        table,
        ["expires_at", "id"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.execute("""
        CREATE FUNCTION preserve_execution_approval() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE field text;
        BEGIN
          IF TG_OP='DELETE' OR OLD.status<>'pending' THEN
            RAISE EXCEPTION 'Retain immutable approval history';
          END IF;
          FOREACH field IN ARRAY ARRAY['id','organization_id','execution_id','step_run_id',
            'version_id','node_id','iteration','revision','source_hash','payload_hash',
            'payload_json','review_json','expires_at','created_at'] LOOP
            IF to_jsonb(NEW)->field IS DISTINCT FROM to_jsonb(OLD)->field THEN
              RAISE EXCEPTION 'Approval snapshot is immutable';
            END IF;
          END LOOP;
          RETURN NEW;
        END $$;
        CREATE TRIGGER execution_approval_history BEFORE UPDATE OR DELETE ON execution_approvals
          FOR EACH ROW EXECUTE FUNCTION preserve_execution_approval();
    """)


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS(SELECT 1 FROM execution_approvals)")).scalar():
        raise RuntimeError("Retain execution approval history before downgrading")
    op.drop_table("execution_approvals")
    op.execute("DROP FUNCTION preserve_execution_approval()")
