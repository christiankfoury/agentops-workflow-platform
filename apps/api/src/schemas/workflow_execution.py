import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.schemas.agent_step import AgentStepRead
from src.schemas.workflow_run import WorkflowRunRead


class ExecutionFieldsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    input_json: dict | None
    output_json: dict | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    heartbeat_at: datetime | None
    completed_at: datetime | None


class ExecutionRead(ExecutionFieldsRead):
    version_id: uuid.UUID
    legacy_run_id: uuid.UUID | None
    business_type: str | None
    run_mode: str | None
    created_by_user_id: uuid.UUID | None
    state_revision: int
    checkpoint_json: dict
    deadline_at: datetime | None
    cancel_requested: bool
    cancel_requested_at: datetime | None
    cancel_requested_by_user_id: uuid.UUID | None
    cancel_reason: str | None


class StepRunRead(ExecutionFieldsRead):
    execution_id: uuid.UUID
    node_id: str
    step_type: str
    branch: str
    iteration: int
    idempotency_key: str
    next_attempt_at: datetime | None


class StepAttemptRead(ExecutionFieldsRead):
    step_run_id: uuid.UUID
    number: int
    idempotency_key: str
    llm_metadata: dict | None
    deadline_at: datetime | None
    error_classification: str | None


class LegacyTraceRead(BaseModel):
    source: Literal["legacy"] = "legacy"
    run: WorkflowRunRead
    agent_steps: list[AgentStepRead]


class ExecutionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    execution_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    from_status: str | None
    to_status: str
    details: dict
    created_at: datetime
