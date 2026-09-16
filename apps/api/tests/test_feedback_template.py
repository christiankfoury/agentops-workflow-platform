import json
from copy import deepcopy

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep
from src.models.human_approval import HumanApproval
from src.models.uploaded_input import UploadedInput
from src.models.workflow_execution import StepRun
from src.models.workflow_run import RunMode, WorkflowRun
from src.schemas.human_approval import HumanApprovalAction, HumanApprovalEdit
from src.services import human_approvals
from src.services.business_approvals import adapt
from src.services.customer_feedback_classifier import run_customer_feedback_classifier
from src.services.customer_feedback_insight import run_customer_feedback_insight
from src.services.customer_feedback_reviewer import run_customer_feedback_reviewer
from src.services.customer_feedback_writer import run_customer_feedback_writer
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.feedback_template import install, start_feedback
from src.services.llm_client import LLMUsage, TextResponse
from src.services.prompt_versions import seed_default_prompt_versions
from src.services.sales_baseline import run_sales_baseline
from src.services.workflow_state import initialize_run
from src.worker import run_worker
from tests.test_customer_feedback_reviewer_writer_api import (
    CLASSIFIER_OUTPUT as CLASSIFICATION,
)
from tests.test_customer_feedback_reviewer_writer_api import (
    PRODUCT_INSIGHT_OUTPUT as INSIGHT,
)
from tests.test_customer_feedback_reviewer_writer_api import (
    REVIEWER_OUTPUT as REVIEW,
)
from tests.test_llm_execution import Provider
from tests.test_sales_template import drain
from tests.test_workflow_transactions_postgres import database as database

REPORT = "Product Insights Report\nImprove mobile checkout and add bulk export."


class LegacyProvider(Provider):
    def generate_structured(self, **kwargs):
        return super().generate_structured(**kwargs)

    def generate_text(self, **kwargs):
        self.calls.append(kwargs)
        return TextResponse(REPORT, "gpt-4.1-mini", LLMUsage(10, 5))


def start(database, mode=RunMode.multi_agent):
    with Session(database) as db:
        seed_default_prompt_versions(db)
        install(db)
        source = UploadedInput(
            title="Customer Feedback Batch",
            input_type="customer_feedback",
            raw_text="Review 1: The mobile app is slow. Ticket 9: Please add bulk export.",
            notes="Q1 feedback",
        )
        db.add(source)
        db.commit()
        current = start_feedback(db, source, mode)
        legacy = initialize_run(
            db,
            WorkflowRun(
                workflow_type="customer_feedback",
                run_mode=mode,
                input_id=source.id,
            ),
        )
        return current.id, legacy.id


def pending(db, identity):
    return db.scalar(
        select(HumanApproval).where(
            HumanApproval.workflow_run_id == identity,
            HumanApproval.status == "pending",
        )
    )


