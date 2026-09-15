import uuid

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from src.schemas.workflow_graph import WorkflowGraph


class ExecutionStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition_id: uuid.UUID
    version_id: uuid.UUID | None = None
    input: dict[str, JsonValue]
    idempotency_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")

    @model_validator(mode="after")
    def bounded_input(self):
        WorkflowGraph.payload_bounds({"input": self.input})
        return self
