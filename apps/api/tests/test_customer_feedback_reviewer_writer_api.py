import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.llm_client import LLMUsage, StructuredResponse, TextResponse
from tests.test_sales_analyst_api import FakeSession

PRODUCT_INSIGHT_OUTPUT = {
    "top_insights": [
        "Mobile checkout performance is the strongest negative theme.",
        "Bulk export is a recurring product request.",
    ],
    "customer_pain_points": ["Slow mobile checkout"],
    "feature_requests": [
        {
            "request": "Bulk export",
            "count": 1,
            "supporting_examples": [{"text": "Please add bulk export.", "source": "ticket-9"}],
        }
    ],
    "risks": ["Checkout slowdown may reduce mobile conversion."],
    "recommendations": [
        {
            "recommendation": "Prioritize mobile checkout performance work.",
            "rationale": "Performance has the highest negative feedback count.",
            "supporting_examples": [
                {"text": "The mobile app is slow during checkout.", "source": "review-1"}
            ],
        }
    ],
    "supporting_examples": [
        {"text": "The mobile app is slow during checkout.", "source": "review-1"},
        {"text": "Please add bulk export.", "source": "ticket-9"},
    ],
}

CLASSIFIER_OUTPUT = {
    "themes": [
        {
            "name": "performance",
            "count": 2,
            "sentiment": "negative",
            "examples": [
                {"text": "The mobile app is slow during checkout.", "source": "review-1"}
            ],
        }
    ],
    "sentiment_patterns": [
        {
            "sentiment": "negative",
            "count": 2,
            "summary": "Performance feedback is mostly negative.",
        }
    ],
    "feature_requests": [
        {
            "request": "Bulk export",
            "count": 1,
            "supporting_examples": [{"text": "Please add bulk export.", "source": "ticket-9"}],
        }
    ],
    "bug_reports": [
        {
            "issue": "Checkout slowdown",
            "count": 2,
            "severity": "medium",
            "supporting_examples": [
                {"text": "The mobile app is slow during checkout.", "source": "review-1"}
            ],
        }
    ],
}

REVIEWER_OUTPUT = {
    "approved": True,
    "quality_score": 0.91,
    "approval_rationale": (
        "The recommendations are supported by source feedback examples and no "
        "important feedback themes are missing."
    ),
    "passed_checks": [
        {
            "name": "Evidence support",
            "status": "passed",
            "rationale": "Each recommendation includes matching customer feedback.",
        },
        {
            "name": "Missing important feedback",
            "status": "passed",
            "rationale": "Bulk export and mobile performance feedback are represented.",
        },
    ],
    "issues": [],
    "retry_recommended": False,
}


class FakeReviewerLLMClient:
    def __init__(self, invalid_output: bool = False) -> None:
        self.invalid_output = invalid_output
        self.messages: list[dict[str, Any]] = []
        self.system: str | None = None

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        self.messages = messages
        self.system = system
        if self.invalid_output:
            return StructuredResponse(
                data={"approved": True},
                model="gpt-reviewer-test",
                usage=LLMUsage(input_tokens=90, output_tokens=30),
            )
        return StructuredResponse(
            data=REVIEWER_OUTPUT,
            model="gpt-reviewer-test",
            usage=LLMUsage(input_tokens=90, output_tokens=30),
        )


class FakeWriterLLMClient:
    def __init__(self, empty_output: bool = False) -> None:
        self.empty_output = empty_output
        self.messages: list[dict[str, Any]] = []
        self.system: str | None = None

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> TextResponse:
        self.messages = messages
        self.system = system
        return TextResponse(
            content="" if self.empty_output else "Product Insights Report\nImprove checkout.",
            model="gpt-writer-test",
            usage=LLMUsage(input_tokens=130, output_tokens=70),
        )


class FakeEndToEndLLMClient:
    def __init__(self) -> None:
        self.structured_calls = 0

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        self.structured_calls += 1
        if self.structured_calls == 1:
            data = CLASSIFIER_OUTPUT
            usage = LLMUsage(input_tokens=100, output_tokens=60)
        elif self.structured_calls == 2:
            data = PRODUCT_INSIGHT_OUTPUT
            usage = LLMUsage(input_tokens=120, output_tokens=70)
        else:
            data = REVIEWER_OUTPUT
            usage = LLMUsage(input_tokens=90, output_tokens=30)
        return StructuredResponse(data=data, model="gpt-e2e-test", usage=usage)

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> TextResponse:
        return TextResponse(
            content="Product Insights Report\nImprove mobile checkout and add bulk export.",
            model="gpt-e2e-test",
            usage=LLMUsage(input_tokens=130, output_tokens=70),
        )


