from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.audit_event import AuditEvent
from src.models.execution_approval import ExecutionApproval
from src.models.execution_recovery import ExecutionRecovery
from src.models.tool import ToolExecution
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.schemas.execution_recovery import RecoveryRequest
from src.services import durable_queue as queue
from src.services.execution_cancellation import cancel_execution
from src.services.execution_recovery import controls, recover, retry_job
from src.services.execution_registry import ExecutorRegistry
from src.services.graph_expressions import ExecutionError
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from tests.test_graph_interpreter import start
from tests.test_http_tool import server as server
from tests.test_http_tool_runtime import approve
from tests.test_http_tool_runtime import fixture as http_fixture
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_worker_leases import expire
from tests.test_workflow_transactions_postgres import database as database


def drain(database, registry=None):
    for _ in range(30):
        claims = queue.claim_jobs(database, "recovery-fixture")
        if not claims:
            return
        queue.process_claim(database, claims[0], registry or ExecutorRegistry())
    pytest.fail("Fixture queue did not drain")


def failed_run(database):
    with Session(database) as db:
        identity = start(db).id
    registry = ExecutorRegistry()
    original = registry.executors["transform"]

    def fail_finish(node, *args):
        if node.id == "finish":
            raise ExecutionError("output_invalid", "Injected final-node failure")
        return original(node, *args)

    registry.executors["transform"] = fail_finish
    drain(database, registry)
    return identity


def snapshot(db, identity):
    run = db.get(WorkflowExecution, identity)
    return {
        column.name: getattr(run, column.name) for column in WorkflowExecution.__table__.columns
    }


def test_terminal_recovery_pins_source_and_reuses_outputs(database):
    identity = failed_run(database)
    with Session(database) as db:
        before = snapshot(db, identity)
        assert before["status"] == "failed" and controls(db, identity)["can_recover"]
        child = recover(db, identity, "Retry the failed final node")
        child_id = child.id
        assert child.version_id == before["version_id"]
        assert child.input_json == before["input_json"]
        assert child.runtime_config == before["runtime_config"]
        copied = db.scalars(select(StepRun).where(StepRun.execution_id == child_id)).all()
        assert {step.node_id for step in copied} == {"start", "choice", "positive", "negative"}
        assert all(step.recovered_from_id for step in copied)
        assert not db.scalars(
            select(StepAttempt).join(StepRun).where(StepRun.execution_id == child_id)
        ).all()
        assert snapshot(db, identity) == before
    drain(database)
    with Session(database) as db:
        assert db.get(WorkflowExecution, child_id).output_json == {"result": 3}
        assert db.get(WorkflowExecution, child_id).status == "completed"
        assert snapshot(db, identity) == before
        assert recover(db, identity, "A repeated operator click").id == child_id
        assert controls(db, identity)["recovery_id"] == child_id
        assert db.scalar(select(func.count()).select_from(ExecutionRecovery)) == 1


def test_concurrent_operators_create_one_child_and_audit(database):
    identity = failed_run(database)
    barrier = Barrier(2)

    def submit(_):
        with Session(database) as db:
            barrier.wait()
            return recover(db, identity, "Concurrent recovery").id

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert results[0] == results[1]
    with Session(database) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "workflow.recover")
            )
            == 1
        )
        receipt = db.scalar(select(ExecutionRecovery))
        receipt.reason = "rewrite"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()


def test_active_retry_preserves_live_claim_and_uses_recovery_budget(database, monkeypatch):
    from src.config import settings

    with Session(database) as db:
        identity = start(db).id
    claim = queue.claim_jobs(database, "stale-worker")[0]
    with Session(database) as db:
        assert not controls(db, identity)["jobs"][0]["can_retry"]
        with pytest.raises(HTTPException, match="live or changed"):
            retry_job(db, identity, claim.id)
    expire(database, claim)
    monkeypatch.setattr(settings, "worker_max_recoveries", 0)
    with Session(database) as db:
        assert controls(db, identity)["jobs"][0]["can_retry"]
        assert retry_job(db, identity, claim.id)["recovered"]
        db.expire_all()
        assert db.get(WorkflowExecution, identity).status == "failed"
        assert db.get(WorkflowExecution, identity).error_code == "recovery_exhausted"
        with pytest.raises(HTTPException):
            retry_job(db, identity, claim.id)
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "workflow.retry_claim")
            )
            == 1
        )


