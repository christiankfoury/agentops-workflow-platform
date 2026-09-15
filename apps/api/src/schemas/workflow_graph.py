"""Version 1 graph format. Recognition does not imply an available executor."""

import json
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictInt, StrictStr, model_validator

NodeID = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]
DataType = Literal["object", "array", "string", "integer", "number", "boolean", "null"]
STEP_TYPES = frozenset(
    {"llm", "code", "tool", "condition", "approval", "transform", "parallel", "delay"}
)


class GraphModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, populate_by_name=True, serialize_by_alias=True
    )


class DataSchema(GraphModel):
    """Closed JSON Schema subset; a type may additionally include null."""

    type: DataType | list[DataType]
    properties: dict[str, "DataSchema"] = Field(default_factory=dict, max_length=100)
    required: list[str] = Field(default_factory=list, max_length=100)
    items: "DataSchema | None" = None
    additional_properties: Literal[False] = Field(default=False, alias="additionalProperties")

    @property
    def types(self) -> set[str]:
        return set(self.type) if isinstance(self.type, list) else {self.type}

    @model_validator(mode="after")
    def valid_shape(self):
        if isinstance(self.type, list) and (
            len(self.type) != 2 or "null" not in self.type or len(set(self.type)) != 2
        ):
            raise ValueError("Type unions must contain one data type and null")
        if "object" not in self.types and (self.properties or self.required):
            raise ValueError("Only objects define properties/required fields")
        if (
            len(set(self.required)) != len(self.required)
            or not set(self.required) <= self.properties.keys()
        ):
            raise ValueError("Required fields must be unique declared properties")
        if ("array" in self.types) != (self.items is not None):
            raise ValueError("Exactly array schemas require items")
        return self


def object_schema() -> DataSchema:
    return DataSchema(type="object")


class Reference(GraphModel):
    source: Literal["input", "node"]
    node_id: NodeID | None = None
    path: list[StrictStr | StrictInt] = Field(default_factory=list, max_length=16)
    on_missing: Literal["error", "null", "default"] = "error"
    default: JsonValue = None

    @model_validator(mode="after")
    def source_shape(self):
        if (self.source == "node") != (self.node_id is not None):
            raise ValueError("Node references require node_id; input references forbid it")
        if any(isinstance(key, int) and (isinstance(key, bool) or key < 0) for key in self.path):
            raise ValueError("Array indexes must be nonnegative integers")
        if self.on_missing == "default" and "default" not in self.model_fields_set:
            raise ValueError("Only default missing behavior requires an explicit default value")
        if self.on_missing != "default" and self.default is not None:
            raise ValueError("A default value requires default missing behavior")
        return self


class Expression(GraphModel):
    op: Literal[
        "literal",
        "ref",
        "eq",
        "ne",
        "gt",
        "gte",
        "lt",
        "lte",
        "and",
        "or",
        "not",
        "exists",
        "add",
        "subtract",
        "multiply",
        "concat",
        "coalesce",
    ]
    value: JsonValue = None
    ref: Reference | None = None
    args: list["Expression"] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def operands(self):
        if self.op == "literal":
            if "value" not in self.model_fields_set or self.ref is not None or self.args:
                raise ValueError("literal requires value and forbids ref/args")
        elif self.op == "ref":
            if self.ref is None or self.value is not None or self.args:
                raise ValueError("ref requires a reference and forbids value/args")
        else:
            expected = 1 if self.op in {"not", "exists"} else 2
            if len(self.args) != expected or self.ref is not None or self.value is not None:
                raise ValueError(f"{self.op} requires exactly {expected} arguments")
        return self


class RetryPolicy(GraphModel):
    max_attempts: int = Field(default=1, ge=1, le=10)
    retryable_errors: list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]] = Field(
        default_factory=list, max_length=16
    )
    initial_delay_seconds: float = Field(default=1, ge=0, le=60)
    max_delay_seconds: float = Field(default=60, ge=0, le=3600)
    backoff_factor: float = Field(default=2, ge=1, le=10)
    jitter_fraction: float = Field(default=0.2, ge=0, le=1)

    @model_validator(mode="after")
    def delay_bounds(self):
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("Maximum retry delay must cover the initial delay")
        return self


class BaseNode(GraphModel):
    id: NodeID
    input_schema: DataSchema = Field(default_factory=object_schema)
    output_schema: DataSchema = Field(default_factory=object_schema)
    inputs: dict[str, Expression] = Field(default_factory=dict, max_length=100)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout_seconds: float = Field(default=60, gt=0, le=3600)
    merge: Literal["exclusive"] | None = None


class LLMConfig(GraphModel):
    prompt_version_id: uuid.UUID
    model: str = Field(min_length=1, max_length=100)
    max_tokens: int = Field(default=2048, ge=1, le=32768)
    temperature: float | None = Field(default=None, ge=0, le=2)


