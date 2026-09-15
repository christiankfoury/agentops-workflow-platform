import json

import httpx
import pytest
from fastapi import HTTPException
from openai import RateLimitError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agent_type import AgentType
from src.models.execution_approval import ExecutionApproval
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.services.execution_registry import DEFAULT_REGISTRY
from src.worker import run_worker
from tests.test_execution_approvals import PAYLOAD, REVIEW, decision
from tests.test_graph_interpreter import start
from tests.test_llm_execution import Provider, prompt
from tests.test_workflow_graph import code, edge, literal, obj, ref
from tests.test_workflow_transactions_postgres import database as database


def whole(node):
    return {"op": "ref", "ref": {"source": "node", "node_id": node, "path": []}}


def graph(db, *, conditional=False, max_revisions=1):
    analyst, reviewer, writer = (
        prompt(db, agent_type)
        for agent_type in [AgentType.analyst, AgentType.reviewer, AgentType.writer]
    )

    def llm(key, prompt_id, output, inputs):
        return {
            "id": key,
            "type": "llm",
            "config": {"prompt_version_id": str(prompt_id), "model": "gpt-4.1-mini"},
            "input_schema": PAYLOAD,
            "output_schema": output,
            "inputs": inputs,
        }

    payload = {
        "entry_node": "prefix",
        "output_schema": PAYLOAD,
        "outputs": {"value": ref("value", "writer")},
        "quality_revision": {
            "entry_node": "analysis",
            "review_node": "review",
            "nodes": ["analysis", "review"],
            "max_revisions": max_revisions,
            "approval_node": "gate",
        },
        "nodes": [
            code(
                "prefix", input_schema=PAYLOAD, output_schema=PAYLOAD, inputs={"value": literal(2)}
            ),
            llm("analysis", analyst, PAYLOAD, {"value": ref("value", "prefix")}),
            llm("review", reviewer, REVIEW, {"value": ref("value", "analysis")}),
            {
                "id": "gate",
                "type": "approval",
                "config": {"max_review_retries": 2},
                "input_schema": obj(payload=PAYLOAD, review=REVIEW),
                "output_schema": PAYLOAD,
                "inputs": {"payload": whole("analysis"), "review": whole("review")},
            },
            llm("writer", writer, PAYLOAD, {"value": ref("value", "gate")}),
        ],
        "edges": [
            edge("prefix", "analysis"),
            edge("analysis", "review"),
            edge("review", "gate"),
            edge("gate", "writer"),
        ],
    }
    if conditional:
        payload["nodes"].append(
            {
                "id": "route",
                "type": "condition",
                "config": {
                    "cases": [{"label": "approved", "when": ref("approved", "review")}],
                    "default": "human",
                },
            }
        )
        payload["nodes"][4]["merge"] = "exclusive"
        payload["nodes"][4]["inputs"]["value"] = {
            "op": "coalesce",
            "args": [ref("value", "gate", on_missing="null"), ref("value", "analysis")],
        }
        payload["edges"][2] = edge("review", "route")
        payload["edges"] += [edge("route", "gate", "human"), edge("route", "writer", "approved")]
    return payload


def review(*, approved=False, retry=True, score=0.4):
    return {"approved": approved, "quality_score": score, "issues": [], "retry_recommended": retry}


def run_fixture(database, monkeypatch, outputs, **kwargs):
    with Session(database) as db:
        identity = start(db, graph(db, **kwargs), {}).id
    provider = Provider(outputs)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    return identity, provider


def pending(database):
    with Session(database) as db:
        item = db.scalar(select(ExecutionApproval).where(ExecutionApproval.status == "pending"))
        return item.id, item.payload_hash


def test_quality_retry_revisits_region_and_rereviews_without_repeating_prefix(
    database, monkeypatch
):
    identity, provider = run_fixture(
        database,
        monkeypatch,
        [{"value": 2}, review(), {"value": 3}, review(approved=True, score=0.95), {"value": 3}],
        conditional=True,
    )
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == "completed" and run.output_json == {"value": 3}
        assert run.checkpoint_json["quality"]["iteration"] == 1
        rows = db.scalars(select(StepRun)).all()
        assert len([row for row in rows if row.node_id == "prefix"]) == 1
        for key in ["analysis", "review"]:
            assert {row.iteration for row in rows if row.node_id == key} == {0, 1}
        assert all(attempt.number == 1 for attempt in db.scalars(select(StepAttempt)))
    assert (
        json.loads(provider.calls[2]["messages"][0]["content"])["revision_context"]["review"]
        == review()
    )


def test_exhaustion_forces_human_gate_and_writer_uses_human_edit(database, monkeypatch):
    identity, provider = run_fixture(
        database,
        monkeypatch,
        [{"value": 2}, review(approved=True), {"value": 3}, review(approved=True)],
        conditional=True,
    )
    item_id, digest = pending(database)
    with pytest.raises(HTTPException, match="Quality revision limit"):
        decision(database, item_id, digest, "request_retry")
    edited = decision(database, item_id, digest, "edit", edited_payload={"value": 99})
    with pytest.raises(HTTPException):
        decision(database, item_id, digest)
    with Session(database) as db:
        item = db.get(ExecutionApproval, edited["replacement_id"])
        new_id, digest = item.id, item.payload_hash
    decision(database, new_id, digest)
    provider.outputs.append({"value": 99})
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert json.loads(provider.calls[-1]["messages"][0]["content"])["input"] == {"value": 99}
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"value": 99}


