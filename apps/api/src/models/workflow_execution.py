import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    event,
    inspect,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from src.database import Base
from src.models.tenant import TenantOwned, tenant_constraints

TERMINAL = {"completed", "failed", "cancelled", "skipped"}


class ExecutionFields:
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    input_json: Mapped[dict | None] = mapped_column(JSONB)
    output_json: Mapped[dict | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


def status_constraint(states):
    return CheckConstraint("status IN (" + ",".join(f"'{state}'" for state in states) + ")")


class WorkflowExecution(ExecutionFields, TenantOwned, Base):
    __tablename__ = "workflow_executions"
    __table_args__ = (
        *tenant_constraints(
            __tablename__,
            {
                "version_id": "workflow_versions",
                "legacy_run_id": "workflow_runs",
            },
        ),
        status_constraint(
            ["pending", "running", "waiting", "retrying", "completed", "failed", "cancelled"]
        ),
        CheckConstraint("state_revision >= 0"),
    )
    version_id: Mapped[uuid.UUID] = mapped_column(UUID())
    legacy_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID())
    business_type: Mapped[str | None] = mapped_column(String(40))
    run_mode: Mapped[str | None] = mapped_column(String(40))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    state_revision: Mapped[int] = mapped_column(Integer, default=0)
    checkpoint_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StepRun(ExecutionFields, TenantOwned, Base):
    __tablename__ = "step_runs"
    __table_args__ = (
        *tenant_constraints(__tablename__, {"execution_id": "workflow_executions"}),
        UniqueConstraint("execution_id", "node_id", "branch", "iteration", name="uq_logical_step"),
        CheckConstraint("iteration >= 0"),
        status_constraint(
            [
                "pending",
                "running",
                "waiting",
                "retrying",
                "completed",
                "failed",
                "cancelled",
                "skipped",
            ]
        ),
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID())
    node_id: Mapped[str] = mapped_column(String(64))
    step_type: Mapped[str] = mapped_column(String(20))
    branch: Mapped[str] = mapped_column(String(256), default="main")
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StepAttempt(ExecutionFields, TenantOwned, Base):
    __tablename__ = "step_attempts"
    __table_args__ = (
        *tenant_constraints(__tablename__, {"step_run_id": "step_runs"}),
        UniqueConstraint("step_run_id", "number", name="uq_step_attempt_number"),
        CheckConstraint("number >= 1"),
        CheckConstraint(
            "error_classification IS NULL OR error_classification IN ('retryable','permanent')"
        ),
        status_constraint(["pending", "running", "completed", "failed", "cancelled"]),
    )
    step_run_id: Mapped[uuid.UUID] = mapped_column(UUID())
    number: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    llm_metadata: Mapped[dict | None] = mapped_column(JSONB)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_classification: Mapped[str | None] = mapped_column(String(20))


class ExecutionEvent(TenantOwned, Base):
    __tablename__ = "execution_events"
    __table_args__ = tenant_constraints(__tablename__, {"execution_id": "workflow_executions"})
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID())
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(Session, "before_flush")
def preserve_execution_identity(db, _context, _instances):
    identities = {
        WorkflowExecution: (
            "version_id",
            "legacy_run_id",
            "created_by_user_id",
            "business_type",
            "run_mode",
        ),
        StepRun: ("execution_id", "node_id", "step_type", "branch", "iteration", "idempotency_key"),
        StepAttempt: ("step_run_id", "number", "idempotency_key"),
    }
    for item in db.new:
        if type(item) in identities and item.status not in {None, "pending"}:
            raise ValueError("New execution records must begin pending")
    for item in db.dirty | db.deleted:
        if type(item) not in identities:
            continue
        state = inspect(item)
        if item in db.deleted or any(
            state.attrs[key].history.has_changes() for key in identities[type(item)]
        ):
            raise ValueError("Execution identity and history are immutable")
        if not db.is_modified(item):
            continue
        owner = (
            item.id
            if isinstance(item, WorkflowExecution)
            else (
                item.execution_id
                if isinstance(item, StepRun)
                else db.scalar(
                    select(StepRun.execution_id).where(StepRun.id == item.step_run_id),
                )
            )
        )
        if db.info.get("workflow_transaction") != (WorkflowExecution, owner):
            raise ValueError("Execution changes require their run's transition authority")
        status_history = state.attrs.status.history
        previous_status = status_history.deleted[0] if status_history.deleted else item.status
        if previous_status in TERMINAL and any(
            attr.history.has_changes() for attr in state.attrs if attr.key != "state_revision"
        ):
            raise ValueError("Terminal execution records cannot change")