def test_cancelled_recovery_and_changed_input_rejected(database):
    with pytest.raises(ValidationError):
        RecoveryRequest(reason="Change input", input={"value": 9})
    with Session(database) as db:
        identity = start(db).id
        with pytest.raises(HTTPException):
            recover(db, identity, "Cannot reopen active execution")
        cancel_execution(db, identity, "Fixture cancellation")
        before = snapshot(db, identity)
        child = recover(db, identity, "Resume in a linked execution")
        assert child.id != identity and snapshot(db, identity) == before
    drain(database)


def test_successful_effect_is_not_repeated_and_approval_is_fresh(database, server, monkeypatch):
    identity, *_ = http_fixture(database, server, monkeypatch, write=True, path="/write")
    approve(database)
    queue.process_claim(database, queue.claim_jobs(database, "first-action")[0])
    with Session(database) as db:
        original_gate = db.scalar(select(ExecutionApproval))
        original_approval_id = original_gate.id
        original_effect = db.scalar(select(ToolExecution))
        effect_id, key = original_effect.id, original_effect.effect_key
        assert original_effect.status == "succeeded"
        cancel_execution(db, identity, "Cancel before final aggregation")
        child_id = recover(db, identity, "Recover completed effect").id
    drain(database)
    with Session(database) as db:
        assert db.get(WorkflowExecution, child_id).status == "waiting"
        fresh = db.scalar(
            select(ExecutionApproval).where(ExecutionApproval.execution_id == child_id)
        )
        assert fresh.status == "pending" and fresh.id != original_approval_id
        assert db.get(ExecutionApproval, original_approval_id).status == "approved"
        approval_id, payload_hash = fresh.id, fresh.payload_hash
    from tests.test_execution_approvals import decision

    decision(database, approval_id, payload_hash)
    drain(database)
    with Session(database) as db:
        assert db.get(WorkflowExecution, child_id).status == "completed"
        effect = db.scalar(select(ToolExecution))
        assert effect.id == effect_id and effect.effect_key == key and effect.attempts == 1
        assert db.scalar(select(func.count()).select_from(ToolExecution)) == 1
    assert len(server.calls) == len(server.effects) == 1


def test_unknown_effect_blocks_until_recorded_reconciliation(database, server, monkeypatch):
    from src.schemas.tool import EffectResolution
    from src.services.tool_effects import resolve
    from tests.test_execution_approvals import decision

    identity, *_ = http_fixture(database, server, monkeypatch, write=True, path="/lost")
    approve(database)
    drain(database)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "failed"
        effect = db.scalar(select(ToolExecution))
        assert effect.status == "unknown"
        assert not controls(db, identity)["can_recover"]
        with pytest.raises(HTTPException):
            recover(db, identity, "Must not replay an unknown write")
        resolve(
            db,
            effect.id,
            EffectResolution(
                succeeded=True,
                result={"status": 200, "body": {"value": "one"}},
                evidence="Verified the single entry in the disposable HTTP effect sink",
            ),
        )
        child_id = recover(db, identity, "Remote outcome verified").id
    drain(database)
    with Session(database) as db:
        gate = db.scalar(
            select(ExecutionApproval).where(ExecutionApproval.execution_id == child_id)
        )
        decision_id, payload_hash = gate.id, gate.payload_hash
    decision(database, decision_id, payload_hash)
    drain(database)
    assert len(server.calls) == len(server.effects) == 1
    with Session(database) as db:
        assert db.get(WorkflowExecution, child_id).status == "completed"


