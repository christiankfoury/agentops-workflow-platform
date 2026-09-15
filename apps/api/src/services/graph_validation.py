"""Pure graph validation; no eval, imports, provider calls or executor dispatch."""

from collections import defaultdict, deque
from math import isfinite

from pydantic import ValidationError

from src.schemas.workflow_graph import DataSchema, Expression, WorkflowGraph


def invalid(path, message):
    raise ValidationError.from_exception_data(
        "WorkflowGraph",
        [
            {
                "type": "value_error",
                "loc": tuple(path),
                "input": None,
                "ctx": {"error": ValueError(message)},
            }
        ],
    )


def compatible(actual: DataSchema, expected: DataSchema) -> bool:
    actual_types = actual.types - ({"integer"} if "number" in expected.types else set())
    if not actual_types <= expected.types:
        return False
    if "object" in actual.types:
        return (
            actual.properties.keys() <= expected.properties.keys()
            and set(expected.required) <= set(actual.required)
            and all(
                compatible(value, expected.properties[key])
                for key, value in actual.properties.items()
            )
        )
    if "array" in actual.types:
        return compatible(actual.items, expected.items)
    return True


def validate_data(value, schema: DataSchema, path=()):
    """Strict JSON type checks, reused by later starts and executor boundaries."""
    kind = (
        "null"
        if value is None
        else "boolean"
        if isinstance(value, bool)
        else "integer"
        if isinstance(value, int)
        else "number"
        if isinstance(value, float)
        else "string"
        if isinstance(value, str)
        else "array"
        if isinstance(value, list)
        else "object"
        if isinstance(value, dict)
        else "invalid"
    )
    if kind not in schema.types and not (kind == "integer" and "number" in schema.types):
        invalid(path, f"Expected {sorted(schema.types)}, received {kind}")
    if kind == "number" and not isfinite(value):
        invalid(path, "Numbers must be finite")
    if kind == "object":
        if not set(schema.required) <= value.keys() or not value.keys() <= schema.properties.keys():
            invalid(path, "Object has missing required or undeclared fields")
        for key, item in value.items():
            validate_data(item, schema.properties[key], (*path, key))
    elif kind == "array":
        for index, item in enumerate(value):
            validate_data(item, schema.items, (*path, index))


def literal_schema(value) -> DataSchema:
    if value is None:
        return DataSchema(type="null")
    if isinstance(value, bool):
        return DataSchema(type="boolean")
    if isinstance(value, int):
        return DataSchema(type="integer")
    if isinstance(value, float):
        return DataSchema(type="number")
    if isinstance(value, str):
        return DataSchema(type="string")
    if isinstance(value, list):
        items = literal_schema(value[0]) if value else DataSchema(type="null")
        for item in value:
            validate_data(item, items)
        return DataSchema(type="array", items=items)
    return DataSchema(
        type="object",
        properties={key: literal_schema(item) for key, item in value.items()},
        required=list(value),
    )


def nullable(schema):
    result = schema.model_copy(deep=True)
    kinds = schema.types | {"null"}
    result.type = sorted(kinds) if len(kinds) > 1 else "null"
    return result


def expression_schema(expr: Expression, graph, nodes, ancestors, consumer, path, depth=0):
    if depth > 8:
        invalid(path, "Expression nesting exceeds eight operations")
    if expr.op == "literal":
        return literal_schema(expr.value)
    if expr.op == "ref":
        ref = expr.ref
        if ref.source == "input":
            schema = graph.input_schema
        else:
            if ref.node_id not in nodes:
                invalid((*path, "ref", "node_id"), "Unknown producer node")
            if consumer is not None and ref.node_id not in ancestors[consumer]:
                invalid((*path, "ref", "node_id"), "Producer must precede the consuming node")
            schema = nodes[ref.node_id].output_schema
        for key in ref.path:
            if isinstance(key, str) and "object" in schema.types and key in schema.properties:
                schema = schema.properties[key]
            elif type(key) is int and "array" in schema.types:
                schema = schema.items
            else:
                invalid((*path, "ref", "path"), f"Undeclared field or invalid array index: {key}")
        if ref.on_missing == "default":
            validate_data(ref.default, schema, (*path, "ref", "default"))
        return nullable(schema) if ref.on_missing == "null" else schema
    args = [
        expression_schema(arg, graph, nodes, ancestors, consumer, (*path, "args", i), depth + 1)
        for i, arg in enumerate(expr.args)
    ]
    kinds = [arg.types for arg in args]
    if expr.op in {"eq", "ne", "exists"}:
        return DataSchema(type="boolean")
    if expr.op in {"and", "or", "not"}:
        if any(kind != {"boolean"} for kind in kinds):
            invalid(path, "Boolean operations require non-null boolean operands")
        return DataSchema(type="boolean")
    if expr.op in {"gt", "gte", "lt", "lte"}:
        if not (
            all(kind <= {"integer", "number"} for kind in kinds)
            or all(kind == {"string"} for kind in kinds)
        ):
            invalid(path, "Ordering requires matching non-null numeric or string operands")
        return DataSchema(type="boolean")
    if expr.op in {"add", "subtract", "multiply"}:
        if any(not kind <= {"integer", "number"} for kind in kinds):
            invalid(path, "Arithmetic requires non-null numbers")
        return DataSchema(type="number" if any("number" in kind for kind in kinds) else "integer")
    if expr.op == "concat":
        if any(kind != {"string"} for kind in kinds):
            invalid(path, "concat requires non-null strings")
        return DataSchema(type="string")
    # Coalesce handles explicit null. Missing values use the reference's separate policy.
    first = args[0].model_copy(deep=True)
    if first.types == {"null"}:
        return args[1]
    first.type = next(iter(first.types - {"null"}))
    if not compatible(args[1], nullable(first)):
        invalid(path, "coalesce operands have incompatible types")
    return nullable(first) if "null" in args[1].types else first


