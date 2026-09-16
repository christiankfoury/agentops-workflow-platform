import json

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep
from src.models.cost_event import CostEvent
from src.models.human_approval import HumanApproval
from src.models.uploaded_input import UploadedInput
from src.models.workflow_execution import StepRun
from src.models.workflow_run import RunMode, WorkflowRun
from src.schemas.human_approval import HumanApprovalAction, HumanApprovalEdit
from src.services.business_approvals import adapt
from src.services.business_projection import execution_for
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.sales_analyst import run_sales_analyst
from src.services.sales_template import install, start_sales
from src.worker import run_worker
from tests.test_llm_execution import Provider
from tests.test_quality_revisions import review
from tests.test_workflow_transactions_postgres import database as database

ANALYSIS = {
    key: ["Revenue 10"]
    for key in [
        "key_findings",
        "risks",
        "opportunities",
        "recommendations",
        "supporting_evidence",
    ]
}


def test_worker_provider_factory_unwraps_secret_without_exposing_it(monkeypatch):
    from pydantic import SecretStr

    from src.config import settings
    from src.services import llm_execution

    captured = {}
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("fixture-provider-key"))
    monkeypatch.setattr(llm_execution, "LLMClient", lambda **kwargs: captured.update(kwargs))
    llm_execution.client_factory({"model": "fixture-model", "timeout_seconds": 12})
    assert captured["api_key"] == "fixture-provider-key"
    assert captured["max_retries"] == 0 and captured["timeout"] == 12


def test_output_validator_contract_is_checked_before_execution():
    import uuid

    from pydantic import ValidationError

    from src.schemas.workflow_graph import WorkflowGraph
    from src.services.execution_registry import ensure_executable
    from tests.test_llm_execution import graph

    payload = graph(uuid.uuid4())
    payload["nodes"][0]["config"]["output_validator"] = "business.final_report.v1"
    with pytest.raises(ValidationError, match="Output validator contract"):
        ensure_executable(WorkflowGraph.model_validate(payload))


def start(database, mode=RunMode.multi_agent):
    with Session(database) as db:
        install(db)
        source = UploadedInput(
            title="Sales fixture", input_type="sales_report", raw_text="Revenue 10"
        )
        db.add(source)
        db.commit()
        run = start_sales(db, source, mode)
        return run.id


def drain(database, monkeypatch, outputs):
    provider = Provider(outputs)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, capacity=1, drain=True, poll_seconds=0.01) == 0
    return provider


def test_sales_human_edit_writer_and_idempotent_cost_projection(database, monkeypatch):
    identity = start(database)
    drain(database, monkeypatch, [ANALYSIS, review(approved=True, retry=False, score=0.95)])
    with Session(database) as db:
        run = db.get(WorkflowRun, identity)
        assert run.status == "waiting_for_human"
        assert run.execution_id == execution_for(db, identity).id
        with pytest.raises(HTTPException) as caught:
            run_sales_analyst(db, run, object())
        assert caught.value.status_code == 409
        pending = db.scalar(select(HumanApproval).where(HumanApproval.status == "pending"))
        previous = pending.id
        changed = {**ANALYSIS, "recommendations": ["Human-approved action"]}
        replacement = adapt(
            db,
            pending,
            "edit",
            HumanApprovalEdit(
                expected_payload_hash=pending.expected_payload_hash,
                edited_analysis_json=changed,
                human_feedback="Use the verified action",
            ),
        )
        assert replacement.id != previous
        with pytest.raises(HTTPException):
            adapt(
                db,
                pending,
                "approve",
                HumanApprovalAction(expected_payload_hash=pending.expected_payload_hash),
            )
        adapt(
            db,
            replacement,
            "approve",
            HumanApprovalAction(expected_payload_hash=replacement.expected_payload_hash),
        )
    provider = drain(
        database, monkeypatch, [{"final_output": "Revenue 10. Human-approved action."}]
    )
    assert (
        json.loads(provider.calls[0]["messages"][0]["content"])["input"]["approved_analysis"]
        == changed
    )
    assert (
        json.loads(provider.calls[0]["messages"][0]["content"])["revision_context"][
            "human_feedback"
        ]
        == "Use the verified action"
    )
    with Session(database) as db:
        run = db.get(WorkflowRun, identity)
        assert run.status == "completed" and "Human-approved" in run.final_output
        assert run.total_tokens == 45 and run.total_cost > 0
        assert len(db.scalars(select(CostEvent)).all()) == 3
        assert len(db.scalars(select(AgentStep)).all()) == 3
        assert len(db.scalars(select(StepRun)).all()) == 4


def test_sales_baseline_is_one_step_and_has_no_approval(database, monkeypatch):
    identity = start(database, RunMode.baseline)
    drain(database, monkeypatch, [{"final_output": "Revenue 10"}])
    with Session(database) as db:
        run = db.get(WorkflowRun, identity)
        assert run.status == "completed" and run.final_output == "Revenue 10"
        assert len(db.scalars(select(StepRun)).all()) == 1
        assert not db.scalars(select(HumanApproval)).all()


