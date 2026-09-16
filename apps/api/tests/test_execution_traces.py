import tracemalloc
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep
from src.models.execution_approval import ExecutionApproval
from src.models.tool import ToolDefinition, ToolExecution, ToolVersion
from src.models.workflow_definition import WorkflowDefinition, WorkflowVersion
from src.models.workflow_execution import WorkflowExecution
from src.schemas.workflow_graph import WorkflowGraph
from src.services import execution_traces as traces
from src.services.execution_records import add_attempt, add_step
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import workflow_transaction
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_graph import all_primitives
from tests.test_workflow_transactions_postgres import database as database


def fixture_trace(database, owner):
    actor = prepare(database, owner)
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        db.info["principal"] = Principal("admin", actor, owner["org"])
        graph = WorkflowGraph.model_validate(all_primitives()).model_dump(mode="json")
        definition = WorkflowDefinition(name="Trace fixture", draft_graph={})
        db.add(definition)
        db.flush()
        # Explicit historical persistence fixture; no tool or provider is dispatched.
        version = WorkflowVersion(
            definition_id=definition.id,
            number=1,
            source_revision=1,
            name="Pinned trace",
            description="",
            graph=graph,
            graph_hash="0" * 64,
        )
        db.add(version)
        db.flush()
        run = WorkflowExecution(version_id=version.id, input_json={"password": "hidden-run"})
        db.add(run)
        db.commit()
        transition(db, run, run, "running")
        ids = {}
        tool_attempt = None
        for node in graph["nodes"]:
            step = add_step(db, run, node["id"], inputs={"node": node["id"], "secret": "hidden"})
            ids[node["id"]] = step.id
            if node["type"] == "tool":
                tool_attempt = add_attempt(db, run, step)
            transition(db, run, step, "running")
            if node["type"] == "tool":
                transition(db, run, tool_attempt, "running")
            with workflow_transaction(db, run):
                step.output_json = {"node": node["id"]}
                if node["type"] == "tool":
                    transition(db, run, tool_attempt, "completed")
                if node["type"] in {"delay", "approval"}:
                    step.waiting_reason = node["type"]
                    transition(db, run, step, "waiting")
                else:
                    transition(
                        db, run, step, "cancelled" if node["id"] == "finish" else "completed"
                    )
        second = add_step(db, run, "start", branch="other", iteration=1, inputs={"value": "second"})
        attempt = add_attempt(db, run, second)
        transition(db, run, second, "running")
        transition(db, run, attempt, "running")
        with workflow_transaction(db, run):
            attempt.llm_metadata = {
                "model": "fixture",
                "total_tokens": 12,
                "estimated_cost_usd": 0.01,
                "usage_complete": True,
            }
            attempt.output_json = {"large": "x" * 70000, "api_key": "hidden-attempt"}
            transition(db, run, attempt, "failed")
            transition(db, run, second, "failed")
            run.checkpoint_json = {
                "edges": {"0": "selected", "1": "skipped"},
                "quality": {"iteration": 1, "status": "revising"},
            }
            approval = ExecutionApproval(
                execution_id=run.id,
                step_run_id=ids["human"],
                version_id=version.id,
                node_id="human",
                iteration=0,
                revision=1,
                source_hash="1" * 64,
                payload_hash="2" * 64,
                payload_json={"token": "hidden-approval"},
                review_json={"approved": True},
            )
            db.add(approval)
        definition.draft_graph = {"changed": True}
        definition.name = "New draft"
        tool = ToolDefinition(name="Fixture tool")
        db.add(tool)
        db.flush()
        tool_version = ToolVersion(definition_id=tool.id, number=1, contract={"adapter": "fixture"})
        db.add(tool_version)
        db.flush()
        effect = ToolExecution(
            version_id=tool_version.id,
            step_run_id=ids["fetch"],
            attempt_id=tool_attempt.id,
            call_id="fixture-call",
            effect_key=uuid.uuid4().hex,
            request_fingerprint="3" * 64,
            request_json={"authorization": "hidden-tool"},
            claim_token=uuid.uuid4(),
            credential_digest="hidden-digest",
        )
        db.add(effect)
        db.commit()
        return {
            "run": str(run.id),
            "step": str(second.id),
            "attempt": str(attempt.id),
            "approval": str(approval.id),
            "version": str(version.id),
            "tool": str(effect.id),
            "ids": ids,
        }


def test_trace_pins_graph_and_pages_logical_steps(database, tenants, tenant_client):
    item = fixture_trace(database, tenants[0])
    base = f"/execution-traces/{item['run']}"
    head = tenant_client.get(base).json()
    assert head["version"]["name"] == "Pinned trace" and head["version"]["id"] == item["version"]
    assert {node["type"] for node in head["graph"]["nodes"]} == {
        "code",
        "condition",
        "parallel",
        "transform",
        "tool",
        "llm",
        "approval",
        "delay",
    }
    assert [edge["state"] for edge in head["graph"]["edges"][:2]] == ["selected", "skipped"]
    latest = next(row for row in head["latest_steps"] if row["node_id"] == "start")
    assert latest["id"] == item["step"] and latest["iteration"] == 1 and latest["branch"] == "other"
    first = tenant_client.get(base + "/records/steps?limit=2").json()
    second = tenant_client.get(base + "/records/steps?limit=2&offset=2").json()
    assert first["next_offset"] == 2
    assert not {row["id"] for row in first["items"]} & {row["id"] for row in second["items"]}
    assert "input_json" not in str(first) and "hidden-run" not in str(head)
    assert tenant_client.get(base + "/records/steps?limit=51").status_code == 422
    assert tenant_client.get(base + "/records/steps?offset=-1").status_code == 422
    assert tenant_client.get(base + "/records/attempts").status_code == 422
    assert tenant_client.get(base + "/records/tools").json()["items"][0]["id"] == item["tool"]
    detail = tenant_client.get(base + f"/records/steps/{item['step']}").json()
    assert '"second"' in detail["payloads"]["input_json"]["text"]
    attempts = tenant_client.get(base + f"/records/attempts?step_id={item['step']}").json()
    assert attempts["items"][0]["id"] == item["attempt"]


