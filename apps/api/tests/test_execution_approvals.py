import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from alembic import command
from src.models.audit_event import AuditEvent
from src.models.durable_job import DurableJob
from src.models.execution_approval import ExecutionApproval
from src.models.identity import Membership, ServicePrincipal, User
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.schemas.execution_approval import ApprovalDecision, ApprovalDecisionRead
from src.services import approval_runtime as approvals
from src.services import durable_queue as queue
from src.services.execution_cancellation import cancel_execution
from src.services.graph_interpreter import run_deterministic_execution
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from src.services.workflow_transactions import workflow_transaction
from src.worker import run_worker
from tests.generic_migration_fixtures import pre_deadline_execution
from tests.test_graph_interpreter import start
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_graph import NUMBER, STRING, code, edge, obj, ref
from tests.test_workflow_transactions_postgres import database as database

PAYLOAD = obj(value=NUMBER)
REVIEW = obj(
    approved={"type": "boolean"},
    quality_score=NUMBER,
    issues={"type": "array", "items": obj(claim=STRING, problem=STRING, severity=STRING)},
    retry_recommended={"type": "boolean"},
)


def graph(config=None):
    return {
        "entry_node": "gate",
        "input_schema": obj(payload=PAYLOAD, review=REVIEW),
        "output_schema": PAYLOAD,
        "outputs": {"value": ref("value", "finish")},
        "nodes": [
            {
                "id": "gate",
                "type": "approval",
                "config": config or {"max_review_retries": 1},
                "input_schema": obj(payload=PAYLOAD, review=REVIEW),
                "output_schema": PAYLOAD,
                "inputs": {"payload": ref("payload"), "review": ref("review")},
            },
            code(
                "finish",
                input_schema=PAYLOAD,
                output_schema=PAYLOAD,
                inputs={"value": ref("value", "gate")},
            ),
        ],
        "edges": [edge("gate", "finish")],
    }


def inputs(high=False):
    return {
        "payload": {"value": 2},
        "review": {
            "approved": not high,
            "quality_score": 0.7,
            "issues": [{"claim": "fixture", "problem": "verify", "severity": "high"}]
            if high
            else [],
            "retry_recommended": high,
        },
    }


def pending(database, config=None):
    with Session(database) as db:
        identity = start(db, graph(config), inputs()).id
    queue.process_claim(database, queue.claim_jobs(database, "register")[0])
    with Session(database) as db:
        item = db.scalar(select(ExecutionApproval).where(ExecutionApproval.status == "pending"))
        return identity, item.id, item.payload_hash


def decision(database, identity, payload_hash, action="approve", **kwargs):
    with Session(database) as db:
        item = approvals.decide_approval(
            db,
            identity,
            ApprovalDecision(
                action=action,
                expected_payload_hash=payload_hash,
                **kwargs,
            ),
        )
        return ApprovalDecisionRead.model_validate(item).model_dump(mode="json")


def test_approval_wait_approve_and_identical_replay_resume_once(database):
    identity, approval_id, payload_hash = pending(database)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    result = decision(database, approval_id, payload_hash)
    assert result["status"] == "approved"
    assert decision(database, approval_id, payload_hash) == result
    with pytest.raises(HTTPException) as error:
        decision(database, approval_id, payload_hash, "reject")
    assert error.value.status_code == 409
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"value": 2}
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 3
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 2


def test_edit_supersedes_snapshot_and_requires_new_approval(database):
    identity, approval_id, payload_hash = pending(database)
    result = decision(database, approval_id, payload_hash, "edit", edited_payload={"value": 9})
    assert result["status"] == "superseded"
    assert (
        decision(database, approval_id, payload_hash, "edit", edited_payload={"value": 9}) == result
    )
    with pytest.raises(HTTPException):
        decision(database, approval_id, payload_hash)
    with Session(database) as db:
        item = db.scalar(select(ExecutionApproval).where(ExecutionApproval.status == "pending"))
        assert str(item.id) == result["replacement_id"] and item.payload_hash != payload_hash
        assert item.payload_json == {"value": 9} and item.revision == 2
        new_id, new_hash = item.id, item.payload_hash
    decision(database, new_id, new_hash)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"value": 9}
        assert db.get(ExecutionApproval, approval_id).payload_json == {"value": 2}


def test_review_retry_has_distinct_bounded_iteration_and_retained_feedback(database):
    identity, approval_id, payload_hash = pending(database)
    decision(database, approval_id, payload_hash, "request_retry", human_feedback="Recheck")
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        current = db.scalar(select(ExecutionApproval).where(ExecutionApproval.status == "pending"))
        assert current.iteration == 1 and current.human_feedback == "Recheck"
        assert db.get(WorkflowExecution, identity).status == "waiting"
        current_id, current_hash = current.id, current.payload_hash
        assert [attempt.number for attempt in db.scalars(select(StepAttempt))] == [1, 1]
    with pytest.raises(HTTPException, match="retry limit"):
        decision(database, current_id, current_hash, "request_retry")
    decision(database, current_id, current_hash)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0