class CodeConfig(GraphModel):
    handler: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,99}$")
    version: int = Field(ge=1)


class ToolConfig(GraphModel):
    tool_id: uuid.UUID
    version: int = Field(ge=1)
    adapter: Literal["http"] = "http"


class ConditionCase(GraphModel):
    label: NodeID
    when: Expression


class ConditionConfig(GraphModel):
    cases: list[ConditionCase] = Field(min_length=1, max_length=8)
    default: NodeID = "default"


class ApprovalConfig(GraphModel):
    reviewer_roles: list[Literal["reviewer", "admin"]] = Field(
        default_factory=lambda: ["reviewer", "admin"], min_length=1, max_length=2
    )
    deadline_seconds: float | None = Field(default=None, gt=0, le=2592000)
    timeout_action: Literal["reject", "fail"] = "fail"


class TransformConfig(GraphModel):
    assign: dict[str, Expression] = Field(max_length=100)


class ParallelBranch(GraphModel):
    name: NodeID
    entry_node: NodeID


class ParallelConfig(GraphModel):
    mode: Literal["fork", "join"]
    branches: list[ParallelBranch] = Field(default_factory=list, max_length=8)
    join_node: NodeID | None = None
    fork_node: NodeID | None = None
    policy: Literal["all_selected"] = "all_selected"

    @model_validator(mode="after")
    def fork_join_shape(self):
        if self.mode == "fork":
            if len(self.branches) < 2 or self.join_node is None or self.fork_node is not None:
                raise ValueError("Fork requires at least two branches and a join_node")
        elif self.fork_node is None or self.branches or self.join_node is not None:
            raise ValueError("Join requires only a fork_node and all_selected policy")
        return self


class DelayConfig(GraphModel):
    seconds: float = Field(ge=0, le=604800)


class LLMNode(BaseNode):
    type: Literal["llm"]
    config: LLMConfig


class CodeNode(BaseNode):
    type: Literal["code"]
    config: CodeConfig


class ToolNode(BaseNode):
    type: Literal["tool"]
    config: ToolConfig


class ConditionNode(BaseNode):
    type: Literal["condition"]
    config: ConditionConfig


class ApprovalNode(BaseNode):
    type: Literal["approval"]
    config: ApprovalConfig = Field(default_factory=ApprovalConfig)


class TransformNode(BaseNode):
    type: Literal["transform"]
    config: TransformConfig


class ParallelNode(BaseNode):
    type: Literal["parallel"]
    config: ParallelConfig


class DelayNode(BaseNode):
    type: Literal["delay"]
    config: DelayConfig


StepDefinition = Annotated[
    LLMNode
    | CodeNode
    | ToolNode
    | ConditionNode
    | ApprovalNode
    | TransformNode
    | ParallelNode
    | DelayNode,
    Field(discriminator="type"),
]


class Edge(GraphModel):
    source: NodeID
    target: NodeID
    label: NodeID | None = None


class QualityRevisionPolicy(GraphModel):
    entry_node: NodeID
    review_node: NodeID
    nodes: list[NodeID] = Field(min_length=2, max_length=30)
    max_revisions: int = Field(ge=1, le=5)


class WorkflowGraph(GraphModel):
    schema_version: Literal[1] = 1
    entry_node: NodeID
    input_schema: DataSchema = Field(default_factory=object_schema)
    output_schema: DataSchema = Field(default_factory=object_schema)
    outputs: dict[str, Expression] = Field(default_factory=dict, max_length=100)
    nodes: list[StepDefinition] = Field(min_length=1, max_length=100)
    edges: list[Edge] = Field(default_factory=list, max_length=300)
    overall_timeout_seconds: float = Field(default=86400, gt=0, le=2592000)
    quality_revision: QualityRevisionPolicy | None = None

    @model_validator(mode="before")
    @classmethod
    def payload_bounds(cls, value):
        if isinstance(value, dict):
            if type(value.get("schema_version", 1)) is not int:
                raise ValueError("schema_version must be an integer")
            def depth(item, level=0):
                if level > 32:
                    raise ValueError("Graph nesting exceeds 32 levels")
                for child in (
                    item.values()
                    if isinstance(item, dict)
                    else item
                    if isinstance(item, list)
                    else []
                ):
                    depth(child, level + 1)

            depth(value)
            if len(json.dumps(value, allow_nan=False).encode()) > 262144:
                raise ValueError("Graph payload exceeds 256 KiB")
        return value

    @model_validator(mode="after")
    def graph_contract(self):
        from src.services.graph_validation import validate_graph_contract

        validate_graph_contract(self)
        self.payload_bounds(self.model_dump(mode="json"))
        return self
