import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.config import DEFAULT_MAX_INPUT_CHARS, DEFAULT_MAX_NOTES_CHARS
from src.models.uploaded_input import InputType
from src.models.workflow_run import WorkflowType


class UploadedInputCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    input_type: InputType
    raw_text: str = Field(min_length=1, max_length=DEFAULT_MAX_INPUT_CHARS)
    notes: str | None = Field(default=None, max_length=DEFAULT_MAX_NOTES_CHARS)
    file_name: str | None = Field(default=None, max_length=255)
    file_type: str | None = Field(default=None, max_length=50)
    file_size: int | None = Field(default=None, ge=0)
    organization_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID | None = None

    @field_validator("title", "raw_text", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("notes", "file_name", "file_type", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value


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


class WorkflowDetectionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    raw_text: str = Field(min_length=1, max_length=DEFAULT_MAX_INPUT_CHARS)
    notes: str | None = Field(default=None, max_length=DEFAULT_MAX_NOTES_CHARS)

    @field_validator("title", "raw_text", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value


class WorkflowDetectionRead(BaseModel):
    workflow_type: WorkflowType
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str
    recommended_action: Literal["auto_select", "confirm", "manual_required"]