def test_governed_input_change_invalidates_old_snapshot(database):
    identity, approval_id, payload_hash = pending(database)
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        step = db.scalar(select(StepRun))
        with workflow_transaction(db, run):
            updated = deepcopy(step.input_json)
            updated["payload"]["value"] = 7
            step.input_json = updated
    with pytest.raises(HTTPException, match="invalidated"):
        decision(database, approval_id, payload_hash)
    with Session(database) as db:
        assert db.get(ExecutionApproval, approval_id).status == "invalidated"
        fresh = db.scalar(select(ExecutionApproval).where(ExecutionApproval.status == "pending"))
        assert fresh.payload_json == {"value": 7}
        assert db.get(WorkflowExecution, identity).status == "waiting"
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1


@pytest.mark.parametrize("operation", ["reject", "cancel", "expire"])
def test_rejection_cancellation_expiry_stop_pending_approval(database, operation):
    identity, approval_id, payload_hash = pending(database, {"deadline_seconds": 60})
    if operation == "reject":
        decision(database, approval_id, payload_hash, "reject")
    elif operation == "cancel":
        with Session(database) as db:
            cancel_execution(db, identity)
    else:
        with Session(database) as db:
            due = db.get(ExecutionApproval, approval_id).expires_at
        assert approvals.expire_approval_waits(database, now=due) == 1
        assert approvals.expire_approval_waits(database, now=due) == 0
    with Session(database) as db:
        expected = {"reject": "rejected", "cancel": "cancelled", "expire": "expired"}[operation]
        assert db.get(ExecutionApproval, approval_id).status == expected
        assert db.get(WorkflowExecution, identity).status == (
            "failed" if operation == "expire" else "cancelled"
        )
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1
    with pytest.raises(HTTPException):
        decision(database, approval_id, payload_hash)


@pytest.mark.parametrize(
    "actions", [("approve", "approve"), ("approve", "reject", "edit", "cancel")]
)
def test_competing_decisions_are_serialized_with_one_resume(database, actions):
    identity, approval_id, payload_hash = pending(database)
    barrier = Barrier(len(actions))

    def compete(action):
        barrier.wait()
        try:
            if action == "cancel":
                with Session(database) as db:
                    cancel_execution(db, identity)
                return "cancelled"
            return decision(
                database,
                approval_id,
                payload_hash,
                action,
                **({"edited_payload": {"value": 9}} if action == "edit" else {}),
            )["status"]
        except HTTPException as error:
            assert error.status_code == 409
            return "conflict"

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        results = list(pool.map(compete, actions))
    with Session(database) as db:
        assert db.scalar(select(func.count()).select_from(DurableJob)) <= 2
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.target_type == "execution_approval",
                )
            )
            <= 1
        )
        if len(actions) == 2:
            assert results == ["approved", "approved"]
            assert db.get(WorkflowExecution, identity).status == "running"
        else:
            assert db.get(WorkflowExecution, identity).status == "cancelled"
            assert not db.scalar(
                select(ExecutionApproval.id).where(ExecutionApproval.status == "pending")
            )


def test_resume_enqueue_failure_rolls_back_decision_and_audit(database, monkeypatch):
    identity, approval_id, payload_hash = pending(database)

    def failed(*_):
        raise RuntimeError("enqueue fixture")

    monkeypatch.setattr(approvals, "queue_resume", failed)
    with pytest.raises(RuntimeError, match="enqueue fixture"):
        decision(database, approval_id, payload_hash)
    with Session(database) as db:
        assert db.get(ExecutionApproval, approval_id).status == "pending"
        assert db.get(WorkflowExecution, identity).status == "waiting"
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1
        assert not db.scalar(
            select(AuditEvent.id).where(AuditEvent.target_type == "execution_approval")
        )


def test_locally_registered_approval_can_resume_through_worker(database):
    with Session(database) as db:
        run = start(db, graph(), inputs())
        identity = run.id
        assert run_deterministic_execution(db, identity).status == "waiting"
        item = db.scalar(select(ExecutionApproval))
        approval_id, payload_hash = item.id, item.payload_hash
    decision(database, approval_id, payload_hash)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"value": 2}
        assert all(job.status == "completed" for job in db.scalars(select(DurableJob)))


