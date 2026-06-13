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
from tests.test_incident_timeline_api import FakeSession, make_input, make_run

TIMELINE_OUTPUT = {
    "timeline": [
        {
            "time": "10:02 AM",
            "event": "API latency increased",
            "source_evidence": "10:02 AM - API latency increased",
        },
        {
            "time": "10:15 AM",
            "event": "Database connection pool saturated",
            "source_evidence": "10:15 AM - Database connection pool saturated",
        },
        {
            "time": "10:40 AM",
            "event": "Latency returned to normal",
            "source_evidence": "10:40 AM - Latency returned to normal",
        },
    ],
    "ambiguous_events": [],
}


class FakeRootCauseLLMClient:
    def __init__(
        self,
        invalid_output: bool = False,
        output_data: dict[str, Any] | None = None,
    ) -> None:
        self.invalid_output = invalid_output
        self.output_data = output_data
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
                data={"suspected_root_cause": "Database saturation"},
                model="gpt-root-test",
                usage=LLMUsage(input_tokens=120, output_tokens=80),
            )
        return StructuredResponse(
            data=self.output_data
            or {
                "impact": [
                    {
                        "description": "Customers experienced elevated API latency.",
                        "severity": "medium",
                        "affected_systems": ["api"],
                    }
                ],
                "suspected_root_cause": "Database connection pool saturation.",
                "confirmed_facts": [
                    {
                        "claim": "Database connection pool saturated at 10:15 AM.",
                        "support": "10:15 AM - Database connection pool saturated",
                    }
                ],
                "likely_causes": [
                    {
                        "claim": "Connection pool saturation likely contributed to latency.",
                        "support": "Latency increased before pool saturation was observed.",
                    }
                ],
                "inferred_claims": [
                    {
                        "claim": "Worker restart may have helped recovery.",
                        "support": "Latency returned to normal after operational response.",
                    }
                ],
                "unknowns": ["The log does not show why the pool saturated."],
                "follow_up_actions": [
                    {
                        "action": "Add connection pool saturation alerts.",
                        "owner": "platform",
                        "priority": "high",
                    }
                ],
            },
            model="gpt-root-test",
            usage=LLMUsage(input_tokens=120, output_tokens=80),
        )


def make_prompt() -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.root_cause,
        name="Root Cause Agent",
        version=1,
        template="Analyze incident root cause.",
        is_active=True,
        created_at=datetime.now(UTC),
    )


def make_timeline_step(run_id: uuid.UUID, output_json: dict[str, Any] | None = TIMELINE_OUTPUT):
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Timeline Agent",
        agent_type=AgentType.timeline.value,
        step_order=1,
        status=AgentStepStatus.completed,
        output_json=output_json,
        model="gpt-timeline-test",
        tokens_input=80,
        tokens_output=40,
        total_tokens=120,
        cost=0.000096,
        latency_ms=700,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def override_dependencies(db: FakeSession, llm: FakeRootCauseLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeRootCauseLLMClient()


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_run_incident_root_cause_success_creates_completed_step():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    timeline_step = make_timeline_step(run.id)
    llm = FakeRootCauseLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(timeline_step)
    db.prompts.append(make_prompt())
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-root-cause")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Root Cause Agent"
    assert body["agent_type"] == "root_cause"
    assert body["step_order"] == 2
    assert body["status"] == AgentStepStatus.completed
    assert body["input_json"]["timeline_step_id"] == str(timeline_step.id)
    assert body["output_json"]["suspected_root_cause"] == (
        "Database connection pool saturation."
    )
    assert body["output_json"]["likely_causes"][0]["claim"].startswith(
        "Connection pool saturation"
    )
    assert body["output_json"]["unknowns"] == [
        "The log does not show why the pool saturated."
    ]
    assert body["cost"] == pytest.approx(0.000176)
    assert run.status == WorkflowStatus.reviewer_running
    assert run.total_tokens == 320
    assert run.total_cost == pytest.approx(0.000272)
    assert "Separate confirmed facts" in llm.messages[0]["content"]
    assert llm.system == "Analyze incident root cause."
    clear_overrides()


def test_run_incident_root_cause_escalates_business_critical_impact():
    db = FakeSession()
    uploaded_input = make_input()
    uploaded_input.raw_text = (
        "10:02 AM - Checkout API latency increased for customers\n"
        "10:09 AM - Error rate increased and 2,300 checkout attempts affected\n"
        "10:40 AM - Latency returned to normal"
    )
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    output_data = {
        "impact": [
            {
                "description": "Checkout confirmation latency delayed customers.",
                "severity": "medium",
                "affected_systems": ["Checkout API"],
            }
        ],
        "suspected_root_cause": "Checkout retry policy overloaded a dependency.",
        "confirmed_facts": [
            {
                "claim": "Checkout API latency increased.",
                "support": "10:02 AM - Checkout API latency increased for customers",
            }
        ],
        "likely_causes": [
            {
                "claim": "Retry behavior likely contributed to the incident.",
                "support": "Error rate increased during checkout impact.",
            }
        ],
        "inferred_claims": [],
        "unknowns": ["Exact code change is unknown."],
        "follow_up_actions": [
            {
                "action": "Add checkout latency deployment guardrail.",
                "owner": "payments",
                "priority": "high",
            }
        ],
    }
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_timeline_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db, FakeRootCauseLLMClient(output_data=output_data))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-root-cause")

    assert response.status_code == 200
    assert response.json()["output_json"]["impact"][0]["severity"] == "high"
    clear_overrides()


def test_run_incident_root_cause_requires_running_workflow():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.created, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_timeline_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-root-cause")

    assert response.status_code == 422
    assert response.json()["detail"] == "Root cause agent can only run from running workflows"
    clear_overrides()


def test_run_incident_root_cause_rejects_non_incident_workflow():
    db = FakeSession()
    uploaded_input = make_input(InputType.sales_report)
    run = make_run(
        workflow_type=WorkflowType.sales_report,
        status=WorkflowStatus.running,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_timeline_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-root-cause")

    assert response.status_code == 422
    assert response.json()["detail"] == "Root cause agent only supports incident log workflows"
    clear_overrides()


def test_run_incident_root_cause_rejects_baseline_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(
        run_mode=RunMode.baseline,
        status=WorkflowStatus.running,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_timeline_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-root-cause")

    assert response.status_code == 422
    assert response.json()["detail"] == "Root cause agent only runs for multi-agent workflows"
    clear_overrides()


def test_run_incident_root_cause_requires_completed_timeline():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-root-cause")

    assert response.status_code == 422
    assert response.json()["detail"] == "Completed timeline step not found"
    clear_overrides()


def test_run_incident_root_cause_invalid_timeline_returns_422():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_timeline_step(run.id, output_json={"timeline": []}))
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-root-cause")

    assert response.status_code == 422
    assert response.json()["detail"] == "Completed timeline output is invalid"
    clear_overrides()


def test_run_incident_root_cause_invalid_output_fails_step_and_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_timeline_step(run.id))
    db.prompts.append(make_prompt())
    override_dependencies(db, FakeRootCauseLLMClient(invalid_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-root-cause")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert "impact" in body["error_message"]
    assert run.status == WorkflowStatus.failed
    clear_overrides()
