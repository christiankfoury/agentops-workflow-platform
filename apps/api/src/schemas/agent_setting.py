import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.agent_type import AgentType

ALLOWED_AGENT_MODELS = ("gpt-4.1-mini", "gpt-4.1", "gpt-4.1-nano")


class AgentSettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None
    agent_type: AgentType
    model: str
    temperature: float | None
    max_tokens: int
    timeout_seconds: float | None
    max_retries: int
    active_prompt_version_id: uuid.UUID | None
    active_prompt_name: str | None
    reviewer_approval_threshold: float | None
    human_approval_threshold: float | None


class AgentSettingUpdate(BaseModel):
    model: str = Field(min_length=1, max_length=100)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int = Field(gt=0)
    timeout_seconds: float | None = Field(default=None, gt=0)
    max_retries: int = Field(ge=0)
    active_prompt_version_id: uuid.UUID | None = None
    reviewer_approval_threshold: float | None = Field(default=None, ge=0, le=1)
    human_approval_threshold: float | None = Field(default=None, ge=0, le=1)

    @field_validator("model")
    @classmethod
    def validate_supported_model(cls, value: str) -> str:
        if value not in ALLOWED_AGENT_MODELS:
            allowed = ", ".join(ALLOWED_AGENT_MODELS)
            raise ValueError(f"Model must be one of: {allowed}")
        return value
