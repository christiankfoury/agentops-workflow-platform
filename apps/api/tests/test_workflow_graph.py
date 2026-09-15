from copy import deepcopy

import pytest
from pydantic import ValidationError

from src.schemas.workflow_graph import STEP_TYPES, DataSchema, WorkflowGraph
from src.services.graph_validation import ensure_executable, validate_data


def obj(**fields):
    return {"type": "object", "properties": fields, "required": list(fields)}


NUMBER, STRING, BOOLEAN = {"type": "number"}, {"type": "string"}, {"type": "boolean"}


def literal(value):
    return {"op": "literal", "value": value}


def ref(field, node=None, **options):
    return {
        "op": "ref",
        "ref": {
            "source": "node" if node else "input",
            "path": [field],
            **({"node_id": node} if node else {}),
            **options,
        },
    }


def code(name, **fields):
    return {
        "id": name,
        "type": "code",
        "config": {"handler": "builtin.identity", "version": 1},
        **fields,
    }


def edge(source, target, label=None):
    return {"source": source, "target": target, **({"label": label} if label else {})}


def all_primitives():
    return {
        "schema_version": 1,
        "entry_node": "start",
        "input_schema": obj(score=NUMBER, text=STRING),
        "output_schema": obj(text=STRING),
        "outputs": {"text": ref("text", "finish")},
        "nodes": [
            code(
                "start",
                input_schema=obj(score=NUMBER),
                inputs={"score": ref("score")},
                output_schema=obj(score=NUMBER),
            ),
            {
                "id": "choice",
                "type": "condition",
                "config": {
                    "cases": [
                        {
                            "label": "good",
                            "when": {"op": "gte", "args": [ref("score", "start"), literal(0.5)]},
                        }
                    ],
                    "default": "review",
                },
            },
            {
                "id": "fork",
                "type": "parallel",
                "config": {
                    "mode": "fork",
                    "join_node": "join",
                    "branches": [
                        {"name": "rewrite", "entry_node": "rewrite"},
                        {"name": "fetch", "entry_node": "fetch"},
                    ],
                },
            },
            {
                "id": "rewrite",
                "type": "transform",
                "output_schema": obj(text=STRING),
                "config": {
                    "assign": {"text": {"op": "concat", "args": [ref("text"), literal(" checked")]}}
                },
            },
            {
                "id": "fetch",
                "type": "tool",
                "config": {
                    "tool_id": "00000000-0000-0000-0000-000000000010",
                    "version": 1,
                },
            },
            {"id": "join", "type": "parallel", "config": {"mode": "join", "fork_node": "fork"}},
            {
                "id": "judge",
                "type": "llm",
                "config": {
                    "prompt_version_id": "00000000-0000-0000-0000-000000000020",
                    "model": "fixture-model",
                },
                "output_schema": obj(decision=BOOLEAN),
            },
            {
                "id": "human",
                "type": "approval",
                "input_schema": obj(decision=BOOLEAN),
                "inputs": {"decision": ref("decision", "judge")},
                "config": {"deadline_seconds": 3600},
            },
            {"id": "wait", "type": "delay", "merge": "exclusive", "config": {"seconds": 10}},
            code(
                "finish",
                input_schema=obj(text=STRING),
                output_schema=obj(text=STRING),
                inputs={"text": ref("text")},
            ),
        ],
        "edges": [
            edge("start", "choice"),
            edge("choice", "fork", "good"),
            edge("choice", "judge", "review"),
            edge("fork", "rewrite", "rewrite"),
            edge("fork", "fetch", "fetch"),
            edge("rewrite", "join"),
            edge("fetch", "join"),
            edge("join", "wait"),
            edge("judge", "human"),
            edge("human", "wait"),
            edge("wait", "finish"),
        ],
    }


def test_all_primitives_round_trip_and_runtime_gate_are_separate():
    graph = WorkflowGraph.model_validate(all_primitives())
    assert {node.type for node in graph.nodes} == STEP_TYPES
    assert WorkflowGraph.model_validate_json(graph.model_dump_json()) == graph
    assert WorkflowGraph.model_validate(graph.model_dump(mode="json")) == graph
    with pytest.raises(ValidationError, match="Executor is not available"):
        ensure_executable(graph)
    with pytest.raises(ValidationError, match="Executor is not available: parallel"):
        ensure_executable(graph, {"code", "condition", "transform"})
    # This is only a registry contract assertion, not a claim that these executors exist.
    ensure_executable(graph, STEP_TYPES)


