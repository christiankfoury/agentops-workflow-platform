import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.models.workflow_event import WorkflowEventType


class WorkflowEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_run_id: uuid.UUID
    agent_step_id: uuid.UUID | None
    event_type: WorkflowEventType
    message: str
    metadata_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
