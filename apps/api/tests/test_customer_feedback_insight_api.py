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
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType
from src.models.workflow_run import RunMode, WorkflowStatus, WorkflowType
from src.services.llm_client import LLMUsage, StructuredResponse
from tests.test_customer_feedback_classifier_api import (
    FakeSession,
    make_input,
    make_run,
)

CLASSIFIER_OUTPUT = {
    "themes": [
        {
            "name": "performance",
            "count": 2,
            "sentiment": "negative",
            "examples": [
                {"text": "The mobile app is slow during checkout.", "source": "review-1"}
            ],
        },
        {
            "name": "feature_requests",
            "count": 1,
            "sentiment": "neutral",
            "examples": [{"text": "Please add bulk export.", "source": "ticket-9"}],
        },
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


class FakeLLMClient:
    def __init__(self, invalid_output: bool = False) -> None:
        self.invalid_output = invalid_output
        self.messages: list[dict[str, Any]] = []
        self.schema: dict[str, Any] | None = None
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
        self.schema = schema
        self.system = system
        if self.invalid_output:
            return StructuredResponse(
                data={"top_insights": ["Mobile performance is a top concern"]},
                model="gpt-test",
                usage=LLMUsage(input_tokens=140, output_tokens=90),
            )
        return StructuredResponse(
            data={
                "top_insights": [
                    "Mobile checkout performance is the strongest negative theme.",
                    "Bulk export is a recurring product request.",
                ],
                "customer_pain_points": ["Slow mobile checkout"],
                "feature_requests": [
                    {
                        "request": "Bulk export",
                        "count": 1,
                        "supporting_examples": [
                            {"text": "Please add bulk export.", "source": "ticket-9"}
                        ],
                    }
                ],
                "risks": ["Checkout slowdown may reduce mobile conversion."],
                "recommendations": [
                    {
                        "recommendation": "Prioritize mobile checkout performance work.",
                        "rationale": "Performance has the highest negative feedback count.",
                        "supporting_examples": [
                            {
                                "text": "The mobile app is slow during checkout.",
                                "source": "review-1",
                            }
                        ],
                    }
                ],
                "supporting_examples": [
                    {"text": "The mobile app is slow during checkout.", "source": "review-1"},
                    {"text": "Please add bulk export.", "source": "ticket-9"},
                ],
            },
            model="gpt-test",
            usage=LLMUsage(input_tokens=140, output_tokens=90),
        )


def make_prompt(is_active: bool = True) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.insight,
        name="Insight Agent",
        version=1,
        template="Create product insights from classified feedback.",
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


def make_classifier_step(
    run_id: uuid.UUID,
    *,
    output_json: dict[str, Any] | None = CLASSIFIER_OUTPUT,
    step_order: int = 1,
) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Customer Feedback Classifier Agent",
        agent_type=AgentType.classifier.value,
        step_order=step_order,
        status=AgentStepStatus.completed,
        output_json=output_json,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def override_dependencies(db: FakeSession, llm: FakeLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeLLMClient()


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_run_customer_feedback_insight_success_creates_completed_step():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    classifier_step = make_classifier_step(run.id)
    llm = FakeLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(classifier_step)
    db.prompts.append(make_prompt())
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-insight")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Customer Feedback Insight Agent"
    assert body["agent_type"] == "insight"
    assert body["status"] == AgentStepStatus.completed
    assert body["step_order"] == 2
    assert body["output_json"]["top_insights"][0] == (
        "Mobile checkout performance is the strongest negative theme."
    )
    assert body["output_json"]["recommendations"][0]["recommendation"] == (
        "Prioritize mobile checkout performance work."
    )
    assert body["model"] == "gpt-test"
    assert body["tokens_input"] == 140
    assert body["tokens_output"] == 90
    assert body["total_tokens"] == 230
    assert body["cost"] == pytest.approx(0.0002)
    assert body["prompt_version_id"] == str(db.prompts[0].id)
    assert body["input_json"]["classification"] == CLASSIFIER_OUTPUT
    assert run.status == WorkflowStatus.reviewer_running
    assert run.total_tokens == 230
    assert run.total_cost == pytest.approx(0.0002)
    assert len(db.cost_events) == 1
    assert "Classifier output JSON:" in llm.messages[0]["content"]
    assert llm.schema is not None
    assert llm.system == "Create product insights from classified feedback."
    clear_overrides()


def test_run_customer_feedback_insight_requires_running_workflow():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.created, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_classifier_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-insight")

    assert response.status_code == 422
    assert response.json()["detail"] == "Insight agent can only run from running workflows"
    clear_overrides()


def test_run_customer_feedback_insight_rejects_non_customer_feedback_workflow():
    db = FakeSession()
    uploaded_input = make_input(InputType.sales_report)
    run = make_run(
        workflow_type=WorkflowType.sales_report,
        status=WorkflowStatus.running,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_classifier_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-insight")

    assert response.status_code == 422
    assert response.json()["detail"] == "Insight agent only supports customer feedback workflows"
    clear_overrides()


def test_run_customer_feedback_insight_rejects_baseline_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(
        run_mode=RunMode.baseline,
        status=WorkflowStatus.running,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_classifier_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-insight")

    assert response.status_code == 422
    assert response.json()["detail"] == "Insight agent only runs for multi-agent workflows"
    clear_overrides()


def test_run_customer_feedback_insight_requires_completed_classifier_output():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-insight")

    assert response.status_code == 422
    assert response.json()["detail"] == "Completed classifier output not found"
    clear_overrides()


def test_run_customer_feedback_insight_rejects_invalid_classifier_output():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_classifier_step(run.id, output_json={"themes": []}))
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-insight")

    assert response.status_code == 422
    assert response.json()["detail"] == "Completed classifier output is invalid"
    clear_overrides()


def test_run_customer_feedback_insight_without_active_prompt_returns_422():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_classifier_step(run.id))
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-insight")

    assert response.status_code == 422
    assert response.json()["detail"] == "Active Insight prompt not found"
    clear_overrides()


def test_run_customer_feedback_insight_invalid_output_fails_step_and_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_classifier_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db, FakeLLMClient(invalid_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-insight")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert "customer_pain_points" in body["error_message"]
    assert run.status == WorkflowStatus.failed
    clear_overrides()