@pytest.mark.parametrize("reason", ["low_score", "high_severity", "recommended"])
def test_retry_policy_matches_sales_escalation_and_exhaustion(database, monkeypatch, reason):
    identity = start(database)
    response = review(approved=True, retry=False, score=0.95)
    if reason == "low_score":
        response["quality_score"] = 0.4
    elif reason == "high_severity":
        response["issues"] = [{"claim": "10", "problem": "Verify", "severity": "high"}]
    else:
        response["retry_recommended"] = True
    provider = drain(database, monkeypatch, [ANALYSIS, response] * 3)
    assert len(provider.calls) == 6
    with Session(database) as db:
        run = db.get(WorkflowRun, identity)
        assert run.status == "waiting_for_human" and run.retry_count == 2
        pending = db.scalar(select(HumanApproval).where(HumanApproval.status == "pending"))
        body = HumanApprovalAction(expected_payload_hash=pending.expected_payload_hash)
        with pytest.raises(HTTPException, match="Quality revision limit"):
            adapt(db, pending, "request_retry", body)
        adapt(db, pending, "reject", body)
        db.refresh(run)
        assert run.status == "cancelled"
        assert db.get(HumanApproval, pending.id).status == "rejected"


def test_manual_retry_keeps_feedback_and_cancellation_stops_writer(database, monkeypatch):
    from src.services.workflow_recovery import cancel_workflow_run

    identity = start(database)
    drain(database, monkeypatch, [ANALYSIS, review(approved=True, retry=False, score=0.95)])
    with Session(database) as db:
        pending = db.scalar(select(HumanApproval).where(HumanApproval.status == "pending"))
        adapt(
            db,
            pending,
            "request_retry",
            HumanApprovalAction(
                expected_payload_hash=pending.expected_payload_hash,
                human_feedback="Verify revenue",
            ),
        )
    provider = drain(
        database, monkeypatch, [ANALYSIS, review(approved=True, retry=False, score=0.95)]
    )
    content = json.loads(provider.calls[0]["messages"][0]["content"])
    assert content["revision_context"]["human_feedback"] == "Verify revenue"
    with Session(database) as db:
        run = db.get(WorkflowRun, identity)
        cancel_workflow_run(db, run)
        assert run.status == "cancelled"
        assert not db.scalars(select(HumanApproval).where(HumanApproval.status == "pending")).all()
    assert not drain(database, monkeypatch, []).calls


def test_empty_final_report_is_repaired_and_all_returned_usage_is_counted(database, monkeypatch):
    identity = start(database, RunMode.baseline)
    drain(database, monkeypatch, [{"final_output": "  "}, {"final_output": " Revenue 10 "}])
    with Session(database) as db:
        run = db.get(WorkflowRun, identity)
        assert run.final_output == "Revenue 10" and run.total_tokens == 30


def test_api_start_adapters_historical_reads_and_backout(database, monkeypatch):
    from fastapi.testclient import TestClient

    from src.config import settings
    from src.database import get_db
    from src.dependencies import get_llm_client
    from src.main import app

    def connection():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = connection
    app.dependency_overrides[get_llm_client] = lambda: object()
    try:
        with TestClient(app) as client:
            installed = client.post("/workflow-definitions/templates/sales/install")
            assert installed.status_code == 200, installed.text
            assert (
                client.post("/workflow-definitions/templates/sales/install").json()
                == installed.json()
            )
            with Session(database) as db:
                source = UploadedInput(
                    title="API", input_type="sales_report", raw_text="Revenue 10"
                )
                db.add(source)
                db.commit()
                source_id = str(source.id)
            body = {"workflow_type": "sales_report", "input_id": source_id}
            accepted = client.post("/workflow-runs", json=body)
            assert accepted.status_code == 201, accepted.text
            identity = accepted.json()["id"]
            assert accepted.json()["execution_id"] is not None
            started_events = client.get(f"/workflow-runs/{identity}/events").json()
            assert sum(event["event_type"] == "workflow_started" for event in started_events) == 1
            for action in ["run-analyst", "run-reviewer", "run-writer", "run-baseline"]:
                assert client.post(f"/workflow-runs/{identity}/{action}").status_code == 409
            drain(database, monkeypatch, [ANALYSIS, review(approved=True, retry=False, score=0.95)])
            approval = client.get("/human-approvals").json()[0]
            url = f"/human-approvals/{approval['id']}"
            assert (
                client.post(
                    url + "/approve",
                    json={
                        "expected_payload_hash": approval["expected_payload_hash"],
                        "human_feedback": "x" * 4001,
                    },
                ).status_code
                == 422
            )
            assert client.post(url + "/approve").status_code == 409
            assert (
                client.post(url + "/approve", json={"expected_payload_hash": "0" * 64}).status_code
                == 409
            )
            assert (
                client.post(
                    url + "/approve",
                    json={"expected_payload_hash": approval["expected_payload_hash"]},
                ).status_code
                == 200
            )
            drain(database, monkeypatch, [{"final_output": "Revenue 10"}])
            assert client.get(f"/workflow-runs/{identity}").json()["final_output"] == "Revenue 10"
            assert len(client.get(f"/workflow-runs/{identity}/agent-steps").json()) == 3
            assert client.get(f"/workflow-runs/{identity}/events").json()
            monkeypatch.setattr(settings, "sales_template_enabled", False)
            historical = client.post("/workflow-runs", json=body).json()
            assert historical["execution_id"] is None
            assert client.post(f"/workflow-runs/{identity}/run-analyst").status_code == 409
            assert len(client.get("/workflow-runs").json()) == 2
    finally:
        app.dependency_overrides.clear()


