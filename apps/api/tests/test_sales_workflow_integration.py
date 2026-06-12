from typing import Any

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_type import AgentType
from src.models.human_approval import ApprovalStatus
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import WorkflowStatus
from src.services.llm_client import LLMUsage, StructuredResponse, TextResponse
from tests.test_sales_analyst_api import (
    FakeSession,
    clear_overrides,
    make_input,
    make_prompt,
    make_run,
)
from tests.test_sales_reviewer_api import make_reviewer_prompt
from tests.test_sales_writer_api import make_writer_prompt

ANALYST_OUTPUT = {
    "key_findings": ["Revenue increased 12% from $4.2M to $4.7M."],
    "risks": ["Enterprise churn increased from 5% to 7%."],
    "opportunities": ["North America grew 18%."],
    "recommendations": ["Prioritize enterprise retention."],
    "supporting_evidence": ["Q1 report: revenue increased 12%."],
}

APPROVED_REVIEW_OUTPUT = {
    "approved": True,
    "quality_score": 0.93,
    "issues": [],
    "retry_recommended": False,
}

RETRY_REVIEW_OUTPUT = {
    "approved": False,
    "quality_score": 0.62,
    "issues": [
        {
            "claim": "Enterprise churn doubled.",
            "problem": "The source only says churn increased from 5% to 7%.",
            "severity": "high",
        }
    ],
    "retry_recommended": True,
}


class SequentialWorkflowLLM:
    def __init__(
        self,
        structured_responses: list[dict[str, Any]],
        text_responses: list[str] | None = None,
    ) -> None:
        self.structured_responses = structured_responses
        self.text_responses = text_responses or []
        self.structured_calls: list[list[dict[str, Any]]] = []
        self.text_calls: list[list[dict[str, Any]]] = []

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> StructuredResponse:
        self.structured_calls.append(messages)
        return StructuredResponse(
            data=self.structured_responses.pop(0),
            model=model or "gpt-integration-test",
            usage=LLMUsage(input_tokens=100, output_tokens=50),
        )

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> TextResponse:
        self.text_calls.append(messages)
        return TextResponse(
            content=self.text_responses.pop(0),
            model=model or "gpt-integration-test",
            usage=LLMUsage(input_tokens=120, output_tokens=60),
        )


def setup_sales_workflow(
    llm: SequentialWorkflowLLM,
    *,
    status: WorkflowStatus = WorkflowStatus.created,
) -> tuple[FakeSession, TestClient, str]:
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=status, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.extend([make_prompt(), make_reviewer_prompt(), make_writer_prompt()])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm
    return db, TestClient(app), str(run.id)


def test_sales_workflow_integration_completes_after_human_approval():
    llm = SequentialWorkflowLLM(
        structured_responses=[ANALYST_OUTPUT, APPROVED_REVIEW_OUTPUT],
        text_responses=["Executive Summary\nRevenue increased 12%."],
    )
    db, client, run_id = setup_sales_workflow(llm)

    analyst_response = client.post(f"/workflow-runs/{run_id}/run-analyst")
    reviewer_response = client.post(f"/workflow-runs/{run_id}/run-reviewer")
    writer_before_approval = client.post(f"/workflow-runs/{run_id}/run-writer")

    assert analyst_response.status_code == 200
    assert reviewer_response.status_code == 200
    assert writer_before_approval.status_code == 422
    assert writer_before_approval.json()["detail"] == "Writer can only run after approval"
    assert db.runs[0].status == WorkflowStatus.waiting_for_human
    assert len(db.approvals) == 1
    approval = db.approvals[0]
    assert approval.status == ApprovalStatus.pending
    assert approval.reviewer_score == 0.93

    approval_response = client.post(
        f"/human-approvals/{approval.id}/approve",
        json={"human_feedback": "Approved for leadership summary."},
    )
    writer_response = client.post(f"/workflow-runs/{run_id}/run-writer")

    assert approval_response.status_code == 200
    assert writer_response.status_code == 200
    assert approval.status == ApprovalStatus.approved
    assert db.runs[0].status == WorkflowStatus.completed
    assert db.runs[0].final_output == "Executive Summary\nRevenue increased 12%."
    assert [step.agent_type for step in db.steps] == [
        AgentType.analyst.value,
        AgentType.reviewer.value,
        AgentType.writer.value,
    ]
    assert any(
        event.event_type == WorkflowEventType.human_approved
        for event in db.workflow_events
    )
    assert any(
        event.event_type == WorkflowEventType.workflow_completed
        for event in db.workflow_events
    )
    clear_overrides()


def test_sales_workflow_integration_retries_after_reviewer_rejection():
    llm = SequentialWorkflowLLM(
        structured_responses=[ANALYST_OUTPUT, RETRY_REVIEW_OUTPUT, ANALYST_OUTPUT],
    )
    db, client, run_id = setup_sales_workflow(llm)

    first_analyst = client.post(f"/workflow-runs/{run_id}/run-analyst")
    reviewer = client.post(f"/workflow-runs/{run_id}/run-reviewer")

    assert first_analyst.status_code == 200
    assert reviewer.status_code == 200
    assert db.runs[0].status == WorkflowStatus.retrying
    assert db.runs[0].retry_count == 0
    assert db.approvals == []
    assert any(
        event.event_type == WorkflowEventType.retry_triggered
        for event in db.workflow_events
    )

    retry_analyst = client.post(f"/workflow-runs/{run_id}/run-analyst")

    assert retry_analyst.status_code == 200
    assert db.runs[0].status == WorkflowStatus.reviewer_running
    assert db.runs[0].retry_count == 1
    retry_step = db.steps[-1]
    assert retry_step.agent_type == AgentType.analyst.value
    assert retry_step.retry_count == 1
    assert "Reviewer recommended retry" in retry_step.input_json["retry_reason"]
    assert "High severity reviewer issue" in retry_step.input_json["retry_reason"]
    assert retry_step.input_json["reviewer_feedback"]["issues"][0]["claim"] == (
        "Enterprise churn doubled."
    )
    assert len(llm.structured_calls) == 3
    clear_overrides()
