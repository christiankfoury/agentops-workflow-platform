import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_step import AgentStepStatus
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.llm_client import LLMUsage, StructuredResponse
from tests.test_customer_feedback_classifier_api import FakeSession


class FakeTimelineLLMClient:
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
                data={"timeline": [{"time": "10:02"}]},
                model="gpt-timeline-test",
                usage=LLMUsage(input_tokens=80, output_tokens=40),
            )
        return StructuredResponse(
            data={
                "timeline": [
                    {
                        "time": "10:02 AM",
                        "event": "API latency increased",
                        "source_evidence": "10:02 AM - API latency increased",
                    },
                    {
                        "time": "10:40 AM",
                        "event": "Latency returned to normal",
                        "source_evidence": "10:40 AM - Latency returned to normal",
                    },
                ],
                "ambiguous_events": ["Customer impact was not explicitly timestamped."],
            },
            model="gpt-timeline-test",
            usage=LLMUsage(input_tokens=80, output_tokens=40),
        )


def make_run(
    *,
    workflow_type: WorkflowType = WorkflowType.incident_log,
    run_mode: RunMode = RunMode.multi_agent,
    status: WorkflowStatus = WorkflowStatus.created,
    input_id: uuid.UUID | None = None,
) -> WorkflowRun:
    return WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=workflow_type,
        run_mode=run_mode,
        status=status,
        input_id=input_id,
        retry_count=0,
        created_at=datetime.now(UTC),
    )


def make_input(input_type: InputType = InputType.incident_log) -> UploadedInput:
    return UploadedInput(
        id=uuid.uuid4(),
        title="API Latency Incident",
        input_type=input_type,
        raw_text=(
            "10:02 AM - API latency increased\n"
            "10:15 AM - Database connection pool saturated\n"
            "10:40 AM - Latency returned to normal"
        ),
        notes="Production incident",
        created_at=datetime.now(UTC),
    )


def make_prompt() -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.timeline,
        name="Timeline Agent",
        version=1,
        template="Extract incident timelines.",
        is_active=True,
        created_at=datetime.now(UTC),
    )


def override_dependencies(db: FakeSession, llm: FakeTimelineLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeTimelineLLMClient()


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_run_incident_timeline_success_creates_completed_step():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    llm = FakeTimelineLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-timeline")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Timeline Agent"
    assert body["agent_type"] == "timeline"
    assert body["status"] == AgentStepStatus.completed
    assert body["output_json"]["timeline"][0]["time"] == "10:02 AM"
    assert body["output_json"]["timeline"][1]["event"] == "Latency returned to normal"
    assert body["output_json"]["ambiguous_events"] == [
        "Customer impact was not explicitly timestamped."
    ]
    assert body["model"] == "gpt-timeline-test"
    assert body["tokens_input"] == 80
    assert body["tokens_output"] == 40
    assert body["total_tokens"] == 120
    assert body["cost"] == pytest.approx(0.000096)
    assert body["prompt_version_id"] == str(db.prompts[0].id)
    assert run.status == WorkflowStatus.running
    assert run.total_tokens == 120
    assert run.total_cost == pytest.approx(0.000096)
    assert "Incident log:" in llm.messages[0]["content"]
    assert llm.schema is not None
    assert llm.system == "Extract incident timelines."
    clear_overrides()


def test_run_incident_timeline_rejects_non_incident_workflow():
    db = FakeSession()
    uploaded_input = make_input(InputType.sales_report)
    run = make_run(workflow_type=WorkflowType.sales_report, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-timeline")

    assert response.status_code == 422
    assert response.json()["detail"] == "Timeline agent only supports incident log workflows"
    clear_overrides()


def test_run_incident_timeline_rejects_baseline_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(run_mode=RunMode.baseline, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-timeline")

    assert response.status_code == 422
    assert response.json()["detail"] == "Timeline agent only runs for multi-agent workflows"
    clear_overrides()


def test_run_incident_timeline_without_active_prompt_returns_422():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-timeline")

    assert response.status_code == 422
    assert response.json()["detail"] == "Active Timeline prompt not found"
    clear_overrides()


def test_run_incident_timeline_invalid_output_fails_step_and_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db, FakeTimelineLLMClient(invalid_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-timeline")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert "event" in body["error_message"]
    assert run.status == WorkflowStatus.failed
    clear_overrides()
