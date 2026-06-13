import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.prompt_version import PromptVersion
from src.models.workflow_run import WorkflowStatus
from src.services.llm_client import LLMUsage, StructuredResponse, TextResponse
from tests.test_incident_root_cause_api import TIMELINE_OUTPUT, make_input, make_run
from tests.test_sales_analyst_api import FakeSession

ROOT_CAUSE_OUTPUT = {
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
}


class FakeIncidentLLMClient:
    def __init__(
        self,
        empty_writer_output: bool = False,
        reviewer_quality_score: float = 0.9,
    ) -> None:
        self.empty_writer_output = empty_writer_output
        self.reviewer_quality_score = reviewer_quality_score
        self.structured_calls = 0
        self.messages: list[dict[str, Any]] = []

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        self.structured_calls += 1
        self.messages = messages
        if "timeline" in schema["required"]:
            data = TIMELINE_OUTPUT
            usage = LLMUsage(input_tokens=80, output_tokens=40)
        elif "suspected_root_cause" in schema["required"]:
            data = ROOT_CAUSE_OUTPUT
            usage = LLMUsage(input_tokens=120, output_tokens=80)
        else:
            data = {
                "approved": True,
                "quality_score": self.reviewer_quality_score,
                "issues": [],
                "retry_recommended": False,
            }
            usage = LLMUsage(input_tokens=100, output_tokens=30)
        return StructuredResponse(data=data, model="gpt-incident-test", usage=usage)

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> TextResponse:
        self.messages = messages
        return TextResponse(
            content="" if self.empty_writer_output else "Incident Report\nAPI latency recovered.",
            model="gpt-incident-test",
            usage=LLMUsage(input_tokens=140, output_tokens=70),
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


def make_step(run_id: uuid.UUID, agent_type: AgentType, output_json: dict[str, Any]) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name=f"{agent_type.value.title()} Agent",
        agent_type=agent_type.value,
        step_order=1 if agent_type == AgentType.timeline else 2,
        status=AgentStepStatus.completed,
        output_json=output_json,
        model="gpt-incident-test",
        tokens_input=80,
        tokens_output=40,
        total_tokens=120,
        cost=0.000096,
        latency_ms=700,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def make_reviewer_step(run_id: uuid.UUID) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Reviewer Agent",
        agent_type=AgentType.reviewer.value,
        step_order=3,
        status=AgentStepStatus.completed,
        output_json={
            "approved": True,
            "quality_score": 0.9,
            "issues": [],
            "retry_recommended": False,
        },
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def make_approval(run_id: uuid.UUID) -> HumanApproval:
    return HumanApproval(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        reviewer_score=0.9,
        issues_json=[],
        status=ApprovalStatus.approved,
        human_feedback="Approved.",
        created_at=datetime.now(UTC),
        resolved_at=datetime.now(UTC),
    )


def override_dependencies(db: FakeSession, llm: FakeIncidentLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeIncidentLLMClient()


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_run_incident_reviewer_creates_review_and_pending_approval():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend(
        [
            make_step(run.id, AgentType.timeline, TIMELINE_OUTPUT),
            make_step(run.id, AgentType.root_cause, ROOT_CAUSE_OUTPUT),
        ]
    )
    db.prompts.append(make_prompt(AgentType.reviewer))
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_type"] == "reviewer"
    assert body["input_json"]["root_cause_step_id"] == str(db.steps[1].id)
    assert body["output_json"]["quality_score"] == 0.9
    assert run.status == WorkflowStatus.waiting_for_human
    assert run.quality_score == 0.9
    assert len(db.approvals) == 1
    assert db.approvals[0].status == ApprovalStatus.pending
    clear_overrides()


def test_run_incident_reviewer_caps_perfect_score_when_unknowns_remain():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.reviewer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend(
        [
            make_step(run.id, AgentType.timeline, TIMELINE_OUTPUT),
            make_step(run.id, AgentType.root_cause, ROOT_CAUSE_OUTPUT),
        ]
    )
    db.prompts.append(make_prompt(AgentType.reviewer))
    override_dependencies(db, FakeIncidentLLMClient(reviewer_quality_score=1.0))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-reviewer")

    assert response.status_code == 200
    assert response.json()["output_json"]["quality_score"] == 0.95
    assert run.quality_score == 0.95
    clear_overrides()


def test_run_incident_writer_completes_workflow_and_stores_report():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    llm = FakeIncidentLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend(
        [
            make_step(run.id, AgentType.timeline, TIMELINE_OUTPUT),
            make_step(run.id, AgentType.root_cause, ROOT_CAUSE_OUTPUT),
            make_reviewer_step(run.id),
        ]
    )
    db.approvals.append(make_approval(run.id))
    db.prompts.append(make_prompt(AgentType.writer))
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_type"] == "writer"
    assert body["output_json"]["final_output"] == "Incident Report\nAPI latency recovered."
    assert run.status == WorkflowStatus.completed
    assert run.final_output == "Incident Report\nAPI latency recovered."
    assert "Executive Summary" in llm.messages[0]["content"]
    assert "strongly support the deployment as the likely cause" in llm.messages[0]["content"]
    clear_overrides()


def test_incident_workflow_runs_end_to_end_through_writer():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.extend(
        [
            make_prompt(AgentType.timeline),
            make_prompt(AgentType.root_cause),
            make_prompt(AgentType.reviewer),
            make_prompt(AgentType.writer),
        ]
    )
    override_dependencies(db, FakeIncidentLLMClient())
    client = TestClient(app)

    timeline_response = client.post(f"/workflow-runs/{run.id}/run-timeline")
    root_response = client.post(f"/workflow-runs/{run.id}/run-root-cause")
    reviewer_response = client.post(f"/workflow-runs/{run.id}/run-reviewer")
    approval_response = client.post(f"/human-approvals/{db.approvals[0].id}/approve")
    writer_response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert timeline_response.status_code == 200
    assert root_response.status_code == 200
    assert reviewer_response.status_code == 200
    assert approval_response.status_code == 200
    assert writer_response.status_code == 200
    assert [step.agent_type for step in db.steps] == [
        "timeline",
        "root_cause",
        "reviewer",
        "writer",
    ]
    assert run.status == WorkflowStatus.completed
    assert run.final_output == "Incident Report\nAPI latency recovered."
    assert run.quality_score == 0.9
    clear_overrides()


def test_run_incident_writer_empty_output_fails_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend(
        [
            make_step(run.id, AgentType.timeline, TIMELINE_OUTPUT),
            make_step(run.id, AgentType.root_cause, ROOT_CAUSE_OUTPUT),
            make_reviewer_step(run.id),
        ]
    )
    db.approvals.append(make_approval(run.id))
    db.prompts.append(make_prompt(AgentType.writer))
    override_dependencies(db, FakeIncidentLLMClient(empty_writer_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 200
    assert response.json()["status"] == AgentStepStatus.failed
    assert run.status == WorkflowStatus.failed
    clear_overrides()