def test_control_api_permissions_scope_and_input_contract(database, tenants, tenant_client):
    from src.models.identity import Membership

    ids = []
    for owner in tenants:
        actor = prepare(database, owner)
        with Session(database) as db:
            bind_tenant(db, owner["org"])
            db.info["principal"] = Principal("admin", actor, owner["org"])
            identity = start(db).id
            cancel_execution(db, identity, "Tenant fixture")
            ids.append(identity)
    base = f"/workflow-executions/{ids[0]}"
    assert tenant_client.get(base + "/controls").status_code == 200
    assert tenant_client.get(f"/workflow-executions/{ids[1]}/controls").status_code == 404
    assert (
        tenant_client.post(
            f"/workflow-executions/{ids[1]}/recover", json={"reason": "cross tenant"}
        ).status_code
        == 404
    )
    assert (
        tenant_client.post(
            base + "/recover", json={"reason": "changed", "input": {"value": 9}}
        ).status_code
        == 422
    )
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        db.scalar(select(Membership)).role = "viewer"
        db.commit()
    assert not tenant_client.get(base + "/controls").json()["can_recover"]
    assert tenant_client.post(base + "/recover", json={"reason": "forbidden"}).status_code == 403
    tenant_client.headers.pop("authorization")
    assert tenant_client.get(base + "/controls").status_code == 401


def test_cancel_race_never_reopens_terminal_source(database):
    with Session(database) as db:
        identity = start(db).id
    barrier = Barrier(2)

    def operate(cancel):
        with Session(database) as db:
            barrier.wait()
            if cancel:
                cancel_execution(db, identity, "Concurrent cancellation")
                return None
            try:
                return recover(db, identity, "Concurrent recovery").id
            except HTTPException as error:
                assert error.status_code == 409
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(operate, [True, False]))
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "cancelled"
        child = recover(db, identity, "Retry after cancellation became visible")
        assert child.id != identity
        assert db.scalar(select(func.count()).select_from(ExecutionRecovery)) == 1


@pytest.mark.parametrize("round_limit", [2, 6])
def test_llm_recovery_retains_calls_and_spent_budget(database, monkeypatch, round_limit):
    from src.models.llm_conversation import LLMConversation
    from src.services.llm_tool_execution import attempt_metadata
    from tests.test_execution_approvals import decision
    from tests.test_llm_tools import call, response, setup

    def interrupted():
        raise ExecutionError("provider_refused", "Injected terminal provider failure")

    identity, registry, provider, effects = setup(
        database,
        monkeypatch,
        [response(call()), interrupted, response(content='{"value":3}')],
        write=True,
        overrides={"max_provider_rounds": round_limit},
    )
    approve(database)
    drain(database, registry)
    assert len(effects) == 1
    with Session(database) as db:
        source = db.scalar(select(LLMConversation))
        source_id = source.id
        assert len(source.state["rounds"]) == 2
        if round_limit == 2:
            assert not controls(db, identity)["can_recover"]
            with pytest.raises(HTTPException):
                recover(db, identity, "Cannot reset provider budget")
            return
        child_id = recover(db, identity, "Continue without repeating confirmed write").id
    drain(database, registry)
    with Session(database) as db:
        gate = db.scalar(
            select(ExecutionApproval).where(ExecutionApproval.execution_id == child_id)
        )
        approval_id, payload_hash = gate.id, gate.payload_hash
    decision(database, approval_id, payload_hash)
    drain(database, registry)
    assert len(effects) == 1 and len(provider.calls) == 3
    with Session(database) as db:
        assert db.get(WorkflowExecution, child_id).status == "completed"
        assert len(db.get(LLMConversation, source_id).state["rounds"]) == 2
        child_step = db.scalar(
            select(StepRun).where(StepRun.execution_id == child_id, StepRun.node_id == "generate")
        )
        continuation = db.scalar(
            select(LLMConversation).where(LLMConversation.step_run_id == child_step.id)
        )
        assert len(continuation.state["rounds"]) == 3
        attempt = db.scalar(select(StepAttempt).where(StepAttempt.step_run_id == child_step.id))
        usage = attempt_metadata(db, attempt)
        assert usage["total_tokens"] == 15
        assert usage["tool_calls"][0]["effect_id"]


