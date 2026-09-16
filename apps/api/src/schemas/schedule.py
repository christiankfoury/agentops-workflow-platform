import uuid
from typing import Literal

from pydantic import Field, JsonValue, model_validator

from src.schemas.workflow_graph import GraphModel, WorkflowGraph
from src.services.cron_schedule import validate_cron


class ScheduleConfig(GraphModel):
    name: str = Field(min_length=1, max_length=200)
    definition_id: uuid.UUID
    version_policy: Literal["published", "pinned"] = "published"
    version_id: uuid.UUID | None = None
    service_principal_id: uuid.UUID
    cron: str = Field(min_length=1, max_length=160)
    timezone: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    input: dict[str, JsonValue] = Field(default_factory=dict)
    concurrency_policy: Literal["forbid"] = "forbid"
    missed_run_policy: Literal["coalesce"] = "coalesce"

    @model_validator(mode="after")
    def valid_configuration(self):
        if not self.name.strip():
            raise ValueError("Name cannot be blank")
        if (self.version_policy == "pinned") != (self.version_id is not None):
            raise ValueError("Only pinned selection requires a version ID")
        validate_cron(self.cron, self.timezone)
        WorkflowGraph.payload_bounds({"input": self.input})
        return self


class ScheduleCreate(ScheduleConfig):
    pass


class ScheduleUpdate(ScheduleConfig):
    expected_revision: int = Field(ge=1, strict=True)
