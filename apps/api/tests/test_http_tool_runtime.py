import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models.execution_approval import ExecutionApproval
from src.models.identity import Organization
from src.models.tenant import DEFAULT_ORGANIZATION_ID
from src.models.tool import ToolCredential, ToolExecution
from src.models.workflow_execution import StepAttempt, WorkflowExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.tool import CredentialCreate, ToolContract, ToolCreate
from src.schemas.workflow_definition import DefinitionCreate
from src.services import durable_queue as queue
from src.services import tool_catalog, tool_effects, tool_runtime, workflow_definitions
from src.services.execution_cancellation import cancel_execution
from src.services.execution_starts import start_execution
from src.services.tenancy import bind_tenant
from src.services.worker_leases import recover_claim
from src.services.workflow_transactions import StaleWorkflowError
from src.worker import run_worker
from tests.test_execution_approvals import REVIEW, decision
from tests.test_http_tool import policy
from tests.test_http_tool import server as server
from tests.test_worker_leases import expire
from tests.test_workflow_graph import STRING, edge, literal, obj, ref
from tests.test_workflow_transactions_postgres import database as database

INPUT = obj(value=STRING)
OUTPUT = obj(status={"type": "integer"}, body=INPUT)
ENVELOPE = obj(node_id=STRING, tool_id=STRING, version={"type": "integer"}, arguments=INPUT)
RETRY = {
    "max_attempts": 3,
    "initial_delay_seconds": 0,
    "retryable_errors": ["tool_unavailable", "tool_timeout", "tool_rate_limit"],
}


def fixture(
    database,
    server,
    monkeypatch,
    *,
    write=False,
    path="/ok",
    idempotent=False,
    credential=False,
    changed=False,
    govern=True,
    side_effecting=None,
    start=True,
    timeout_seconds=30,
):
    raw = policy(
        server,
        methods={"GET", "POST"},
        credential_alias="fixture" if credential else None,
        idempotency_retention_seconds=120 if idempotent else 0,
    ).model_dump(mode="json")
    monkeypatch.setattr(
        settings, "http_tool_destinations", {f"{DEFAULT_ORGANIZATION_ID}/fixture": raw}
    )
    monkeypatch.setattr(settings, "worker_control_poll_seconds", 0.02)
    monkeypatch.setattr(
        settings,
        "tool_credential_values",
        {
            f"{DEFAULT_ORGANIZATION_ID}/fixture": SecretStr("worker-secret-fixture"),
        },
    )
    with Session(database) as db:
        credential_id = (
            tool_catalog.create_credential(
                db,
                CredentialCreate(
                    name="HTTP fixture",
                    source_alias="fixture",
                ),
            ).id
            if credential
            else None
        )
        version = tool_catalog.create(
            db,
            ToolCreate(
                name="HTTP fixture",
                contract=ToolContract(
                    adapter="http",
                    input_schema=INPUT,
                    output_schema=OUTPUT,
                    credential_ref=credential_id,
                    side_effecting=write if side_effecting is None else side_effecting,
                    timeout_seconds=timeout_seconds,
                    options={
                        "destination": "fixture",
                        "method": "POST" if write else "GET",
                        "path": path,
                    },
                    retry=RETRY,
                ),
            ),
        )
        payload = {
            "node_id": "action",
            "tool_id": str(version.definition_id),
            "version": 1,
            "arguments": {"value": "one"},
        }
        node = {
            "id": "action",
            "type": "tool",
            "input_schema": INPUT,
            "output_schema": OUTPUT,
            "inputs": {"value": literal("different" if changed else "one")},
            "retry": RETRY,
            "config": {"tool_id": str(version.definition_id), "version": 1},
        }
        graph = {"entry_node": "action", "nodes": [node]}
        if write and govern:
            node["config"]["approval_node"] = "gate"
            if not changed:
                binding = ref("arguments", "gate")
                binding["ref"]["path"].append("value")
                node["inputs"]["value"] = binding
            graph["entry_node"] = "gate"
            graph["nodes"].insert(
                0,
                {
                    "id": "gate",
                    "type": "approval",
                    "config": {"deadline_seconds": 300},
                    "input_schema": obj(payload=ENVELOPE, review=REVIEW),
                    "output_schema": ENVELOPE,
                    "inputs": {
                        "payload": literal(payload),
                        "review": literal(
                            {
                                "approved": True,
                                "quality_score": 1,
                                "issues": [],
                                "retry_recommended": False,
                            }
                        ),
                    },
                },
            )
            graph["edges"] = [edge("gate", "action")]
        definition = workflow_definitions.create_definition(
            db, DefinitionCreate(name="HTTP graph", graph=graph)
        )
        workflow_definitions.publish(db, definition.id, 1)
        run_id = (
            start_execution(
                db,
                ExecutionStartRequest(
                    definition_id=definition.id, input={}, idempotency_key="http-fixture"
                ),
            ).id
            if start
            else None
        )
        return run_id, version.id, credential_id, graph, definition.id


