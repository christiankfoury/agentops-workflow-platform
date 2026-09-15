"""Constrained expression evaluator. No eval, dynamic imports or user code."""

from copy import deepcopy
from math import isfinite

from src.schemas.workflow_graph import WorkflowGraph
from src.services.graph_validation import validate_data

MISSING = object()


class ExecutionError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def resolve_reference(ref, inputs, outputs):
    value = inputs if ref.source == "input" else outputs.get(ref.node_id, MISSING)
    for key in ref.path:
        if isinstance(value, dict) and isinstance(key, str):
            value = value.get(key, MISSING)
        elif isinstance(value, list) and type(key) is int and 0 <= key < len(value):
            value = value[key]
        else:
            return MISSING
    return value


def equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def evaluate(expr, inputs, outputs):
    if expr.op == "literal":
        return deepcopy(expr.value)
    if expr.op == "ref":
        value = resolve_reference(expr.ref, inputs, outputs)
        if value is MISSING:
            if expr.ref.on_missing == "error":
                raise ExecutionError("binding_missing", "Required reference is missing")
            value = expr.ref.default if expr.ref.on_missing == "default" else None
        return deepcopy(value)
    if expr.op == "exists":
        if expr.args[0].op == "ref":
            return resolve_reference(expr.args[0].ref, inputs, outputs) is not MISSING
        try:
            evaluate(expr.args[0], inputs, outputs)
            return True
        except ExecutionError as error:
            if error.code != "binding_missing":
                raise
            return False
    first = evaluate(expr.args[0], inputs, outputs)
    if expr.op == "not":
        return not first
    if expr.op == "and" and not first:
        return False
    if expr.op == "or" and first:
        return True
    if expr.op == "coalesce" and first is not None:
        return first
    second = evaluate(expr.args[1], inputs, outputs)
    operations = {
        "eq": lambda: equal(first, second),
        "ne": lambda: not equal(first, second),
        "gt": lambda: first > second,
        "gte": lambda: first >= second,
        "lt": lambda: first < second,
        "lte": lambda: first <= second,
        "and": lambda: bool(second),
        "or": lambda: bool(second),
        "coalesce": lambda: second,
        "concat": lambda: first + second,
        "add": lambda: first + second,
        "subtract": lambda: first - second,
        "multiply": lambda: first * second,
    }
    try:
        result = operations[expr.op]()
    except OverflowError as error:
        raise ExecutionError("expression_range", "Expression exceeded numeric range") from error
    if isinstance(result, float) and not isfinite(result):
        raise ExecutionError("expression_range", "Expression produced a non-finite number")
    return result


def resolve_bindings(bindings, inputs, outputs, schema):
    value = {key: evaluate(expr, inputs, outputs) for key, expr in bindings.items()}
    validate_data(value, schema)
    WorkflowGraph.payload_bounds({"value": value})
    return value
