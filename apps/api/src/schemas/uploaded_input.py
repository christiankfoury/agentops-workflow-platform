import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.uploaded_input import InputType


class UploadedInputCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    input_type: InputType
    raw_text: str = Field(min_length=1)
    notes: str | None = None
    file_name: str | None = Field(default=None, max_length=255)
    file_type: str | None = Field(default=None, max_length=50)
    file_size: int | None = Field(default=None, ge=0)
    organization_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID | None = None


class UploadedInputRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    title: str
    input_type: InputType
    raw_text: str
    notes: str | None
    file_name: str | None
    file_type: str | None
    file_size: int | None
    created_at: datetime
