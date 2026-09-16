import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from src.config import settings
from src.models.durable_job import DurableJob
from src.models.tool import ToolCredential, ToolExecution
from src.models.workflow_execution import StepRun, WorkflowExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.tool import CredentialCreate, EffectResolution, ToolContract, ToolCreate
from src.schemas.workflow_definition import DefinitionCreate
from src.schemas.workflow_graph import RetryPolicy
from src.services import durable_queue as queue
from src.services import github_tool, tool_catalog, tool_effects, workflow_definitions
from src.services.execution_starts import start_execution
from src.services.retry_runtime import retry_decision
from src.services.worker_leases import recover_claim
from src.worker import run_worker
from tests.test_execution_approvals import REVIEW
from tests.test_github_tool import CONTENT, ORGANIZATION, SECRET, configure
from tests.test_github_tool import server as server
from tests.test_http_tool_runtime import approve, snapshot
from tests.test_worker_leases import expire
from tests.test_workflow_graph import STRING, edge, literal, obj
from tests.test_workflow_transactions_postgres import database as database

ISSUE = obj(number={"type": "integer"}, title=STRING, body=STRING, state=STRING, url=STRING)
CREATE_INPUT, CREATE_OUTPUT = obj(title=STRING, body=STRING), obj(issue=ISSUE)
READ_INPUT = obj(page={"type": "integer"})
READ_OUTPUT = obj(
    issues={"type": "array", "items": ISSUE},
    next_page={"type": ["integer", "null"]},
    page_limit_reached={"type": "boolean"},
)
RETRY = {
    "max_attempts": 3,
    "initial_delay_seconds": 0,
    "retryable_errors": ["tool_unavailable", "tool_timeout", "tool_rate_limit"],
}