def make_customer_feedback_input() -> UploadedInput:
    return UploadedInput(
        id=uuid.uuid4(),
        title="Customer Feedback Batch",
        input_type=InputType.customer_feedback,
        raw_text="Review 1: The mobile app is slow. Ticket 9: Please add bulk export.",
        notes="Q1 feedback",
        created_at=datetime.now(UTC),
    )


def make_run(
    *,
    status: WorkflowStatus,
    input_id: uuid.UUID,
    run_mode: RunMode = RunMode.multi_agent,
) -> WorkflowRun:
    return WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.customer_feedback,
        run_mode=run_mode,
        status=status,
        input_id=input_id,
        retry_count=0,
        created_at=datetime.now(UTC),
    )


def make_prompt(agent_type: AgentType) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=agent_type,
        name=f"{agent_type.value.title()} Agent",
        version=1,
        template=f"Run {agent_type.value}.",
        is_active=True,
        created_at=datetime.now(UTC),
    )


def make_completed_insight_step(run_id: uuid.UUID) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Customer Feedback Insight Agent",
        agent_type=AgentType.insight.value,
        step_order=2,
        status=AgentStepStatus.completed,
        output_json=PRODUCT_INSIGHT_OUTPUT,
        model="gpt-insight-test",
        tokens_input=140,
        tokens_output=90,
        total_tokens=230,
        cost=0.0002,
        latency_ms=900,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def make_completed_reviewer_step(run_id: uuid.UUID) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Reviewer Agent",
        agent_type=AgentType.reviewer.value,
        step_order=3,
        status=AgentStepStatus.completed,
        output_json={
            **REVIEWER_OUTPUT,
        },
        model="gpt-reviewer-test",
        tokens_input=90,
        tokens_output=30,
        total_tokens=120,
        cost=0.000084,
        latency_ms=700,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def make_approved_human_approval(
    run_id: uuid.UUID,
    edited_analysis_json: dict[str, Any] | None = None,
) -> HumanApproval:
    return HumanApproval(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        reviewer_score=0.91,
        issues_json=[],
        status=ApprovalStatus.approved,
        human_feedback="Keep it concise.",
        edited_analysis_json=edited_analysis_json,
        created_at=datetime.now(UTC),
        resolved_at=datetime.now(UTC),
    )


def override_dependencies(
    db: FakeSession,
    llm: FakeReviewerLLMClient | FakeWriterLLMClient | None = None,
) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeReviewerLLMClient()


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_run_customer_feedback_reviewer_creates_review_and_pending_approval():
    db = FakeSession()
    uploaded_input = make_customer_feedback_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    insight_step = make_completed_insight_step(run.id)
    llm = FakeReviewerLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(insight_step)
    db.prompts.append(make_prompt(AgentType.reviewer))
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Reviewer Agent"
    assert body["agent_type"] == "reviewer"
    assert body["step_order"] == 3
    assert body["status"] == AgentStepStatus.completed
    assert body["input_json"]["insight_step_id"] == str(insight_step.id)
    assert body["output_json"]["quality_score"] == 0.91
    assert body["output_json"]["approval_rationale"].startswith(
        "The recommendations are supported",
    )
    assert body["output_json"]["passed_checks"][0]["name"] == "Evidence support"
    assert body["cost"] == pytest.approx(0.000084)
    assert run.status == WorkflowStatus.waiting_for_human
    assert run.quality_score == 0.91
    assert run.total_tokens == 350
    assert run.total_cost == pytest.approx(0.000284)
    assert len(db.approvals) == 1
    assert db.approvals[0].status == ApprovalStatus.pending
    assert db.approvals[0].reviewer_score == 0.91
    assert "supported by actual feedback examples" in llm.messages[0]["content"]
    assert "approval rationale" in llm.messages[0]["content"]
    assert "missing important feedback" in llm.messages[0]["content"]
    clear_overrides()


def test_run_customer_feedback_reviewer_requires_completed_insight():
    db = FakeSession()
    uploaded_input = make_customer_feedback_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt(AgentType.reviewer))
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Completed insight step not found"
    clear_overrides()