@pytest.mark.parametrize("score", [0.1, 0.9])
def test_both_condition_routes_have_typed_input_and_default(score):
    graph = WorkflowGraph.model_validate(all_primitives())
    validate_data({"score": score, "text": "fixture"}, graph.input_schema)
    choice = graph.nodes[1]
    assert {edge.label for edge in graph.edges if edge.source == choice.id} == {"good", "review"}
    assert choice.config.default == "review"


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda g: g["nodes"].append(deepcopy(g["nodes"][0])), "unique"),
        (lambda g: g.update(entry_node="missing"), "Entry node"),
        (lambda g: g["nodes"].append(code("orphan")), "Unreachable"),
        (lambda g: g["edges"].append(edge("missing", "finish")), "missing node"),
        (lambda g: g["edges"].append(edge("finish", "choice")), "cycles"),
        (lambda g: g["edges"].append(deepcopy(g["edges"][0])), "Duplicate edge"),
        (lambda g: g["edges"].pop(2), "Unreachable|default"),
        (lambda g: g["nodes"][1]["config"].update(default="good"), "default"),
        (lambda g: g["nodes"][8].pop("merge"), "explicit exclusive merge"),
        (
            lambda g: g["nodes"][2]["config"].update(join_node="finish"),
            "matching all-selected join",
        ),
        (lambda g: g["edges"].append(edge("fetch", "rewrite")), "overlap|outside its region"),
        (lambda g: g["nodes"][5]["config"].update(fork_node="start"), "matching all-selected join"),
        (lambda g: g["nodes"][0].update(type="python"), "union_tag_invalid"),
        (lambda g: g["nodes"][0]["config"].update(source="import os"), "extra_forbidden"),
        (lambda g: g["nodes"][0].update(retry={"max_attempts": 100}), "less_than_equal"),
        (lambda g: g["nodes"][0].update(timeout_seconds=0), "greater_than"),
        (lambda g: g.update(schema_version=2), "literal_error"),
    ],
)
def test_malformed_graphs_are_rejected_with_field_locations(mutation, message):
    payload = all_primitives()
    mutation(payload)
    with pytest.raises(ValidationError, match=message) as error:
        WorkflowGraph.model_validate(payload)
    assert error.value.errors()[0]["loc"]


@pytest.mark.parametrize(
    "expression, message",
    [
        ({"op": "eval", "value": "open('/private')"}, "literal_error"),
        (ref("score", "missing"), "Unknown producer"),
        (ref("text", "finish"), "Producer must precede"),
        (ref("undeclared"), "Undeclared field"),
        ({"op": "add", "args": [literal("wrong"), literal(2)]}, "non-null numbers"),
        ({"op": "and", "args": [literal(1), literal(True)]}, "boolean operands"),
        ({"op": "not", "args": []}, "exactly 1"),
        (literal("wrong type"), "received string"),
    ],
)
def test_unsafe_or_incompatible_expressions_fail_at_the_binding(expression, message):
    payload = all_primitives()
    payload["nodes"][0]["inputs"]["score"] = expression
    with pytest.raises(ValidationError, match=message):
        WorkflowGraph.model_validate(payload)


def test_missing_and_null_are_distinct_and_default_is_typed():
    payload = all_primitives()
    payload["input_schema"]["required"] = ["text"]
    graph = WorkflowGraph.model_validate(payload)
    validate_data({"text": "missing score is permitted by input schema"}, graph.input_schema)
    # A missing required runtime reference errors unless its policy says null/default.
    assert graph.nodes[0].inputs["score"].ref.on_missing == "error"
    payload["nodes"][0]["inputs"]["score"] = ref("score", on_missing="default", default=0)
    WorkflowGraph.model_validate(payload)
    payload["nodes"][0]["inputs"]["score"]["ref"]["default"] = "invalid"
    with pytest.raises(ValidationError, match="received string"):
        WorkflowGraph.model_validate(payload)
    payload["nodes"][0]["inputs"]["score"] = ref("score", on_missing="null")
    with pytest.raises(ValidationError, match="incompatible"):
        WorkflowGraph.model_validate(payload)
    payload["nodes"][0]["input_schema"]["properties"]["score"] = {"type": ["number", "null"]}
    WorkflowGraph.model_validate(payload)
    with pytest.raises(ValidationError, match="received null"):
        validate_data({"score": None, "text": "fixture"}, graph.input_schema)


def test_data_schemas_reject_coercion_extra_properties_and_invalid_shape():
    for value in [True, "1", None, float("inf")]:
        with pytest.raises(ValidationError):
            validate_data(value, DataSchema(type="number"))
    with pytest.raises(ValidationError, match="undeclared"):
        validate_data({"extra": 1}, DataSchema(type="object"))
    for schema in [
        {"type": ["number", "string"]},
        {"type": "array"},
        {"type": "object", "required": ["missing"]},
        {"type": "object", "additionalProperties": True},
    ]:
        with pytest.raises(ValidationError):
            DataSchema.model_validate(schema)


