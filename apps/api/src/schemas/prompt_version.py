import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.agent_type import AgentType


class PromptVersionCreate(BaseModel):
    agent_type: AgentType
    name: str = Field(min_length=1, max_length=255)
    version: int = Field(ge=1)
    template: str = Field(min_length=1)
    is_active: bool = False
    notes: str | None = None
    created_by_user_id: uuid.UUID | None = None


class PromptVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_type: AgentType
    name: str
    version: int
    template: str
    is_active: bool
    notes: str | None
    created_by_user_id: uuid.UUID | None
    created_at: datetime