@pytest.mark.parametrize("action", ["approve", "edit", "reject", "baseline"])
def test_feedback_old_new_fixture_parity(database, monkeypatch, action):
    mode = RunMode.baseline if action == "baseline" else RunMode.multi_agent
    current, legacy = start(database, mode)
    provider = LegacyProvider([CLASSIFICATION, INSIGHT, REVIEW])
    with Session(database) as db:
        old = db.get(WorkflowRun, legacy)
        if action == "baseline":
            run_sales_baseline(db, old, provider)
        else:
            for agent in [
                run_customer_feedback_classifier,
                run_customer_feedback_insight,
                run_customer_feedback_reviewer,
            ]:
                assert agent(db, old, provider).status == "completed"
            approval = pending(db, legacy)
            if action == "edit":
                changed = {**INSIGHT, "top_insights": ["Human verified mobile checkout"]}
                human_approvals.edit_human_approval(db, approval, "Verified", changed)
            if action == "reject":
                human_approvals.reject_human_approval(db, approval)
            else:
                human_approvals.approve_human_approval(db, approval)
                run_customer_feedback_writer(db, old, provider)
    if action == "baseline":
        drain(database, monkeypatch, [{"final_output": REPORT}])
    else:
        drain(database, monkeypatch, [CLASSIFICATION, INSIGHT, REVIEW])
        with Session(database) as db:
            approval = pending(db, current)
            assert approval.reviewer_score == REVIEW["quality_score"]
            if action == "edit":
                approval = adapt(
                    db,
                    approval,
                    "edit",
                    HumanApprovalEdit(
                        expected_payload_hash=approval.expected_payload_hash,
                        edited_analysis_json=changed,
                        human_feedback="Verified",
                    ),
                )
            adapt(
                db,
                approval,
                "reject" if action == "reject" else "approve",
                HumanApprovalAction(expected_payload_hash=approval.expected_payload_hash),
            )
        if action != "reject":
            writer = drain(database, monkeypatch, [{"final_output": REPORT}])
            inputs = json.loads(writer.calls[0]["messages"][0]["content"])["input"]
            assert inputs["approved_insights"] == (changed if action == "edit" else INSIGHT)
            if action == "edit":
                assert (
                    "Human verified mobile checkout" in provider.calls[-1]["messages"][0]["content"]
                )
    with Session(database) as db:
        old, new = db.get(WorkflowRun, legacy), db.get(WorkflowRun, current)
        assert old.status == new.status == ("cancelled" if action == "reject" else "completed")
        assert old.final_output == new.final_output
        assert old.input_id == new.input_id and old.execution_id is None and new.execution_id
        old_steps = db.scalars(
            select(AgentStep)
            .where(AgentStep.workflow_run_id == legacy)
            .order_by(AgentStep.step_order)
        ).all()
        new_steps = db.scalars(
            select(AgentStep)
            .where(AgentStep.workflow_run_id == current)
            .order_by(AgentStep.step_order)
        ).all()
        assert [step.output_json for step in old_steps] == [step.output_json for step in new_steps]
        assert old.total_tokens == new.total_tokens


def test_revision_restarts_classifier_and_resumes_fresh_worker(database, monkeypatch):
    current, _ = start(database)
    provider = Provider([CLASSIFICATION])
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, max_jobs=1, poll_seconds=0.01) == 0
    changed = deepcopy(CLASSIFICATION)
    changed["themes"][0]["count"] = 3
    bad_review = {**REVIEW, "approved": False, "quality_score": 0.4, "retry_recommended": True}
    provider = drain(database, monkeypatch, [INSIGHT, bad_review, changed, INSIGHT, REVIEW])
    calls = [json.loads(call["messages"][0]["content"]) for call in provider.calls]
    assert calls[0]["input"]["classification"] == CLASSIFICATION
    assert calls[3]["input"]["classification"] == changed
    assert calls[2]["revision_context"]["review"]["quality_score"] == 0.4
    with Session(database) as db:
        run = db.get(WorkflowRun, current)
        assert run.status == "waiting_for_human" and run.retry_count == 1
        assert (
            len(db.scalars(select(StepRun).where(StepRun.execution_id == run.execution_id)).all())
            == 7
        )
        approval = pending(db, current)
        adapt(
            db,
            approval,
            "request_retry",
            HumanApprovalAction(
                expected_payload_hash=approval.expected_payload_hash,
                human_feedback="Recheck evidence",
            ),
        )
    provider = drain(database, monkeypatch, [changed, INSIGHT, REVIEW])
    assert (
        json.loads(provider.calls[0]["messages"][0]["content"])["revision_context"][
            "human_feedback"
        ]
        == "Recheck evidence"
    )
    with Session(database) as db:
        approval = pending(db, current)
        with pytest.raises(HTTPException) as error:
            adapt(
                db,
                approval,
                "request_retry",
                HumanApprovalAction(expected_payload_hash=approval.expected_payload_hash),
            )
        assert error.value.status_code == 409


def test_semantic_repairs_and_invalid_human_edit_are_atomic(database, monkeypatch):
    current, _ = start(database)
    bad = deepcopy(CLASSIFICATION)
    bad["themes"][0]["count"] = -1
    provider = drain(database, monkeypatch, [bad, CLASSIFICATION, INSIGHT, REVIEW])
    assert len(provider.calls) == 4
    with Session(database) as db:
        approval = pending(db, current)
        identity, digest = approval.id, approval.expected_payload_hash
        bad = deepcopy(INSIGHT)
        bad["feature_requests"][0]["count"] = -1
        with pytest.raises(HTTPException) as error:
            adapt(
                db,
                approval,
                "edit",
                HumanApprovalEdit(expected_payload_hash=digest, edited_analysis_json=bad),
            )
        assert error.value.status_code == 422
        db.refresh(approval)
        assert approval.status == "pending" and pending(db, current).id == identity
        assert approval.expected_payload_hash == digest