def fixture(database, server, monkeypatch, *, write=True, govern=True):
    configure(server, monkeypatch)
    monkeypatch.setattr(
        settings, "tool_credential_values", {f"{ORGANIZATION}/github-fixture": SecretStr(SECRET)}
    )
    schema, output = (CREATE_INPUT, CREATE_OUTPUT) if write else (READ_INPUT, READ_OUTPUT)
    arguments = CONTENT if write else {"page": 1}
    envelope = obj(node_id=STRING, tool_id=STRING, version={"type": "integer"}, arguments=schema)
    with Session(database) as db:
        credential = tool_catalog.create_credential(
            db, CredentialCreate(name="GitHub fixture", source_alias="github-fixture")
        )
        version = tool_catalog.create(
            db,
            ToolCreate(
                name="GitHub fixture",
                contract=ToolContract(
                    adapter="github",
                    input_schema=schema,
                    output_schema=output,
                    credential_ref=credential.id,
                    side_effecting=write,
                    retry=RETRY,
                    options={
                        "repository": "work",
                        "operation": "create_issue" if write else "read_issues",
                    },
                ),
            ),
        )
        node = {
            "id": "action",
            "type": "tool",
            "input_schema": schema,
            "output_schema": output,
            "inputs": {key: literal(value) for key, value in arguments.items()},
            "retry": RETRY,
            "config": {"adapter": "github", "tool_id": str(version.definition_id), "version": 1},
        }
        graph = {"entry_node": "action", "nodes": [node]}
        if write and govern:
            node["config"]["approval_node"] = "gate"
            graph["entry_node"] = "gate"
            graph["nodes"].insert(
                0,
                {
                    "id": "gate",
                    "type": "approval",
                    "config": {"deadline_seconds": 300},
                    "input_schema": obj(payload=envelope, review=REVIEW),
                    "output_schema": envelope,
                    "inputs": {
                        "payload": literal(
                            {
                                "node_id": "action",
                                "tool_id": str(version.definition_id),
                                "version": 1,
                                "arguments": arguments,
                            }
                        ),
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
            db, DefinitionCreate(name="GitHub workflow", graph=graph)
        )
        workflow_definitions.publish(db, definition.id, 1)
        run = start_execution(
            db,
            ExecutionStartRequest(
                definition_id=definition.id, input={}, idempotency_key="github-fixture"
            ),
        )
        return run.id, credential.id, version.id


def test_approved_create_persists_marker_before_post_and_redacts_receipt(
    database, server, monkeypatch
):
    run_id, *_ = fixture(database, server, monkeypatch)
    original = github_tool.http_tool.request

    def inspect(*args, **kwargs):
        with Session(database) as db:
            effect = db.scalar(select(ToolExecution))
            assert effect.reconciliation["marker"] == github_tool.marker(effect.effect_key, SECRET)
            assert effect.dispatched and effect.attempts == 1
        return original(*args, **kwargs)

    monkeypatch.setattr(github_tool.http_tool, "request", inspect)
    approve(database)
    assert not server.calls
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("completed", "succeeded")
    assert len(server.issues) == 1 and len(server.calls) == 1
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        assert SECRET not in json.dumps(tool_catalog.public(effect), default=str)
        assert effect.result_json["issue"]["body"] == CONTENT["body"]


@pytest.mark.parametrize("hidden", [False, True])
def test_lost_response_recovers_unique_receipt_or_stays_unknown(
    database, server, monkeypatch, hidden
):
    run_id, *_ = fixture(database, server, monkeypatch)
    approve(database)
    server.lost = True
    assert queue.process_claim(database, queue.claim_jobs(database, "first")[0])
    assert snapshot(database, run_id)[1] == "unknown" and len(server.issues) == 1
    if hidden:
        server.response = []
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == (
        ("failed", "unknown") if hidden else ("completed", "reconciled")
    )
    assert sum(call[0] == "POST" for call in server.calls) == 1
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        marker = effect.reconciliation["marker"]
        assert marker
        if hidden:
            receipt = {
                "issue": {
                    **CONTENT,
                    "number": 1,
                    "state": "open",
                    "url": "https://github.com/acme/work/issues/1",
                }
            }
            tool_effects.resolve(
                db,
                effect.id,
                EffectResolution(
                    succeeded=True,
                    result=receipt,
                    evidence="Fixture operator inspected the created issue",
                ),
            )
            db.refresh(effect)
            assert effect.reconciliation["marker"] == marker
            assert effect.reconciliation["method"] == "operator"
            assert "outcome" not in effect.reconciliation
            assert db.get(WorkflowExecution, run_id).status == "failed"


def test_worker_crash_before_receipt_commit_recovers_without_duplicate_issue(
    database, server, monkeypatch
):
    run_id, *_ = fixture(database, server, monkeypatch)
    approve(database)
    claim = queue.claim_jobs(database, "crashed")[0]
    original = tool_effects.finish

    def crash(*args, **kwargs):
        raise SystemExit("Fixture crash after remote creation")

    monkeypatch.setattr(tool_effects, "finish", crash)
    with pytest.raises(SystemExit):
        queue.process_claim(database, claim)
    monkeypatch.setattr(tool_effects, "finish", original)
    expire(database, claim)
    assert recover_claim(database, claim)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("completed", "reconciled")
    assert len(server.issues) == 1 and sum(call[0] == "POST" for call in server.calls) == 1


@pytest.mark.parametrize("change", ["credential", "repository", "operation"])
def test_revocation_or_policy_change_after_approval_denies_creation(
    database, server, monkeypatch, change
):
    run_id, credential_id, _ = fixture(database, server, monkeypatch)
    approve(database)
    if change == "credential":
        with Session(database) as db:
            tool_catalog.set_active(db, ToolCredential, credential_id, False)
    else:
        raw = settings.github_tool_repositories[f"{ORGANIZATION}/work"]
        raw["repo" if change == "repository" else "operations"] = (
            "other" if change == "repository" else ["read_issues"]
        )
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    assert snapshot(database, run_id)[:2] == ("failed", None) and not server.calls


def test_create_without_approval_gate_cannot_publish(database, server, monkeypatch):
    with pytest.raises(HTTPException) as error:
        fixture(database, server, monkeypatch, govern=False)
    assert error.value.status_code == 422 and not server.calls


def test_rate_limit_persists_due_time_and_guard_blocks_early_recovery(
    database, server, monkeypatch
):
    run_id, *_ = fixture(database, server, monkeypatch, write=False)
    server.error = 429, {"message": "limited"}, {"Retry-After": "120"}
    assert queue.process_claim(database, queue.claim_jobs(database, "limited")[0])
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        retry_at = datetime.fromisoformat(effect.reconciliation["retry_not_before"])
        step = db.scalar(select(StepRun))
        job = db.scalar(select(DurableJob).where(DurableJob.status == "queued"))
        assert retry_at == step.next_attempt_at == job.due_at
        assert retry_at > db.scalar(select(func.clock_timestamp())) + timedelta(seconds=110)
        assert effect.status == "failed" and effect.attempts == 1
        # Simulate an early recovery delivery without changing retained provider metadata.
        db.connection().execute(
            update(DurableJob.__table__)
            .where(DurableJob.id == job.id)
            .values(due_at=func.clock_timestamp())
        )
        db.connection().execute(
            update(StepRun.__table__)
            .where(StepRun.id == step.id)
            .values(next_attempt_at=func.clock_timestamp())
        )
        db.commit()
    claim = queue.claim_jobs(database, "early-recovery")[0]
    assert queue.process_claim(database, claim)
    assert len(server.calls) == 1
    with Session(database) as db:
        assert db.scalar(select(ToolExecution)).attempts == 1
        assert db.get(WorkflowExecution, run_id).status == "running"
        assert db.scalar(select(StepRun)).next_attempt_at == retry_at
        assert db.scalar(select(DurableJob).where(DurableJob.status == "queued")).due_at == retry_at


def test_provider_backoff_takes_precedence_over_jitter_and_respects_run_deadline():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    policy = RetryPolicy(
        max_attempts=3, retryable_errors=["tool_rate_limit"], initial_delay_seconds=0
    )
    due = now + timedelta(seconds=120)
    assert retry_decision(policy, 1, "tool_rate_limit", now, retry_not_before=due)[1] == due
    assert retry_decision(
        policy, 1, "tool_rate_limit", now, now + timedelta(seconds=60), retry_not_before=due
    )[1:] == (None, "run_deadline")


def test_worker_read_redacts_provider_secret_text(database, server, monkeypatch):
    run_id, *_ = fixture(database, server, monkeypatch, write=False)
    server.issues.append(
        {"number": 1, "title": "Fixture", "body": "Token: " + SECRET, "state": "open"}
    )
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    status, effect, result = snapshot(database, run_id)
    assert (status, effect) == ("completed", "succeeded")
    assert result["issues"][0]["body"] == "Token: [REDACTED]"
