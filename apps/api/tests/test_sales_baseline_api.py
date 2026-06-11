from typing import Any

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.uploaded_input import InputType
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowStatus, WorkflowType
from src.services.llm_client import LLMUsage, TextResponse
from src.services.sales_baseline import SALES_BASELINE_AGENT_TYPE
from tests.test_sales_analyst_api import (
    FakeSession,
    clear_overrides,
    make_input,
    make_run,
)


class FakeBaselineLLMClient:
    def __init__(self, should_fail: bool = False, empty_output: bool = False) -> None:
        self.should_fail = should_fail
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
        if self.should_fail:
            raise RuntimeError("LLM unavailable")
        return TextResponse(
            content="" if self.empty_output else "Executive Summary\nRevenue increased 12%.",
            model="gpt-baseline-test",
            usage=LLMUsage(input_tokens=90, output_tokens=45),
        )


def override_dependencies(db: FakeSession, llm: FakeBaselineLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeBaselineLLMClient()


def test_run_sales_baseline_success_completes_workflow_without_approvals():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(
        run_mode=RunMode.baseline,
        status=WorkflowStatus.created,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    llm = FakeBaselineLLMClient()
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-baseline")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Baseline Agent"
    assert body["agent_type"] == SALES_BASELINE_AGENT_TYPE
    assert body["status"] == AgentStepStatus.completed
    assert body["output_json"] == {
        "final_output": "Executive Summary\nRevenue increased 12%."
    }
    assert body["prompt_version_id"] is None
    assert body["retry_count"] == 0
    assert run.status == WorkflowStatus.completed
    assert run.final_output == "Executive Summary\nRevenue increased 12%."
    assert run.total_tokens == 135
    assert len(db.steps) == 1
    assert len(db.approvals) == 0
    assert len(db.cost_events) == 1
    assert db.cost_events[0].agent_step_id == db.steps[0].id
    assert [event.event_type for event in db.workflow_events] == [
        WorkflowEventType.agent_started,
        WorkflowEventType.agent_completed,
        WorkflowEventType.workflow_completed,
    ]
    assert "single-agent baseline" in (llm.system or "")
    clear_overrides()


def test_run_sales_baseline_requires_baseline_run_mode():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.created, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    llm = FakeBaselineLLMClient()
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-baseline")

    assert response.status_code == 422
    assert response.json()["detail"] == "Baseline only runs for baseline workflows"
    clear_overrides()


def test_run_baseline_supports_customer_feedback_workflow():
    db = FakeSession()
    uploaded_input = make_input(InputType.customer_feedback)
    run = make_run(
        workflow_type=WorkflowType.customer_feedback,
        run_mode=RunMode.baseline,
        status=WorkflowStatus.created,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    llm = FakeBaselineLLMClient()
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-baseline")

    assert response.status_code == 200
    assert run.status == WorkflowStatus.completed
    assert "Customer feedback:" in llm.messages[0]["content"]
    assert "product insights report" in (llm.system or "")
    clear_overrides()


def test_run_sales_baseline_rejects_unsupported_workflow():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(
        workflow_type=WorkflowType.incident_log,
        run_mode=RunMode.baseline,
        status=WorkflowStatus.created,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-baseline")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Baseline only supports sales report and customer feedback workflows"
    )
    clear_overrides()


def test_run_sales_baseline_rejects_duplicate_completed_baseline():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(
        run_mode=RunMode.baseline,
        status=WorkflowStatus.created,
        input_id=uploaded_input.id,
    )
    completed_step = AgentStep(
        workflow_run_id=run.id,
        agent_name="Baseline Agent",
        agent_type=SALES_BASELINE_AGENT_TYPE,
        step_order=1,
        status=AgentStepStatus.completed,
        retry_count=0,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(completed_step)
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-baseline")

    assert response.status_code == 422
    assert response.json()["detail"] == "Baseline already completed for workflow run"
    clear_overrides()


def test_run_sales_baseline_llm_failure_creates_failed_step_and_fails_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(
        run_mode=RunMode.baseline,
        status=WorkflowStatus.created,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    override_dependencies(db, FakeBaselineLLMClient(should_fail=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-baseline")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert body["error_message"] == "LLM unavailable"
    assert run.status == WorkflowStatus.failed
    assert [event.event_type for event in db.workflow_events] == [
        WorkflowEventType.agent_started,
        WorkflowEventType.agent_failed,
        WorkflowEventType.workflow_failed,
    ]
    clear_overrides()
