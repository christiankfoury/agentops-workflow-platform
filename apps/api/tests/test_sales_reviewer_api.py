import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.models.workflow_run import WorkflowStatus
from src.services.llm_client import LLMUsage, StructuredResponse
from tests.test_sales_analyst_api import (
    FakeSession,
    clear_overrides,
    make_input,
    make_run,
)


class FakeReviewerLLMClient:
    def __init__(self, should_fail: bool = False, invalid_output: bool = False) -> None:
        self.should_fail = should_fail
        self.invalid_output = invalid_output

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        if self.should_fail:
            raise RuntimeError("LLM unavailable")
        if self.invalid_output:
            return StructuredResponse(
                data={"approved": True},
                model="gpt-reviewer-test",
                usage=LLMUsage(input_tokens=80, output_tokens=20),
            )
        return StructuredResponse(
            data={
                "approved": False,
                "quality_score": 0.78,
                "issues": [
                    {
                        "claim": "Enterprise churn doubled",
                        "problem": "Source only says churn increased",
                        "severity": "high",
                    }
                ],
                "retry_recommended": True,
            },
            model="gpt-reviewer-test",
            usage=LLMUsage(input_tokens=80, output_tokens=20),
        )


def make_reviewer_prompt(is_active: bool = True) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.reviewer,
        name="Reviewer Agent",
        version=1,
        template="Review sales analysis.",
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


def make_completed_analyst_step(run_id: uuid.UUID) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Sales Analyst Agent",
        agent_type=AgentType.analyst.value,
        step_order=1,
        status=AgentStepStatus.completed,
        output_json={
            "key_findings": ["Revenue increased 12%"],
            "risks": ["Enterprise churn increased"],
            "opportunities": ["Analytics Suite growth remains strong"],
            "recommendations": ["Prioritize enterprise retention"],
            "supporting_evidence": ["Revenue increased from $4.2M to $4.7M"],
        },
        model="gpt-analyst-test",
        tokens_input=100,
        tokens_output=50,
        total_tokens=150,
        latency_ms=1200,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def override_dependencies(
    db: FakeSession, llm: FakeReviewerLLMClient | None = None
) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeReviewerLLMClient()


def test_run_sales_reviewer_success_creates_completed_step():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    analyst_step = make_completed_analyst_step(run.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(analyst_step)
    db.prompts.append(make_reviewer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Reviewer Agent"
    assert body["agent_type"] == "reviewer"
    assert body["step_order"] == 2
    assert body["status"] == AgentStepStatus.completed
    assert body["output_json"]["quality_score"] == 0.78
    assert body["output_json"]["retry_recommended"] is True
    assert body["model"] == "gpt-reviewer-test"
    assert body["tokens_input"] == 80
    assert body["tokens_output"] == 20
    assert body["total_tokens"] == 100
    assert body["prompt_version_id"] == str(db.prompts[0].id)
    assert run.status == WorkflowStatus.waiting_for_human
    assert run.quality_score == 0.78
    assert run.total_tokens == 250
    assert run.latency_ms is not None
    clear_overrides()


def test_run_sales_reviewer_missing_workflow_returns_404():
    db = FakeSession()
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{uuid.uuid4()}/run-reviewer")

    assert response.status_code == 404
    clear_overrides()


def test_run_sales_reviewer_rejects_run_before_analyst_completion():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.created, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_reviewer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Reviewer can only run after analyst completion"
    clear_overrides()


def test_run_sales_reviewer_requires_completed_analyst_step():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_reviewer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Completed analyst step not found"
    clear_overrides()


def test_run_sales_reviewer_without_active_prompt_returns_422():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_analyst_step(run.id))
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Active Reviewer prompt not found"
    clear_overrides()


def test_run_sales_reviewer_llm_failure_creates_failed_step_and_fails_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_analyst_step(run.id))
    db.prompts.append(make_reviewer_prompt())
    override_dependencies(db, FakeReviewerLLMClient(should_fail=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert body["error_message"] == "LLM unavailable"
    assert run.status == WorkflowStatus.failed
    clear_overrides()


def test_run_sales_reviewer_invalid_output_creates_failed_step_and_fails_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_analyst_step(run.id))
    db.prompts.append(make_reviewer_prompt())
    override_dependencies(db, FakeReviewerLLMClient(invalid_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert "quality_score" in body["error_message"]
    assert run.status == WorkflowStatus.failed
    clear_overrides()