def test_trace_details_redact_and_bound_attempt_and_approval(database, tenants, tenant_client):
    item = fixture_trace(database, tenants[0])
    base = f"/execution-traces/{item['run']}"
    detail = tenant_client.get(base + f"/records/attempts/{item['attempt']}?step_id={item['step']}")
    assert detail.status_code == 200
    payload = detail.json()["payloads"]
    assert payload["output_json"]["truncated"] and len(payload["output_json"]["text"]) == 64000
    assert (
        "hidden-attempt" not in detail.text and '"total_tokens": 12' in payload["llm_usage"]["text"]
    )
    assert detail.json()["usage"]["total_tokens"] == 12
    tool = tenant_client.get(base + f"/records/tools/{item['tool']}")
    assert tool.status_code == 200 and "REDACTED" in tool.text
    assert "hidden-tool" not in tool.text and "hidden-digest" not in tool.text
    assert "claim_token" not in tool.text and "credential_digest" not in tool.text
    approval = tenant_client.get(base + f"/records/approvals/{item['approval']}")
    assert "hidden-approval" not in approval.text and "REDACTED" in approval.text
    run = tenant_client.get(base + "/payloads")
    assert "hidden-run" not in run.text and "REDACTED" in run.text
    events = tenant_client.get(base + "/records/events?limit=1").json()
    assert events["next_offset"] == 1
    event = tenant_client.get(base + f"/records/events/{events['items'][0]['id']}")
    assert event.status_code == 200 and "details" in event.json()["payloads"]


def test_trace_scope_applies_to_every_reader(database, tenants, tenant_client):
    own, other = [fixture_trace(database, owner) for owner in tenants]
    client = tenant_client
    assert len(client.get("/execution-traces").json()["items"]) == 1
    for suffix in [
        "",
        "/payloads",
        "/records/steps",
        "/records/events",
        "/records/tools",
        "/records/approvals",
        f"/records/attempts?step_id={other['step']}",
    ]:
        assert client.get(f"/execution-traces/{other['run']}" + suffix).status_code == 404
    for kind, key in [("steps", "step"), ("attempts", "attempt"), ("approvals", "approval")]:
        url = f"/execution-traces/{own['run']}/records/{kind}/{other[key]}?step_id={own['step']}"
        assert client.get(url).status_code == 404
    assert (
        client.get(f"/execution-traces/{own['run']}/records/steps/{uuid.uuid4()}").status_code
        == 404
    )
    client.headers.pop("authorization")
    assert client.get(f"/execution-traces/{own['run']}").status_code == 401


def test_historical_trace_preserves_labels_and_avoids_projected_usage(
    database, tenants, tenant_client
):
    identity = tenants[0]["run"]
    base = f"/execution-traces/legacy/{identity}"
    head = tenant_client.get(base).json()
    assert head["source"] == "legacy" and head["run"]["workflow_type"] == "sales_report"
    rows = tenant_client.get(base + "/steps?limit=1").json()
    assert rows["items"][0]["model"] == "fixture"
    detail = tenant_client.get(base + f"/steps/{rows['items'][0]['id']}")
    assert detail.status_code == 200
    assert (
        tenant_client.get(f"/execution-traces/legacy/{tenants[1]['run']}/steps").status_code == 404
    )
    item = fixture_trace(database, tenants[0])
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        original = db.get(WorkflowExecution, uuid.UUID(item["run"]))
        canonical = WorkflowExecution(version_id=original.version_id, legacy_run_id=identity)
        db.add(canonical)
        db.commit()
        canonical_id = str(canonical.id)
        assert db.scalar(select(AgentStep.id).where(AgentStep.workflow_run_id == identity))
    assert tenant_client.get(base).json() == {"source": "generic", "execution_id": canonical_id}
    assert tenant_client.get(base + "/steps").status_code == 409


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {"Authorization": "hidden", "nested": [{"api-key": "hidden"}]},
        {"url": "https://user:pass@example.com/path"},
        [0] * 20000,
    ],
)
def test_preview_is_bounded_and_redacts_known_fields(value):
    result = traces.preview(value, 80)
    assert len(result["text"]) <= 80
    assert "hidden" not in result["text"] and "user:pass" not in result["text"]


def test_large_preview_does_not_encode_the_entire_source():
    source = [{"text": "x" * 64000}] * 500
    tracemalloc.start()
    try:
        result = traces.preview(source, 64000)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert result["truncated"] and len(result["text"]) == 64000
    assert peak < 2_000_000  # A 32 MB source must not be copied into a full JSON string.