def bindings(values, expected, graph, nodes, ancestors, consumer, path):
    if expected.types != {"object"}:
        invalid(path, "Binding maps require a non-null object schema")
    if (
        not set(expected.required) <= values.keys()
        or not values.keys() <= expected.properties.keys()
    ):
        invalid(path, "Bindings must cover required fields and cannot invent fields")
    for key, expr in values.items():
        field_path = (*path, key)
        if expr.op == "literal":
            validate_data(expr.value, expected.properties[key], field_path)
        elif not compatible(
            expression_schema(expr, graph, nodes, ancestors, consumer, field_path),
            expected.properties[key],
        ):
            invalid(field_path, "Expression type is incompatible with the destination schema")


def validate_graph_contract(graph: WorkflowGraph):
    nodes = {node.id: node for node in graph.nodes}
    positions = {node.id: index for index, node in enumerate(graph.nodes)}
    if len(nodes) != len(graph.nodes):
        invalid(("nodes",), "Node IDs must be unique")
    if graph.entry_node not in nodes:
        invalid(("entry_node",), "Entry node does not exist")
    outgoing, incoming = defaultdict(list), defaultdict(list)
    seen = set()
    for index, edge in enumerate(graph.edges):
        if edge.source not in nodes or edge.target not in nodes:
            invalid(("edges", index), "Edge references a missing node")
        identity = (edge.source, edge.target, edge.label)
        if identity in seen:
            invalid(("edges", index), "Duplicate edge")
        seen.add(identity)
        outgoing[edge.source].append(edge)
        incoming[edge.target].append(edge)
    if incoming[graph.entry_node]:
        invalid(("entry_node",), "Entry node cannot have incoming edges")
    queue, reached = [graph.entry_node], set()
    while queue:
        current = queue.pop()
        if current in reached:
            continue
        reached.add(current)
        queue.extend(edge.target for edge in outgoing[current])
    if reached != nodes.keys():
        invalid(("nodes",), f"Unreachable nodes: {sorted(nodes.keys() - reached)}")
    degrees = {key: len(incoming[key]) for key in nodes}
    ready, order, ancestors = deque([graph.entry_node]), [], defaultdict(set)
    signatures = defaultdict(list)
    signatures[graph.entry_node] = [frozenset()]
    while ready:
        key = ready.popleft()
        order.append(key)
        if nodes[key].type == "parallel" and nodes[key].config.mode == "join":
            # A closed all-selected region completes once for each activation of
            # its fork. Internal branch choices are no longer alternative routes
            # into downstream merges. Region matching is checked below.
            signatures[key] = list(signatures[nodes[key].config.fork_node])
        for edge in outgoing[key]:
            ancestors[edge.target] |= ancestors[key] | {key}
            extra = {(key, edge.label)} if nodes[key].type == "condition" else set()
            signatures[edge.target].extend(signature | extra for signature in signatures[key])
            if len(signatures[edge.target]) > 256:
                invalid(("nodes", positions[edge.target]), "Graph exceeds 256 routing paths")
            degrees[edge.target] -= 1
            if degrees[edge.target] == 0:
                ready.append(edge.target)
    if len(order) != len(nodes):
        invalid(("edges",), "Arbitrary graph cycles are forbidden")
    for key in order:
        node, edges = nodes[key], outgoing[key]
        path = ("nodes", positions[key])
        bindings(node.inputs, node.input_schema, graph, nodes, ancestors, key, (*path, "inputs"))
        if node.type == "condition":
            labels = [case.label for case in node.config.cases] + [node.config.default]
            if len(set(labels)) != len(labels) or sorted(labels) != sorted(
                edge.label or "" for edge in edges
            ):
                invalid(
                    (*path, "config"), "Condition requires exactly one edge per case and default"
                )
            for i, case in enumerate(node.config.cases):
                location = (*path, "config", "cases", i, "when")
                if expression_schema(case.when, graph, nodes, ancestors, key, location).types != {
                    "boolean"
                }:
                    invalid(location, "Condition predicate must be a non-null boolean")
        elif node.type == "parallel" and node.config.mode == "fork":
            validate_region(node, nodes, outgoing, incoming, path)
        elif len(edges) > 1 or any(edge.label is not None for edge in edges):
            invalid(path, "Only conditions and parallel forks may select labeled/multiple edges")
        if node.type == "parallel" and node.config.mode == "join":
            fork = nodes.get(node.config.fork_node)
            if (
                fork is None
                or fork.type != "parallel"
                or fork.config.mode != "fork"
                or fork.config.join_node != key
            ):
                invalid((*path, "config", "fork_node"), "Join must reference its matching fork")
        elif len(incoming[key]) > 1:
            if node.merge != "exclusive":
                invalid(
                    (*path, "merge"), "Multiple incoming edges require an explicit exclusive merge"
                )
            routes = signatures[key]
            for i, left in enumerate(routes):
                for right in routes[i + 1 :]:
                    if not any(a == b and x != y for a, x in left for b, y in right):
                        invalid((*path, "merge"), "Incoming routes are not mutually exclusive")
        if node.type == "transform":
            bindings(
                node.config.assign,
                node.output_schema,
                graph,
                nodes,
                ancestors,
                key,
                (*path, "config", "assign"),
            )
    bindings(graph.outputs, graph.output_schema, graph, nodes, ancestors, None, ("outputs",))
    if graph.quality_revision:
        policy = graph.quality_revision
        region = set(policy.nodes)
        if (
            len(region) != len(policy.nodes)
            or not region <= nodes.keys()
            or not {policy.entry_node, policy.review_node} <= region
            or policy.entry_node not in ancestors[policy.review_node]
            or any(
                key != policy.entry_node and policy.entry_node not in ancestors[key]
                for key in region
            )
            or any(
                key != policy.review_node and key not in ancestors[policy.review_node]
                for key in region
            )
            or any(
                edge.source not in region
                for key in region - {policy.entry_node}
                for edge in incoming[key]
            )
            or any(
                edge.target not in region
                for key in region - {policy.review_node}
                for edge in outgoing[key]
            )
        ):
            invalid(
                ("quality_revision",),
                "Revision metadata must describe an ordered entry-to-review subgraph",
            )


