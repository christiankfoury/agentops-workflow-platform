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
from src.models.workflow_run import RunMode, WorkflowStatus, WorkflowType
from src.services.llm_client import LLMUsage, TextResponse
from tests.test_sales_analyst_api import (
    FakeSession,
    clear_overrides,
    make_input,
    make_run,
)
from tests.test_sales_reviewer_api import make_completed_analyst_step


class FakeWriterLLMClient:
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
            model="gpt-writer-test",
            usage=LLMUsage(input_tokens=120, output_tokens=60),
        )


def make_writer_prompt(is_active: bool = True) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.writer,
        name="Writer Agent",
        version=1,
        template="Write executive summaries.",
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


def make_completed_reviewer_step(run_id: uuid.UUID) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Reviewer Agent",
        agent_type=AgentType.reviewer.value,
        step_order=2,
        status=AgentStepStatus.completed,
        output_json={
            "approved": True,
            "quality_score": 0.92,
            "issues": [],
            "retry_recommended": False,
        },
        model="gpt-reviewer-test",
        tokens_input=80,
        tokens_output=20,
        total_tokens=100,
        cost=0.000064,
        latency_ms=800,
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
        reviewer_score=0.92,
        issues_json=[],
        status=ApprovalStatus.approved,
        human_feedback="Use concise leadership language.",
        edited_analysis_json=edited_analysis_json,
        created_at=datetime.now(UTC),
        resolved_at=datetime.now(UTC),
    )


def override_dependencies(db: FakeSession, llm: FakeWriterLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeWriterLLMClient()


def test_run_sales_writer_success_completes_workflow_and_stores_final_output():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    analyst_step = make_completed_analyst_step(run.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend([analyst_step, make_completed_reviewer_step(run.id)])
    db.approvals.append(make_approved_human_approval(run.id))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Writer Agent"
    assert body["agent_type"] == "writer"
    assert body["step_order"] == 3
    assert body["status"] == AgentStepStatus.completed
    assert body["output_json"]["final_output"] == "Executive Summary\nRevenue increased 12%."
    assert body["model"] == "gpt-writer-test"
    assert body["tokens_input"] == 120
    assert body["tokens_output"] == 60
    assert body["total_tokens"] == 180
    assert body["cost"] == pytest.approx(0.000144)
    assert body["prompt_version_id"] == str(db.prompts[0].id)
    assert run.final_output == "Executive Summary\nRevenue increased 12%."
    assert run.status == WorkflowStatus.completed
    assert run.completed_at is not None
    assert run.total_tokens == 430
    assert run.total_cost == pytest.approx(0.000328)
    assert len(db.cost_events) == 1
    assert db.cost_events[0].agent_step_id == db.steps[-1].id
    assert run.latency_ms is not None
    clear_overrides()


def test_run_sales_writer_prefers_human_edited_analysis():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    edited_analysis = {
        "key_findings": ["Revenue increased 12% after finance correction"],
        "risks": ["Enterprise churn increased"],
        "opportunities": ["Analytics Suite growth remains strong"],
        "recommendations": ["Prioritize enterprise retention"],
        "supporting_evidence": ["Revenue increased from $4.2M to $4.7M"],
    }
    llm = FakeWriterLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend([make_completed_analyst_step(run.id), make_completed_reviewer_step(run.id)])
    db.approvals.append(make_approved_human_approval(run.id, edited_analysis))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 200
    body = response.json()
    assert body["input_json"]["analysis_source"] == "human_edited"
    assert body["input_json"]["analysis"] == edited_analysis
    assert "Revenue increased 12% after finance correction" in llm.messages[0]["content"]
    clear_overrides()


def test_run_sales_writer_rejects_before_approval():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.waiting_for_human, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_analyst_step(run.id))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Writer can only run after approval"
    clear_overrides()


def test_run_sales_writer_requires_approved_human_or_reviewer_approval():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_analyst_step(run.id))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Writer requires approved human approval or reviewer approval"
    )
    clear_overrides()


def test_run_sales_writer_rejects_duplicate_completed_writer():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    completed_writer = AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run.id,
        agent_name="Writer Agent",
        agent_type=AgentType.writer.value,
        step_order=3,
        status=AgentStepStatus.completed,
        output_json={"final_output": "Existing summary"},
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend(
        [
            make_completed_analyst_step(run.id),
            make_completed_reviewer_step(run.id),
            completed_writer,
        ]
    )
    db.approvals.append(make_approved_human_approval(run.id))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Writer already completed for workflow run"
    clear_overrides()


def test_run_sales_writer_rejects_baseline_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(
        run_mode=RunMode.baseline,
        status=WorkflowStatus.writer_running,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_analyst_step(run.id))
    db.approvals.append(make_approved_human_approval(run.id))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Writer only runs for multi-agent workflows"
    clear_overrides()


def test_run_sales_writer_rejects_non_sales_workflow():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(
        workflow_type=WorkflowType.incident_log,
        status=WorkflowStatus.writer_running,
        input_id=uploaded_input.id,
    )
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(make_completed_analyst_step(run.id))
    db.approvals.append(make_approved_human_approval(run.id))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Writer only supports sales report workflows"
    clear_overrides()


def test_run_sales_writer_without_active_prompt_returns_422():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend([make_completed_analyst_step(run.id), make_completed_reviewer_step(run.id)])
    db.approvals.append(make_approved_human_approval(run.id))
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 422
    assert response.json()["detail"] == "Active Writer prompt not found"
    clear_overrides()


def test_run_sales_writer_llm_failure_creates_failed_step_and_fails_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend([make_completed_analyst_step(run.id), make_completed_reviewer_step(run.id)])
    db.approvals.append(make_approved_human_approval(run.id))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db, FakeWriterLLMClient(should_fail=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert body["error_message"] == "LLM unavailable"
    assert run.status == WorkflowStatus.failed
    clear_overrides()


def test_run_sales_writer_empty_output_creates_failed_step_and_fails_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.writer_running, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.extend([make_completed_analyst_step(run.id), make_completed_reviewer_step(run.id)])
    db.approvals.append(make_approved_human_approval(run.id))
    db.prompts.append(make_writer_prompt())
    override_dependencies(db, FakeWriterLLMClient(empty_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-writer")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert body["error_message"] == "Writer returned empty final output"
    assert run.status == WorkflowStatus.failed
    clear_overrides()