def approve(database):
    assert queue.process_claim(database, queue.claim_jobs(database, "approval")[0])
    with Session(database) as db:
        gate = db.scalar(select(ExecutionApproval).where(ExecutionApproval.status == "pending"))
        identity, payload_hash = gate.id, gate.payload_hash
    decision(database, identity, payload_hash)


def snapshot(database, run_id):
    with Session(database) as db:
        run = db.get(WorkflowExecution, run_id)
        effect = db.scalar(select(ToolExecution))
        return run.status, effect.status if effect else None, effect.result_json if effect else None


def test_real_worker_read_credentials_and_redacted_receipt(database, server, monkeypatch):
    run_id, *_ = fixture(database, server, monkeypatch, credential=True, path="/echo")
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    status, effect, result = snapshot(database, run_id)
    assert (status, effect) == ("completed", "succeeded")
    assert result == {"status": 200, "body": {"value": "Bearer [REDACTED]"}}
    assert server.calls[0][2]["Authorization"] == "Bearer worker-secret-fixture"
    with Session(database) as db:
        assert "worker-secret-fixture" not in json.dumps(
            [
                tool_catalog.public(db.scalar(select(ToolExecution))),
                db.scalar(select(StepAttempt)).output_json,
            ],
            default=str,
        )


def test_governed_write_waits_for_human_and_dispatches_once(database, server, monkeypatch):
    run_id, *_ = fixture(database, server, monkeypatch, write=True, path="/write", idempotent=True)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("waiting", None) and not server.calls
    with Session(database) as db:
        item = db.scalar(select(ExecutionApproval))
        identity, payload_hash = item.id, item.payload_hash
    decision(database, identity, payload_hash)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("completed", "succeeded")
    assert len(server.effects) == 1 and len(server.calls) == 1
    assert len(server.calls[0][2]["Idempotency-Key"]) == 64


@pytest.mark.parametrize("idempotent", [True, False])
def test_lost_write_response_recovers_only_with_provider_guarantee(
    database, server, monkeypatch, idempotent
):
    run_id, *_ = fixture(
        database, server, monkeypatch, write=True, path="/lost", idempotent=idempotent
    )
    approve(database)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == (
        ("completed", "reconciled") if idempotent else ("failed", "unknown")
    )
    assert len(server.effects) == 1 and len(server.calls) == (2 if idempotent else 1)
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        assert effect.attempts == (2 if idempotent else 1)
        if idempotent:
            assert effect.reconciliation == {"method": "adapter", "outcome": "succeeded"}


def test_worker_crash_after_remote_receipt_reuses_stable_effect(database, server, monkeypatch):
    run_id, *_ = fixture(database, server, monkeypatch, write=True, path="/write", idempotent=True)
    approve(database)
    claim = queue.claim_jobs(database, "crashed")[0]
    original = tool_effects.finish

    def crash(*args, **kwargs):
        raise SystemExit("Fixture process loss before ledger receipt commit")

    monkeypatch.setattr(tool_effects, "finish", crash)
    with pytest.raises(SystemExit):
        queue.process_claim(database, claim)
    assert len(server.effects) == 1 and snapshot(database, run_id)[1] == "pending"
    monkeypatch.setattr(tool_effects, "finish", original)
    expire(database, claim)
    assert recover_claim(database, claim)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("completed", "reconciled")
    assert len(server.effects) == 1


@pytest.mark.parametrize("changed", ["arguments", "expiry"])
def test_stale_approval_cannot_authorize_write(database, server, monkeypatch, changed):
    run_id, *_ = fixture(
        database, server, monkeypatch, write=True, path="/write", changed=changed == "arguments"
    )
    approve(database)
    if changed == "expiry":
        now = tool_runtime.runtime_now
        monkeypatch.setattr(
            tool_runtime, "runtime_now", lambda db: now(db) + timedelta(seconds=301)
        )
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("failed", None)
    assert not server.calls
    with Session(database) as db:
        assert db.get(WorkflowExecution, run_id).error_code == "tool_approval_required"


@pytest.mark.parametrize("change", ["credential", "destination"])
def test_revocation_after_acceptance_prevents_network_dispatch(
    database, server, monkeypatch, change
):
    run_id, _, credential_id, *_ = fixture(database, server, monkeypatch, credential=True)
    if change == "credential":
        with Session(database) as db:
            tool_catalog.set_active(db, ToolCredential, credential_id, False)
    else:
        monkeypatch.setattr(settings, "http_tool_destinations", {})
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("failed", None) and not server.calls


@pytest.mark.parametrize(
    "kwargs", [{"write": True, "govern": False}, {"write": True, "side_effecting": False}]
)
def test_publication_rejects_missing_approval_and_forged_effect_policy(
    database, server, monkeypatch, kwargs
):
    with pytest.raises(HTTPException) as error:
        fixture(database, server, monkeypatch, **kwargs)
    assert error.value.status_code == 422 and not server.calls


