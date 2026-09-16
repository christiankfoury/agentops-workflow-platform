"""Durable LLM continuation and reserved provider usage."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f090_llm_conversations"
down_revision = "f086_tool_contracts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "llm_conversations",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column("organization_id", UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("step_run_id", UUID(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("state", JSONB(), nullable=False),
        sa.UniqueConstraint("id", "organization_id", name="uq_llm_conversations_tenant_identity"),
        sa.UniqueConstraint("step_run_id"),
        sa.ForeignKeyConstraint(
            ["step_run_id", "organization_id"],
            ["step_runs.id", "step_runs.organization_id"],
            name="fk_llm_conversations_step_run_id_tenant",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint("octet_length(state::text) <= 2097152", name="ck_llm_state_bound"),
    )
    op.create_index(
        "ix_llm_conversations_organization_id", "llm_conversations", ["organization_id"]
    )
    op.execute("""
    CREATE FUNCTION preserve_llm_conversation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Retain LLM conversation history'; END IF;
      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
         OR NEW.step_run_id IS DISTINCT FROM OLD.step_run_id
         OR NEW.fingerprint IS DISTINCT FROM OLD.fingerprint THEN
        RAISE EXCEPTION 'Conversation identity is immutable';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER llm_conversation_history BEFORE UPDATE OR DELETE ON llm_conversations
      FOR EACH ROW EXECUTE FUNCTION preserve_llm_conversation();
    """)


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM llm_conversations)")):
        raise RuntimeError("Retain LLM conversation history")
    op.drop_table("llm_conversations")
    op.execute("DROP FUNCTION preserve_llm_conversation()")