def test_quality_exhaustion_preserves_legacy_review_decision(database, monkeypatch):
    current, legacy = start(database)
    review = {
        **REVIEW,
        "approved": False,
        "quality_score": 0.3,
        "retry_recommended": True,
        "issues": [{"claim": "Checkout", "problem": "Verify evidence", "severity": "high"}],
    }
    with Session(database) as db:
        old = db.get(WorkflowRun, legacy)
        provider = LegacyProvider([CLASSIFICATION, INSIGHT, review])
        for agent in [
            run_customer_feedback_classifier,
            run_customer_feedback_insight,
            run_customer_feedback_reviewer,
        ]:
            agent(db, old, provider)
        assert old.status == "waiting_for_human"
    drain(database, monkeypatch, [CLASSIFICATION, INSIGHT, review] * 3)
    with Session(database) as db:
        old, new = pending(db, legacy), pending(db, current)
        assert old.issues_json == new.issues_json and old.reviewer_score == new.reviewer_score
        assert db.get(WorkflowRun, current).retry_count == 2
        human_approvals.reject_human_approval(db, old)
        adapt(
            db, new, "reject", HumanApprovalAction(expected_payload_hash=new.expected_payload_hash)
        )
        assert (
            db.get(WorkflowRun, legacy).status == db.get(WorkflowRun, current).status == "cancelled"
        )


def test_feedback_contracts_are_closed_and_nullable_fields_required():
    from src.schemas.workflow_graph import DataSchema
    from src.services.feedback_template import CLASSIFICATION, INSIGHT, REVIEW
    from src.services.llm_execution import provider_schema

    def check(schema):
        if schema["type"] == "object":
            assert set(schema["required"]) == set(schema["properties"])
            assert schema["additionalProperties"] is False
            for child in schema["properties"].values():
                check(child)
        if schema["type"] == "array":
            check(schema["items"])

    for schema in [CLASSIFICATION, INSIGHT, REVIEW]:
        check(provider_schema(DataSchema.model_validate(schema)))


def test_csv_start_backout_and_duplicate_controls(database, monkeypatch):
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
            uploaded = client.post(
                "/uploaded-inputs/upload",
                data={"title": "CSV", "input_type": "customer_feedback"},
                files={
                    "file": (
                        "feedback.csv",
                        "feedback,source\nSlow checkout,review-1\n"
                        "Please add bulk export,ticket-9\n",
                        "text/csv",
                    )
                },
            )
            assert uploaded.status_code == 201, uploaded.text
            source = uploaded.json()
            body = {"workflow_type": "customer_feedback", "input_id": source["id"]}
            assert client.post("/workflow-runs", json=body).status_code == 409
            installed = client.post("/workflow-definitions/templates/customer-feedback/install")
            assert installed.status_code == 200, installed.text
            assert all(item["name"].startswith("Customer feedback") for item in installed.json())
            assert (
                client.post("/workflow-definitions/templates/customer-feedback/install").json()
                == installed.json()
            )
            accepted = client.post("/workflow-runs", json=body)
            assert accepted.status_code == 201, accepted.text
            identity = accepted.json()["id"]
            for action in [
                "run-classifier",
                "run-insight",
                "run-reviewer",
                "run-writer",
                "run-baseline",
            ]:
                assert client.post(f"/workflow-runs/{identity}/{action}").status_code == 409
            provider = drain(database, monkeypatch, [CLASSIFICATION, INSIGHT, REVIEW])
            assert (
                json.loads(provider.calls[0]["messages"][0]["content"])["input"]["source"][
                    "raw_text"
                ]
                == source["raw_text"]
            )
            assert len(client.get(f"/workflow-runs/{identity}/agent-steps").json()) == 3
            monkeypatch.setattr(settings, "feedback_template_enabled", False)
            assert client.post("/workflow-runs", json=body).json()["execution_id"] is None
            assert client.post(f"/workflow-runs/{identity}/run-classifier").status_code == 409
            assert client.post(f"/workflow-runs/{identity}/cancel").status_code == 200
    finally:
        app.dependency_overrides.clear()