def test_expired_approval_is_not_copied_into_recovery(database):
    from datetime import timedelta

    from src.services import approval_runtime
    from tests.test_execution_approvals import graph, inputs

    with Session(database) as db:
        identity = start(db, graph({"deadline_seconds": 120}), inputs()).id
    drain(database)
    with Session(database) as db:
        old = db.scalar(select(ExecutionApproval))
        old_id, expires = old.id, old.expires_at
    approval_runtime.expire_approval_waits(database, now=expires + timedelta(seconds=1))
    with Session(database) as db:
        assert db.get(ExecutionApproval, old_id).status == "expired"
        child_id = recover(db, identity, "New approval window").id
    drain(database)
    with Session(database) as db:
        new = db.scalar(select(ExecutionApproval).where(ExecutionApproval.execution_id == child_id))
        assert new.status == "pending" and new.id != old_id
        assert db.get(ExecutionApproval, old_id).status == "expired"


def test_parallel_recovery_preserves_completed_sibling_and_joins_once(database):
    from tests.test_parallel_runtime import graph

    with Session(database) as db:
        identity = start(db, graph(), {}).id
    registry = ExecutorRegistry()
    original = registry.executors["code"]

    def fail_right(node, *args):
        if node.id == "right":
            raise ExecutionError("output_invalid", "Injected branch failure")
        return original(node, *args)

    registry.executors["code"] = fail_right
    drain(database, registry)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "failed"
        child_id = recover(db, identity, "Recover failed branch").id
    drain(database)
    with Session(database) as db:
        child = db.get(WorkflowExecution, child_id)
        assert child.status == "completed" and child.output_json == {"left": 2, "right": 3}
        joins = db.scalars(
            select(StepRun).where(StepRun.execution_id == child_id, StepRun.node_id == "join")
        ).all()
        assert len(joins) == 1


def test_quality_recovery_preserves_iteration_and_requests_fresh_approval(database, monkeypatch):
    from src.services.execution_registry import DEFAULT_REGISTRY
    from tests.test_execution_approvals import decision
    from tests.test_quality_revisions import review, run_fixture

    identity, provider = run_fixture(
        database,
        monkeypatch,
        [{"value": 2}, review(), {"value": 3}, review(retry=False), {"value": 3}],
    )
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).checkpoint_json["quality"]["iteration"] == 1
        cancel_execution(db, identity, "Cancel at quality approval")
        child_id = recover(db, identity, "Preserve reviewed iteration").id
    drain(database, DEFAULT_REGISTRY)
    with Session(database) as db:
        gate = db.scalar(
            select(ExecutionApproval).where(ExecutionApproval.execution_id == child_id)
        )
        assert gate.iteration == 1 and gate.status == "pending"
        approval_id, payload_hash = gate.id, gate.payload_hash
    decision(database, approval_id, payload_hash)
    drain(database, DEFAULT_REGISTRY)
    with Session(database) as db:
        assert db.get(WorkflowExecution, child_id).status == "completed"
        assert db.get(WorkflowExecution, child_id).output_json == {"value": 3}


def test_exhausted_effect_budget_is_not_reset(database, server, monkeypatch):
    identity, *_ = http_fixture(database, server, monkeypatch, path="/status/503")
    drain(database)
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        assert effect.attempts == 3 and effect.status == "failed"
        state = controls(db, identity)
        assert not state["can_recover"]
        assert any("exhausted" in reason for reason in state["reasons"])
        with pytest.raises(HTTPException):
            recover(db, identity, "Cannot reset effect budget")
    assert len(server.calls) == 3
