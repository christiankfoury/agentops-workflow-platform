import uuid

from pydantic import BaseModel, ConfigDict, Field


class ExecutionCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = Field(default=None, max_length=1000)


class ExecutionCancelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    cancel_requested: bool