def validate_region(fork, nodes, outgoing, incoming, path):
    config = fork.config
    join = nodes.get(config.join_node)
    if (
        join is None
        or join.type != "parallel"
        or join.config.mode != "join"
        or join.config.fork_node != fork.id
    ):
        invalid((*path, "config", "join_node"), "Fork requires its matching all-selected join")
    expected = {(branch.name, branch.entry_node) for branch in config.branches}
    if (
        len({branch.name for branch in config.branches}) != len(config.branches)
        or len({branch.entry_node for branch in config.branches}) != len(config.branches)
        or expected != {(edge.label, edge.target) for edge in outgoing[fork.id]}
    ):
        invalid(
            (*path, "config", "branches"), "Fork edges must match distinct named branch entries"
        )
    all_nodes = set()
    for branch in config.branches:
        pending, region = [branch.entry_node], set()
        if branch.entry_node == join.id:
            invalid(path, "Parallel branch cannot be empty")
        while pending:
            key = pending.pop()
            if key == join.id or key in region:
                continue
            region.add(key)
            if not outgoing[key]:
                invalid(path, f"Branch {branch.name} terminates before its join")
            pending.extend(edge.target for edge in outgoing[key])
        if region & all_nodes:
            invalid(path, "Parallel branches overlap before their declared join")
        if any(edge.source not in region | {fork.id} for key in region for edge in incoming[key]):
            invalid(path, "Parallel branch has an incoming edge from outside its region")
        all_nodes |= region
    if any(edge.source not in all_nodes for edge in incoming[join.id]):
        invalid(path, "Parallel join receives an edge outside its declared branches")


def ensure_executable(graph: WorkflowGraph, available_types=(), *, quality_revisions=False):
    """Call with the actual executor registry at publication/start boundaries."""
    for index, node in enumerate(graph.nodes):
        if node.type not in available_types:
            invalid(("nodes", index, "type"), f"Executor is not available: {node.type}")
    if graph.quality_revision and not quality_revisions:
        invalid(("quality_revision",), "Quality revision execution is not available")