def test_bounded_revision_policy_is_metadata_and_never_allows_a_cycle():
    payload = all_primitives()
    payload["quality_revision"] = {
        "entry_node": "judge",
        "review_node": "human",
        "nodes": ["judge", "human"],
        "max_revisions": 2,
    }
    graph = WorkflowGraph.model_validate(payload)
    with pytest.raises(ValidationError, match="Quality revision execution"):
        ensure_executable(graph, STEP_TYPES)
    payload["edges"].append(edge("human", "judge"))
    with pytest.raises(ValidationError, match="cycles"):
        WorkflowGraph.model_validate(payload)


def test_payload_and_expression_bounds():
    payload = all_primitives()
    payload["nodes"][0]["inputs"]["score"] = literal("x" * 262144)
    with pytest.raises(ValidationError, match="256 KiB"):
        WorkflowGraph.model_validate(payload)
    payload = all_primitives()
    expr = literal(1)
    for _ in range(10):
        expr = {"op": "add", "args": [expr, literal(1)]}
    payload["nodes"][0]["inputs"]["score"] = expr
    with pytest.raises(ValidationError, match="eight operations"):
        WorkflowGraph.model_validate(payload)


def test_array_paths_coalesce_and_closed_schema_serialization():
    payload = {
        "entry_node": "start",
        "input_schema": obj(values={"type": "array", "items": STRING}),
        "output_schema": obj(first=STRING),
        "nodes": [code("start")],
        "outputs": {
            "first": {
                "op": "coalesce",
                "args": [
                    {
                        "op": "ref",
                        "ref": {"source": "input", "path": ["values", 0], "on_missing": "null"},
                    },
                    literal("empty"),
                ],
            },
        },
    }
    graph = WorkflowGraph.model_validate(payload)
    assert graph.model_dump(mode="json")["input_schema"]["additionalProperties"] is False
    assert WorkflowGraph.model_validate_json(graph.model_dump_json()) == graph
    payload["outputs"]["first"]["args"][0]["ref"]["path"][1] = True
    with pytest.raises(ValidationError):
        WorkflowGraph.model_validate(payload)


def test_parallel_region_cannot_end_early_or_accept_external_edges():
    payload = all_primitives()
    payload["edges"] = [item for item in payload["edges"] if item["source"] != "fetch"]
    with pytest.raises(ValidationError, match="terminates before"):
        WorkflowGraph.model_validate(payload)
    payload = all_primitives()
    payload["edges"].append(edge("human", "join"))
    with pytest.raises(ValidationError, match="outside its declared branches"):
        WorkflowGraph.model_validate(payload)


def test_duplicate_conditional_route_to_same_target_is_an_explicit_exclusive_merge():
    payload = {
        "entry_node": "choice",
        "nodes": [
            {
                "id": "choice",
                "type": "condition",
                "config": {"cases": [{"label": "yes", "when": literal(True)}]},
            },
            code("end", merge="exclusive"),
        ],
        "edges": [edge("choice", "end", "yes"), edge("choice", "end", "default")],
    }
    WorkflowGraph.model_validate(payload)


def test_deep_payload_is_rejected_before_json_serialization_recurses():
    payload = all_primitives()
    value = 0
    for _ in range(1500):
        value = [value]
    payload["nodes"][0]["inputs"]["score"] = literal(value)
    with pytest.raises(ValidationError, match="32 levels"):
        WorkflowGraph.model_validate(payload)


def test_revision_region_cannot_omit_intermediate_nodes():
    payload = {
        "entry_node": "start",
        "nodes": [code("start"), code("middle"), code("review")],
        "edges": [edge("start", "middle"), edge("middle", "review")],
        "quality_revision": {
            "entry_node": "start", "review_node": "review",
            "nodes": ["start", "review"], "max_revisions": 1,
        },
    }
    with pytest.raises(ValidationError, match="entry-to-review subgraph"):
        WorkflowGraph.model_validate(payload)
    payload["quality_revision"]["nodes"].append("middle")
    WorkflowGraph.model_validate(payload)


def test_parallel_join_discards_internal_route_choices_before_later_merge():
    def choice(name):
        return {
            "id": name, "type": "condition",
            "config": {"cases": [{"label": "yes", "when": literal(True)}]},
        }

    payload = {
        "entry_node": "fork",
        "nodes": [
            {"id": "fork", "type": "parallel", "config": {
                "mode": "fork", "join_node": "join", "branches": [
                    {"name": "left", "entry_node": "choice"},
                    {"name": "right", "entry_node": "other"},
                ],
            }},
            choice("choice"), code("yes"), code("no"), code("other"),
            {"id": "join", "type": "parallel",
             "config": {"mode": "join", "fork_node": "fork"}},
            choice("later"), code("end", merge="exclusive"),
        ],
        "edges": [
            edge("fork", "choice", "left"), edge("fork", "other", "right"),
            edge("choice", "yes", "yes"), edge("choice", "no", "default"),
            edge("yes", "join"), edge("no", "join"), edge("other", "join"),
            edge("join", "later"), edge("later", "end", "yes"),
            edge("later", "end", "default"),
        ],
    }
    WorkflowGraph.model_validate(payload)