def test_projection_remains_linkable_to_existing_evaluation_comparison(database, monkeypatch):
    from src.models.evaluation_case import EvaluationCase
    from src.models.evaluation_result import EvaluationResult
    from src.services.evaluation_comparisons import build_evaluation_comparisons
    from src.services.evaluation_promotion import _get_or_create_existing_run_result

    identity = start(database, RunMode.baseline)
    drain(database, monkeypatch, [{"final_output": "Revenue 10"}])
    multi_id = start(database)
    drain(database, monkeypatch, [ANALYSIS, review(approved=True, retry=False, score=0.95)])
    with Session(database) as db:
        pending = db.scalar(select(HumanApproval).where(HumanApproval.status == "pending"))
        adapt(
            db,
            pending,
            "approve",
            HumanApprovalAction(expected_payload_hash=pending.expected_payload_hash),
        )
    drain(database, monkeypatch, [{"final_output": "Revenue 10"}])
    with Session(database) as db:
        run = db.get(WorkflowRun, identity)
        case = EvaluationCase(
            workflow_type="sales_report",
            title="Same source",
            input_text="Revenue 10",
            expected_facts_json=["Revenue 10"],
            expected_risks_json=[],
            expected_recommendations_json=[],
        )
        db.add(case)
        db.commit()
        first = _get_or_create_existing_run_result(db, case, run)
        repeated = _get_or_create_existing_run_result(db, case, run)
        assert first.id == repeated.id and first.workflow_run_id == identity
        assert len(db.scalars(select(EvaluationResult)).all()) == 1
        assert first.cost == run.total_cost
        multi = db.get(WorkflowRun, multi_id)
        multi_result = _get_or_create_existing_run_result(db, case, multi)
        comparisons = build_evaluation_comparisons(
            [case], [first, multi_result], [run, multi], db.scalars(select(AgentStep)).all()
        )
        assert len(comparisons) == 1
        assert comparisons[0].baseline.workflow_run_id == identity
        assert comparisons[0].multi_agent.workflow_run_id == multi_id
        assert comparisons[0].multi_agent.final_output == "Revenue 10"


def test_concurrent_template_install_is_idempotent(database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from src.models.workflow_definition import WorkflowVersion

    barrier = Barrier(2)

    def install_once():
        with Session(database) as db:
            barrier.wait(timeout=10)
            return [item.id for item in install(db)]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(install_once) for _ in range(2)]
        assert futures[0].result(timeout=30) == futures[1].result(timeout=30)
    with Session(database) as db:
        assert len(db.scalars(select(WorkflowVersion)).all()) == 2


def test_acceptance_projection_failure_rolls_back_both_run_records_and_job(database, monkeypatch):
    from src.models.durable_job import DurableJob
    from src.models.execution_start import ExecutionStart
    from src.models.workflow_execution import WorkflowExecution
    from src.services import business_projection

    def fail_projection(*args):
        raise RuntimeError("Injected projection failure")

    with Session(database) as db:
        install(db)
        source = UploadedInput(
            title="Atomic start", input_type="sales_report", raw_text="Revenue 10"
        )
        db.add(source)
        db.commit()
        monkeypatch.setattr(business_projection, "sync", fail_projection)
        with pytest.raises(RuntimeError, match="Injected projection"):
            start_sales(db, source, RunMode.baseline)
        for model in [WorkflowRun, WorkflowExecution, ExecutionStart, DurableJob]:
            assert not db.scalars(select(model)).all()


def test_sales_migration_retains_history_and_enforces_one_owner():
    import os
    import uuid

    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    from alembic import command
    from src.models.workflow_execution import WorkflowExecution
    from tests.test_workflow_transactions_postgres import make_run

    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration83_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f082_execution_config")
            with Session(conn) as db:
                old_id = make_run(db).id
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            with Session(scoped) as db:
                assert db.get(WorkflowRun, old_id).execution_id is None
            identity = start(scoped, RunMode.baseline)
            with Session(scoped) as db:
                original = execution_for(db, identity)
                db.add(
                    WorkflowExecution(
                        version_id=original.version_id,
                        legacy_run_id=identity,
                        input_json=original.input_json,
                        runtime_config=original.runtime_config,
                        deadline_at=original.deadline_at,
                    )
                )
                with pytest.raises(IntegrityError, match="uq_execution_legacy_run"):
                    db.commit()
                db.rollback()
            with pytest.raises(RuntimeError, match="Retain durable ownership"):
                command.downgrade(config, "f082_execution_config")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
