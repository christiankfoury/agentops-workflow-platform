"""Persist administrator intent for durable evaluation approvals."""

import sqlalchemy as sa

from alembic import op

revision = "f085_durable_evaluations"
down_revision = "f083_sales_templates"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evaluation_results", sa.Column("requested_by_user_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_evaluation_requester", "evaluation_results", "users", ["requested_by_user_id"], ["id"]
    )
    for name in ["automatic_approval", "approval_blocked", "derive_expected"]:
        op.add_column(
            "evaluation_results",
            sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    op.create_index("ix_evaluation_workflow_run", "evaluation_results", ["workflow_run_id"])
    op.execute("""
    CREATE FUNCTION preserve_evaluation_intent() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF ROW(OLD.requested_by_user_id, OLD.automatic_approval, OLD.derive_expected)
         IS DISTINCT FROM ROW(NEW.requested_by_user_id, NEW.automatic_approval, NEW.derive_expected)
      THEN RAISE EXCEPTION 'Evaluation approval intent is immutable'; END IF;
      IF OLD.workflow_run_id IS NOT NULL AND
         ROW(OLD.workflow_run_id, OLD.evaluation_case_id, OLD.run_mode)
         IS DISTINCT FROM ROW(NEW.workflow_run_id, NEW.evaluation_case_id, NEW.run_mode)
      THEN RAISE EXCEPTION 'Evaluation run binding is immutable'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER evaluation_intent_immutable BEFORE UPDATE ON evaluation_results
      FOR EACH ROW EXECUTE FUNCTION preserve_evaluation_intent();
    """)


def downgrade():
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM evaluation_results "
            "WHERE status='pending' AND automatic_approval)"
        )
    ):
        raise RuntimeError("Finish or cancel pending durable evaluations before downgrading")
    op.drop_index("ix_evaluation_workflow_run", "evaluation_results")
    op.execute("DROP TRIGGER evaluation_intent_immutable ON evaluation_results")
    op.execute("DROP FUNCTION preserve_evaluation_intent()")
    op.drop_constraint("fk_evaluation_requester", "evaluation_results", type_="foreignkey")
    for name in [
        "requested_by_user_id",
        "automatic_approval",
        "approval_blocked",
        "derive_expected",
    ]:
        op.drop_column("evaluation_results", name)
