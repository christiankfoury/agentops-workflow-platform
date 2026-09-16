import uuid
from typing import Annotated, Literal

from pydantic import Field, model_validator

from src.schemas.workflow_graph import GraphModel, Reference, WorkflowGraph

SecretAlias = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,99}$")]


class WebhookConfig(GraphModel):
    name: str = Field(min_length=1, max_length=200)
    definition_id: uuid.UUID
    version_policy: Literal["published", "pinned"] = "published"
    version_id: uuid.UUID | None = None
    service_principal_id: uuid.UUID
    enabled: bool = True
    input_mapping: dict[Annotated[str, Field(min_length=1, max_length=100)], Reference] | None = (
        Field(default=None, max_length=100)
    )
    max_payload_bytes: int = Field(default=65536, ge=1024, le=262144, strict=True)
    freshness_seconds: int = Field(default=300, ge=30, le=600, strict=True)

    @model_validator(mode="after")
    def bounded_configuration(self):
        if not self.name.strip():
            raise ValueError("Name cannot be blank")
        if (self.version_policy == "pinned") != (self.version_id is not None):
            raise ValueError("Only pinned selection requires a version ID")
        if any(ref.source != "input" for ref in (self.input_mapping or {}).values()):
            raise ValueError("Webhook mappings can reference only the signed payload")
        WorkflowGraph.payload_bounds(self.model_dump(mode="json"))
        return self


class WebhookCreate(WebhookConfig):
    secret_alias: SecretAlias = Field(json_schema_extra={"writeOnly": True})


class WebhookUpdate(WebhookConfig):
    expected_revision: int = Field(ge=1, strict=True)


class WebhookRotate(GraphModel):
    expected_revision: int = Field(ge=1, strict=True)
    secret_alias: SecretAlias = Field(json_schema_extra={"writeOnly": True})
    grace_seconds: int = Field(default=300, ge=0, le=3600, strict=True)
