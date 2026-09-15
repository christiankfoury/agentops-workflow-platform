import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from src.schemas.workflow_graph import WorkflowGraph


class DefinitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    graph: dict[str, JsonValue]

    @model_validator(mode="after")
    def bounded_draft(self):
        if not self.name.strip():
            raise ValueError("Name cannot be blank")
        WorkflowGraph.payload_bounds(self.graph)
        return self


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, strict=True)


class DefinitionUpdate(DefinitionCreate, RevisionRequest):
    pass


class DefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str
    draft_graph: dict
    draft_revision: int
    published_version_id: uuid.UUID | None
    archived: bool
    created_at: datetime
    updated_at: datetime


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    definition_id: uuid.UUID
    number: int
    source_revision: int
    name: str
    description: str
    graph: dict
    graph_hash: str
    prompt_snapshots: dict
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    archived_at: datetime | None


class ValidationResult(BaseModel):
    valid: bool
    executable: bool = False
    errors: list[dict] = Field(default_factory=list)
    runtime_errors: list[dict] = Field(default_factory=list)