def test_cross_tenant_catalog_reference_cannot_publish(database, server, monkeypatch):
    _, _, _, graph, _ = fixture(database, server, monkeypatch, start=False)
    with Session(database) as db:
        organization = Organization(name="Other organization")
        db.add(organization)
        db.commit()
        bind_tenant(db, organization.id)
        item = workflow_definitions.create_definition(
            db, DefinitionCreate(name="Foreign tool", graph=graph)
        )
        with pytest.raises(HTTPException) as error:
            workflow_definitions.publish(db, item.id, 1)
        assert error.value.status_code == 422


def test_changed_server_policy_cannot_replay_unknown_effect(database, server, monkeypatch):
    run_id, *_ = fixture(database, server, monkeypatch, write=True, path="/lost", idempotent=True)
    approve(database)
    assert queue.process_claim(database, queue.claim_jobs(database, "first")[0])
    assert snapshot(database, run_id)[1] == "unknown"
    settings.http_tool_destinations[f"{DEFAULT_ORGANIZATION_ID}/fixture"]["max_response_bytes"] = (
        500
    )
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("failed", "unknown")
    assert len(server.calls) == 1


def test_policy_change_after_approval_requires_republication_before_first_dispatch(
    database, server, monkeypatch
):
    run_id, *_ = fixture(database, server, monkeypatch, write=True, path="/write")
    approve(database)
    settings.http_tool_destinations[f"{DEFAULT_ORGANIZATION_ID}/fixture"]["max_response_bytes"] = (
        500
    )
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("failed", None)
    assert not server.calls


def test_cancel_during_response_preserves_cancelled_run_and_no_success(
    database, server, monkeypatch
):
    run_id, *_ = fixture(database, server, monkeypatch, path="/hold")
    claim = queue.claim_jobs(database, "cancelled")[0]
    with ThreadPoolExecutor(1) as pool:
        running = pool.submit(queue.process_claim, database, claim)
        assert server.entered.wait(5)
        with Session(database) as db:
            cancel_execution(db, run_id)
        with pytest.raises(StaleWorkflowError):
            running.result(5)
    server.release.set()
    assert snapshot(database, run_id)[:2] == ("cancelled", "failed")


def test_schema_mismatch_and_rate_limit_follow_shared_retry_policy(database, server, monkeypatch):
    run_id, *_ = fixture(database, server, monkeypatch, path="/wrong-schema")
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("failed", "failed")
    with Session(database) as db:
        assert db.get(WorkflowExecution, run_id).error_code == "tool_response_invalid"
    assert len(server.calls) == 1


def test_rate_limit_retries_are_bounded_by_engine_and_contract(database, server, monkeypatch):
    run_id, *_ = fixture(database, server, monkeypatch, path="/status/429")
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("failed", "failed")
    with Session(database) as db:
        assert db.get(WorkflowExecution, run_id).error_code == "retry_exhausted"
        assert db.scalar(select(ToolExecution)).attempts == 3
    assert len(server.calls) == 3


def test_edited_action_requires_fresh_approval_then_uses_exact_new_arguments(
    database, server, monkeypatch
):
    run_id, *_ = fixture(database, server, monkeypatch, write=True, path="/write")
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        item = db.scalar(select(ExecutionApproval))
        identity, payload_hash, payload = item.id, item.payload_hash, dict(item.payload_json)
    payload["arguments"] = {"value": "edited"}
    result = decision(database, identity, payload_hash, "edit", edited_payload=payload)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0 and not server.calls
    with Session(database) as db:
        item = db.get(ExecutionApproval, uuid.UUID(result["replacement_id"]))
        identity, payload_hash = item.id, item.payload_hash
    decision(database, identity, payload_hash)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[2]["body"] == {"value": "edited"}


def test_revoked_reviewer_cannot_authorize_future_dispatch(database, server, monkeypatch):
    from src.models.identity import Membership, User
    from src.schemas.execution_approval import ApprovalDecision
    from src.services.approval_runtime import decide_approval
    from src.services.identity import Principal

    run_id, *_ = fixture(database, server, monkeypatch, write=True, path="/write")
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        user = User(issuer="fixture", subject="reviewer", display_name="Fixture reviewer")
        db.add(user)
        db.flush()
        membership = Membership(
            user_id=user.id, organization_id=DEFAULT_ORGANIZATION_ID, role="reviewer"
        )
        db.add(membership)
        db.commit()
        db.info["principal"] = Principal("reviewer", user.id, DEFAULT_ORGANIZATION_ID)
        item = db.scalar(select(ExecutionApproval))
        decide_approval(
            db, item.id, ApprovalDecision(action="approve", expected_payload_hash=item.payload_hash)
        )
        membership.active = False
        db.commit()
    monkeypatch.setattr(settings, "identity_enabled", True)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        bind_tenant(db, DEFAULT_ORGANIZATION_ID)
        assert db.get(WorkflowExecution, run_id).error_code == "tool_approval_required"
    assert not server.calls