def test_run_customer_feedback_reviewer_invalid_output_fails_step_and_run():
    db = FakeSession()
    uploaded_input = make_customer_feedback_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_insight_step(run.id))
    db.prompts.append(make_prompt(AgentType.reviewer))
    override_dependencies(db, FakeReviewerLLMClient(invalid_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert "quality_score" in body["error_message"]
    assert run.status == WorkflowStatus.failed
    clear_overrides()


def test_run_customer_feedback_writer_completes_workflow_and_stores_report():
    db = FakeSession()
    uploaded_input = make_customer_feedback_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    insight_step = make_completed_insight_step(run.id)
    reviewer_step = make_completed_reviewer_step(run.id)
    llm = FakeWriterLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend([insight_step, reviewer_step])
    db.approvals.append(make_approved_human_approval(run.id))
    db.prompts.append(make_prompt(AgentType.writer))
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Writer Agent"
    assert body["agent_type"] == "writer"
    assert body["step_order"] == 4
    assert body["status"] == AgentStepStatus.completed
    assert body["output_json"]["final_output"] == "Product Insights Report\nImprove checkout."
    assert body["input_json"]["insights"] == PRODUCT_INSIGHT_OUTPUT
    assert body["cost"] == pytest.approx(0.000164)
    assert run.final_output == "Product Insights Report\nImprove checkout."
    assert run.status == WorkflowStatus.completed
    assert run.total_tokens == 550
    assert run.total_cost == pytest.approx(0.000448)
    assert "product insights report" in llm.messages[0]["content"]
    assert "Executive Summary" in llm.messages[0]["content"]
    assert "Priority Table" in llm.messages[0]["content"]
    assert "SSO as Enterprise blocker" in llm.messages[0]["content"]
    assert "generated from human-approved" in llm.messages[0]["content"]
    clear_overrides()


def test_run_customer_feedback_writer_prefers_human_edited_insights():
    db = FakeSession()
    uploaded_input = make_customer_feedback_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    edited_insights = {
        **PRODUCT_INSIGHT_OUTPUT,
        "top_insights": ["Mobile checkout performance is the corrected top priority."],
    }
    llm = FakeWriterLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend([make_completed_insight_step(run.id), make_completed_reviewer_step(run.id)])
    db.approvals.append(make_approved_human_approval(run.id, edited_insights))
    db.prompts.append(make_prompt(AgentType.writer))
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 200
    body = response.json()
    assert body["input_json"]["insights_source"] == "human_edited"
    assert body["input_json"]["insights"] == edited_insights
    assert "corrected top priority" in llm.messages[0]["content"]
    clear_overrides()


def test_run_customer_feedback_writer_requires_approved_review_or_human_approval():
    db = FakeSession()
    uploaded_input = make_customer_feedback_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_insight_step(run.id))
    db.prompts.append(make_prompt(AgentType.writer))
    override_dependencies(db, FakeWriterLLMClient())
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Writer requires approved human approval or reviewer approval"
    )
    clear_overrides()


def test_customer_feedback_workflow_runs_end_to_end_through_writer():
    db = FakeSession()
    uploaded_input = make_customer_feedback_input()
    run = make_run(status=WorkflowStatus.created, input_id=uploaded_input.id)
    llm = FakeEndToEndLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.extend(
        [
            make_prompt(AgentType.classifier),
            make_prompt(AgentType.insight),
            make_prompt(AgentType.reviewer),
            make_prompt(AgentType.writer),
        ]
    )
    override_dependencies(db, llm)
    client = TestClient(app)

    classifier_response = client.post(f"/workflow-runs/{run.id}/run-classifier")
    insight_response = client.post(f"/workflow-runs/{run.id}/run-insight")
    reviewer_response = client.post(f"/workflow-runs/{run.id}/run-reviewer")
    approval_response = client.post(
        f"/human-approvals/{db.approvals[0].id}/approve",
        json={"human_feedback": "Approved for product leadership."},
    )
    writer_response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert classifier_response.status_code == 200
    assert insight_response.status_code == 200
    assert reviewer_response.status_code == 200
    assert approval_response.status_code == 200
    assert writer_response.status_code == 200
    assert [step.agent_type for step in db.steps] == [
        AgentType.classifier.value,
        AgentType.insight.value,
        AgentType.reviewer.value,
        AgentType.writer.value,
    ]
    assert run.status == WorkflowStatus.completed
    assert run.final_output == (
        "Product Insights Report\nImprove mobile checkout and add bulk export."
    )
    assert run.quality_score == 0.91
    assert run.total_tokens == 670
    assert db.approvals[0].status == ApprovalStatus.approved
    clear_overrides()
