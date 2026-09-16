"""Private bounded continuation state; public traces expose only safe metadata."""

import uuid

from sqlalchemy import CheckConstraint, String, UniqueConstraint, event, inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints


class LLMConversation(TenantOwned, Base):
    __tablename__ = "llm_conversations"
    __table_args__ = (
        *tenant_constraints(__tablename__, {"step_run_id": "step_runs"}),
        UniqueConstraint("step_run_id"),
        CheckConstraint("octet_length(state::text) <= 2097152", name="ck_llm_state_bound"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    step_run_id: Mapped[uuid.UUID] = mapped_column(UUID())
    fingerprint: Mapped[str] = mapped_column(String(64))
    state: Mapped[dict] = mapped_column(JSONB)


@event.listens_for(Session, "before_flush")
def protect_conversations(db, _context, _instances):
    for item in db.new | db.dirty | db.deleted:
        if not isinstance(item, LLMConversation):
            continue
        if item in db.deleted:
            raise ValueError("Retain LLM conversation history")
        if not db.info.get("llm_conversation_write"):
            raise ValueError("Conversation changes require an owned worker checkpoint")
        if item not in db.new and any(
            inspect(item).attrs[key].history.has_changes()
            for key in ("id", "step_run_id", "fingerprint")
        ):
            raise ValueError("Conversation identity is immutable")