def test_human_retry_preserves_feedback_and_replaces_approval_iteration(database, monkeypatch):
    identity, provider = run_fixture(
        database, monkeypatch, [{"value": 2}, review(retry=False)], max_revisions=2
    )
    item_id, digest = pending(database)
    decision(database, item_id, digest, "request_retry", human_feedback="Check the source again")
    with pytest.raises(HTTPException):
        decision(database, item_id, digest)
    provider.outputs += [{"value": 4}, review(retry=False)]
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    context = json.loads(provider.calls[2]["messages"][0]["content"])["revision_context"]
    assert context["human_feedback"] == "Check the source again"
    assert context["edited_payload"] == {"value": 2}
    with Session(database) as db:
        item = db.scalar(select(ExecutionApproval).where(ExecutionApproval.status == "pending"))
        assert item.id != item_id and item.iteration == 1
        assert db.get(WorkflowExecution, identity).status == "waiting"


@pytest.mark.parametrize("waiting_sibling", [False, True])
def test_quality_revision_inside_parallel_region_retains_independent_sibling(
    database, monkeypatch, waiting_sibling
):
    with Session(database) as db:
        payload = graph(db, conditional=True)
        payload["entry_node"] = "fork"
        payload["nodes"] += [
            {
                "id": "fork",
                "type": "parallel",
                "config": {
                    "mode": "fork",
                    "join_node": "join",
                    "branches": [
                        {"name": "quality", "entry_node": "prefix"},
                        {"name": "sibling", "entry_node": "sibling"},
                    ],
                },
            },
            code(
                "sibling", input_schema=PAYLOAD, output_schema=PAYLOAD, inputs={"value": literal(7)}
            ),
            {"id": "join", "type": "parallel", "config": {"mode": "join", "fork_node": "fork"}},
        ]
        payload["edges"] += [
            edge("fork", "prefix", "quality"),
            edge("fork", "sibling", "sibling"),
            edge("writer", "join"),
            edge("sibling", "join"),
        ]
        if waiting_sibling:
            payload["nodes"][-2] = {"id": "sibling", "type": "delay", "config": {"seconds": 3600}}
        identity = start(db, payload, {}).id
    provider = Provider(
        [{"value": 2}, review(), {"value": 3}, review(approved=True, score=0.95), {"value": 3}]
    )
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    if waiting_sibling:
        from src.services.delay_runtime import wake_due_delays

        with Session(database) as db:
            assert db.get(WorkflowExecution, identity).status == "waiting"
            due = db.scalar(select(StepRun).where(StepRun.node_id == "sibling")).wake_at
        assert wake_due_delays(database, now=due) == 1
        assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"value": 3}
        siblings = db.scalars(select(StepRun).where(StepRun.node_id == "sibling")).all()
        assert len(siblings) == 1 and siblings[0].output_json == (
            {} if waiting_sibling else {"value": 7}
        )
        assert siblings[0].iteration == 0
        assert db.scalar(select(StepRun).where(StepRun.node_id == "join")).iteration == 1


def test_infrastructure_attempts_and_quality_iterations_have_separate_budgets(
    database, monkeypatch
):
    with Session(database) as db:
        payload = graph(db, conditional=True)
        payload["nodes"][1]["retry"] = {
            "max_attempts": 2,
            "initial_delay_seconds": 0,
            "retryable_errors": ["provider_rate_limit"],
        }
        identity = start(db, payload, {}).id
    request = httpx.Request("POST", "https://example.invalid")
    error = RateLimitError("fixture", response=httpx.Response(429, request=request), body=None)
    provider = Provider(
        [
            error,
            {"value": 2},
            review(),
            {"value": 3},
            review(approved=True, score=0.95),
            {"value": 3},
        ]
    )
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"value": 3}
        rows = db.scalars(
            select(StepRun).where(StepRun.node_id == "analysis").order_by(StepRun.iteration)
        ).all()
        attempts = [
            db.scalars(
                select(StepAttempt)
                .where(StepAttempt.step_run_id == row.id)
                .order_by(StepAttempt.number)
            ).all()
            for row in rows
        ]
        assert [[item.number for item in items] for items in attempts] == [[1, 2], [1]]
        assert attempts[0][0].idempotency_key == attempts[0][1].idempotency_key
        assert attempts[0][0].idempotency_key != attempts[1][0].idempotency_key
        assert attempts[0][0].llm_metadata["usage_complete"] is False


def test_reviewer_semantic_schema_failure_uses_bounded_repair(database, monkeypatch):
    identity, provider = run_fixture(
        database,
        monkeypatch,
        [
            {"value": 2},
            review(approved=True, score=1.5),
            review(approved=True, score=0.95),
            {"value": 2},
        ],
        conditional=True,
    )
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"
        step = db.scalar(select(StepRun).where(StepRun.node_id == "review"))
        attempt = db.scalar(select(StepAttempt).where(StepAttempt.step_run_id == step.id))
        assert attempt.llm_metadata["schema_repairs"] == 1
        assert attempt.llm_metadata["total_tokens"] == 30
    assert "schema validation" in provider.calls[2]["messages"][-1]["content"]


def test_quality_policy_rejects_impossible_issue_schema_before_provider_io(database):
    from copy import deepcopy

    from pydantic import ValidationError

    from src.schemas.workflow_graph import WorkflowGraph

    with Session(database) as db:
        payload = graph(db)
    malformed = deepcopy(REVIEW)
    malformed["properties"]["issues"]["items"] = {"type": "string"}
    payload["nodes"][2]["output_schema"] = malformed
    payload["nodes"][3]["input_schema"]["properties"]["review"] = malformed
    with pytest.raises(ValidationError, match="issues require"):
        DEFAULT_REGISTRY.validate(WorkflowGraph.model_validate(payload))
