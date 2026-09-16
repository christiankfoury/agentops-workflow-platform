"""Server-owned executor registrations; graph payloads cannot register handlers."""

from copy import deepcopy
from dataclasses import dataclass

from src.schemas.workflow_graph import DataSchema
from src.services.graph_expressions import ExecutionError, evaluate, resolve_bindings
from src.services.graph_validation import compatible, invalid
from src.services.graph_validation import ensure_executable as validate_types


@dataclass(frozen=True)
class NodeResult:
    output: dict
    route: str | None = None
    llm_metadata: dict | None = None


class ExecutorRegistry:
    def __init__(self):
        from src.services.llm_execution import client_factory

        self.llm_factory = client_factory
        from src.services.business_outputs import FEEDBACK_MODELS, final_report, model_validator
        from src.services.business_schemas import graph_schema

        self.output_validators = {"business.final_report.v1": final_report}
        self.output_contracts = {
            "business.final_report.v1": DataSchema(
                type="object",
                properties={"final_output": DataSchema(type="string")},
                required=["final_output"],
            )
        }
        for name, model in FEEDBACK_MODELS.items():
            self.output_validators[name] = model_validator(model)
            self.output_contracts[name] = DataSchema.model_validate(
                graph_schema(model.model_json_schema())
            )
        self.handlers = {("builtin.identity", 1): deepcopy}
        self.controlled_handlers = {}
        self.executors = {
            "code": self.code,
            "transform": self.transform,
            "condition": self.condition,
            "parallel": self.parallel,
        }

    def validate(self, graph):
        # Delay checkpoints are registered transactionally, without an I/O executor.
        from src.services.quality_revisions import validate_policy

        validate_types(graph, {*self.executors, "delay", "approval", "llm"}, quality_revisions=True)
        validate_policy(graph)
        for index, node in enumerate(graph.nodes):
            if (
                node.type in {"llm", "approval"}
                and node.config.output_validator is not None
                and node.config.output_validator not in self.output_validators
            ):
                invalid(("nodes", index, "config"), "Registered output validator is unavailable")
            if (
                node.type in {"llm", "approval"}
                and node.config.output_validator in self.output_contracts
                and not compatible(
                    node.output_schema, self.output_contracts[node.config.output_validator]
                )
            ):
                invalid(
                    ("nodes", index, "output_schema"), "Output validator contract does not match"
                )
            if node.type == "llm" and node.output_schema.types != {"object"}:
                invalid(("nodes", index, "output_schema"), "LLM output must be a non-null object")
            if (
                node.type == "code"
                and (node.config.handler, node.config.version) not in self.handlers
                and (node.config.handler, node.config.version) not in self.controlled_handlers
            ):
                invalid(
                    ("nodes", index, "config"), "Registered code handler/version is unavailable"
                )

    def code(self, node, inputs, context, control=None):
        try:
            controlled = self.controlled_handlers.get((node.config.handler, node.config.version))
            if controlled is not None:
                return NodeResult(controlled(deepcopy(inputs), control))
            handler = self.handlers[(node.config.handler, node.config.version)]
            return NodeResult(handler(deepcopy(inputs)))
        except Exception as error:
            raise ExecutionError(
                "handler_failed", "Registered deterministic handler failed"
            ) from error

    def transform(self, node, inputs, context, control=None):
        return NodeResult(resolve_bindings(node.config.assign, *context, node.output_schema))

    def condition(self, node, inputs, context, control=None):
        label = next(
            (case.label for case in node.config.cases if evaluate(case.when, *context)),
            node.config.default,
        )
        return NodeResult({}, label)

    def execute(self, node, inputs, context, control=None):
        executor = self.executors.get(node.type)
        if executor is None:
            raise ExecutionError("unsupported_executor", "Step executor is unavailable")
        return executor(node, inputs, context, control)

    def parallel(self, node, inputs, context, control=None):
        # A join's declared bindings assemble named branch outputs in a stable order.
        return NodeResult({key: deepcopy(inputs[key]) for key in sorted(inputs)})


DEFAULT_REGISTRY = ExecutorRegistry()


def ensure_executable(graph):
    DEFAULT_REGISTRY.validate(graph)
