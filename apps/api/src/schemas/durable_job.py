import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    execution_id: uuid.UUID
    sequence: int
    status: str
    attempt_id: uuid.UUID | None
    worker_id: str | None
    created_at: datetime
    due_at: datetime
    claimed_at: datetime | None
    dispatched_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
