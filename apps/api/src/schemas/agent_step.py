import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.models.agent_step import AgentStepStatus


class AgentStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_run_id: uuid.UUID
    agent_name: str
    agent_type: str
    step_order: int
    status: AgentStepStatus
    input_json: dict[str, Any] | None
    output_json: dict[str, Any] | None
    model: str | None
    prompt_version_id: uuid.UUID | None
    tokens_input: int | None
    tokens_output: int | None
    total_tokens: int | None
    cost: float | None
    latency_ms: int | None
    retry_count: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