def test_worker_restart_preserves_wait_and_resumes_only_after_decision(database):
    identity, approval_id, payload_hash = pending(database)
    schema = database.get_execution_options()["schema_translate_map"][None]
    env = {
        **os.environ,
        "DATABASE_URL": os.environ["WORKFLOW_TEST_DATABASE_URL"],
        "PGOPTIONS": f"-c search_path={schema}",
        "IDENTITY_ENABLED": "false",
        "WORKER_POLL_SECONDS": "0.01",
    }

    def restarted():
        result = subprocess.run(
            [sys.executable, "-m", "src.worker", "--drain"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr

    restarted()
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "waiting"
    decision(database, approval_id, payload_hash)
    restarted()
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "completed"


@pytest.mark.parametrize("role", ["viewer", "operator", "reviewer", "admin"])
@pytest.mark.parametrize("high", [False, True])
def test_decision_role_and_high_severity_policy(database, tenants, tenant_client, role, high):
    actor = prepare(database, tenants[0])
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        db.info["principal"] = Principal("admin", actor, tenants[0]["org"])
        start(db, graph(), inputs(high))
    queue.process_claim(database, queue.claim_jobs(database, "worker")[0])
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        item = db.scalar(select(ExecutionApproval))
        identity, payload_hash = item.id, item.payload_hash
    prepare(database, tenants[0], role)
    response = tenant_client.post(
        f"/execution-approvals/{identity}/decide",
        json={"action": "approve", "expected_payload_hash": payload_hash},
    )
    allowed = role == "admin" or (role == "reviewer" and not high)
    assert response.status_code == (200 if allowed else 403), response.text
    if allowed:
        assert set(response.json()) == {"id", "status", "replacement_id"}
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        assert db.get(ExecutionApproval, identity).decided_by_user_id == (
            actor if allowed else None
        )


def test_tenant_revocation_and_service_scope_cannot_grant_reviewer_role(
    database, tenants, tenant_client
):
    items = []
    for tenant in tenants:
        actor = prepare(database, tenant)
        with Session(database) as db:
            bind_tenant(db, tenant["org"])
            db.info["principal"] = Principal("admin", actor, tenant["org"])
            start(db, graph(), inputs())
    for claim in queue.claim_jobs(database, "worker", 2):
        queue.process_claim(database, claim)
    for tenant in tenants:
        with Session(database) as db:
            bind_tenant(db, tenant["org"])
            item = db.scalar(select(ExecutionApproval))
            items.append((item.id, item.payload_hash))
    actor = prepare(database, tenants[0], "reviewer")
    for index, (identity, payload_hash) in enumerate(items):
        response = tenant_client.get(f"/execution-approvals/{identity}")
        assert response.status_code == (200 if index == 0 else 404)
    own_id, own_hash = items[0]
    other_id, other_hash = items[1]
    assert (
        tenant_client.post(
            f"/execution-approvals/{other_id}/decide",
            json={"action": "approve", "expected_payload_hash": other_hash},
        ).status_code
        == 404
    )
    with Session(database) as db:
        member = db.scalar(
            select(Membership).where(Membership.organization_id == tenants[0]["org"])
        )
        member.active = False
        db.commit()
    body = {"action": "approve", "expected_payload_hash": own_hash}
    assert tenant_client.post(f"/execution-approvals/{own_id}/decide", json=body).status_code == 403
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        db.get(User, actor).kind = "service"
        db.add(
            ServicePrincipal(
                user_id=actor,
                organization_id=tenants[0]["org"],
                role="operator",
                scopes=["approval.decide"],
            )
        )
        db.commit()
    assert tenant_client.get(f"/execution-approvals/{own_id}").status_code == 403
    response = tenant_client.post(f"/execution-approvals/{own_id}/decide", json=body)
    assert response.status_code == 403, response.text
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        assert db.get(ExecutionApproval, own_id).status == "pending"


def test_approval_migration_guards_snapshot_and_resolved_history():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration80_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f079_durable_delays")
            with Session(conn) as db:
                pre_deadline_execution(db)
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            _, identity, payload_hash = pending(scoped)
            with pytest.raises(Exception, match="snapshot is immutable"):
                conn.execute(text("UPDATE execution_approvals SET payload_hash=repeat('a',64)"))
            conn.rollback()
            edited = decision(scoped, identity, payload_hash, "edit", edited_payload={"value": 4})
            with Session(scoped) as db:
                current = db.get(ExecutionApproval, uuid.UUID(edited["replacement_id"]))
                current_id, current_hash = current.id, current.payload_hash
            decision(scoped, current_id, current_hash)
            assert run_worker(scoped, drain=True, poll_seconds=0.01) == 0
            with pytest.raises(Exception, match="immutable approval history"):
                conn.execute(text("UPDATE execution_approvals SET status='pending'"))
            conn.rollback()
            with pytest.raises(RuntimeError, match="Retain execution approval history"):
                command.downgrade(config, "f079_durable_delays")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_decision_time_expiry_applies_reject_policy(database, monkeypatch):
    identity, approval_id, payload_hash = pending(
        database,
        {
            "deadline_seconds": 60,
            "timeout_action": "reject",
        },
    )
    with Session(database) as db:
        due = db.get(ExecutionApproval, approval_id).expires_at
    monkeypatch.setattr(approvals, "runtime_now", lambda _: due)
    with pytest.raises(HTTPException, match="expired"):
        decision(database, approval_id, payload_hash)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).status == "cancelled"
        assert db.get(ExecutionApproval, approval_id).status == "expired"
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 1


def test_edits_preserve_high_severity_policy_and_reject_forged_actor(
    database, tenants, tenant_client
):
    actor = prepare(database, tenants[0])
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        db.info["principal"] = Principal("admin", actor, tenants[0]["org"])
        start(db, graph(), inputs(True))
    queue.process_claim(database, queue.claim_jobs(database, "register")[0])
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        item = db.scalar(select(ExecutionApproval))
        identity, payload_hash = item.id, item.payload_hash
    prepare(database, tenants[0], "reviewer")
    body = {"action": "edit", "expected_payload_hash": payload_hash, "edited_payload": {"value": 5}}
    assert (
        tenant_client.post(
            f"/execution-approvals/{identity}/decide",
            json={
                **body,
                "approved_by_user_id": str(uuid.uuid4()),
            },
        ).status_code
        == 422
    )
    assert (
        tenant_client.post(
            f"/execution-approvals/{identity}/decide",
            json={
                **body,
                "edited_payload": {"wrong": "shape"},
            },
        ).status_code
        == 422
    )
    response = tenant_client.post(f"/execution-approvals/{identity}/decide", json=body)
    assert response.status_code == 200, response.text
    new_id = response.json()["replacement_id"]
    current = tenant_client.get(f"/execution-approvals/{new_id}").json()
    assert current["review_json"]["issues"][0]["severity"] == "high"
    approval = {"action": "approve", "expected_payload_hash": current["payload_hash"]}
    assert (
        tenant_client.post(f"/execution-approvals/{new_id}/decide", json=approval).status_code
        == 403
    )
    prepare(database, tenants[0], "admin")
    assert (
        tenant_client.post(f"/execution-approvals/{new_id}/decide", json=approval).status_code
        == 200
    )


def test_same_version_and_payload_still_bind_approval_hash_to_exact_execution(database):
    from src.models.workflow_definition import WorkflowVersion
    from src.schemas.execution_start import ExecutionStartRequest
    from src.services.execution_starts import start_execution

    first_run, first_id, first_hash = pending(database)
    with Session(database) as db:
        run = db.get(WorkflowExecution, first_run)
        version = db.get(WorkflowVersion, run.version_id)
        second_run = start_execution(
            db,
            ExecutionStartRequest(
                definition_id=version.definition_id,
                version_id=version.id,
                input=inputs(),
                idempotency_key=uuid.uuid4().hex,
            ),
        ).id
    queue.process_claim(database, queue.claim_jobs(database, "second")[0])
    with Session(database) as db:
        second = db.scalar(
            select(ExecutionApproval).where(ExecutionApproval.execution_id == second_run)
        )
        assert second.payload_hash != first_hash
        second_id = second.id
    with pytest.raises(HTTPException, match="payload changed"):
        decision(database, second_id, first_hash)
    decision(database, first_id, first_hash)


def test_cached_session_cannot_approve_a_changed_governed_input(database):
    identity, approval_id, payload_hash = pending(database)
    with Session(database) as cached:
        stale = cached.scalar(select(StepRun))
        assert stale.input_json["payload"]["value"] == 2
        with Session(database) as editor:
            run = editor.get(WorkflowExecution, identity)
            step = editor.get(StepRun, stale.id)
            with workflow_transaction(editor, run):
                changed = deepcopy(step.input_json)
                changed["payload"]["value"] = 8
                step.input_json = changed
        with pytest.raises(HTTPException, match="invalidated"):
            approvals.decide_approval(
                cached,
                approval_id,
                ApprovalDecision(
                    action="approve",
                    expected_payload_hash=payload_hash,
                ),
            )
    with Session(database) as db:
        assert db.get(ExecutionApproval, approval_id).status == "invalidated"
        assert db.scalar(
            select(ExecutionApproval).where(ExecutionApproval.status == "pending")
        ).payload_json == {"value": 8}
