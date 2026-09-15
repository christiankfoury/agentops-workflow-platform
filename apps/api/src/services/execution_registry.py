"""Server-owned executor registrations; graph payloads cannot register handlers."""

from copy import deepcopy
from dataclasses import dataclass

from src.services.graph_expressions import ExecutionError, evaluate, resolve_bindings
from src.services.graph_validation import ensure_executable as validate_types
from src.services.graph_validation import invalid


@dataclass(frozen=True)
class NodeResult:
    output: dict
    route: str | None = None


class ExecutorRegistry:
    def __init__(self):
        self.handlers = {("builtin.identity", 1): deepcopy}
        self.controlled_handlers = {}
        self.executors = {
            "code": self.code,
            "transform": self.transform,
            "condition": self.condition,
        }

    def validate(self, graph):
        validate_types(graph, self.executors)
        for index, node in enumerate(graph.nodes):
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


DEFAULT_REGISTRY = ExecutorRegistry()


def ensure_executable(graph):
    DEFAULT_REGISTRY.validate(graph)
