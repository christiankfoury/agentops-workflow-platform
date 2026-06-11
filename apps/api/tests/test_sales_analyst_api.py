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
from src.models.cost_event import CostEvent
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEvent
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.llm_client import LLMUsage, StructuredResponse


class FakeQuery:
    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.criteria: list[Any] = []

    def filter(self, *criteria: object) -> "FakeQuery":
        self.criteria.extend(criteria)
        return self

    def order_by(self, *_args: object) -> "FakeQuery":
        return self

    def all(self) -> list[Any]:
        return [item for item in self.items if self._matches_all(item)]

    def first(self) -> Any | None:
        return next(iter(self.all()), None)

    def _matches_all(self, item: Any) -> bool:
        return all(self._matches(item, criterion) for criterion in self.criteria)

    def _matches(self, item: Any, criterion: object) -> bool:
        key = criterion.left.key
        value = self._criterion_value(criterion)
        current = getattr(item, key)
        operator_name = criterion.operator.__name__
        if operator_name == "eq":
            return current == value
        if operator_name == "ne":
            return current != value
        raise AssertionError(f"Unsupported fake query operator: {operator_name}")

    def _criterion_value(self, criterion: object) -> object:
        right = criterion.right
        if hasattr(right, "value"):
            return right.value
        if right.__class__.__name__ == "True_":
            return True
        if right.__class__.__name__ == "False_":
            return False
        raise AssertionError(f"Unsupported fake query value: {right!r}")


class FakeSession:
    def __init__(self) -> None:
        self.runs: list[WorkflowRun] = []
        self.inputs: list[UploadedInput] = []
        self.prompts: list[PromptVersion] = []
        self.steps: list[AgentStep] = []
        self.approvals: list[HumanApproval] = []
        self.cost_events: list[CostEvent] = []
        self.workflow_events: list[WorkflowEvent] = []

    def query(
        self,
        model: (
            type[WorkflowRun]
            | type[UploadedInput]
            | type[PromptVersion]
            | type[AgentStep]
            | type[CostEvent]
            | type[WorkflowEvent]
        ),
    ) -> FakeQuery:
        if model is UploadedInput:
            return FakeQuery(self.inputs)
        if model is PromptVersion:
            return FakeQuery(self.prompts)
        if model is AgentStep:
            return FakeQuery(self.steps)
        if model is HumanApproval:
            return FakeQuery(self.approvals)
        if model is CostEvent:
            return FakeQuery(self.cost_events)
        if model is WorkflowEvent:
            return FakeQuery(self.workflow_events)
        return FakeQuery(self.runs)

    def add(
        self,
        item: (
            WorkflowRun
            | UploadedInput
            | PromptVersion
            | AgentStep
            | HumanApproval
            | CostEvent
            | WorkflowEvent
        ),
    ) -> None:
        if isinstance(item, AgentStep) and item not in self.steps:
            self.steps.append(item)
        if isinstance(item, WorkflowRun) and item not in self.runs:
            self.runs.append(item)
        if isinstance(item, HumanApproval) and item not in self.approvals:
            self.approvals.append(item)
        if isinstance(item, CostEvent) and item not in self.cost_events:
            self.cost_events.append(item)
        if isinstance(item, WorkflowEvent) and item not in self.workflow_events:
            self.workflow_events.append(item)

    def commit(self) -> None:
        pass

    def refresh(
        self,
        item: (
            WorkflowRun
            | UploadedInput
            | PromptVersion
            | AgentStep
            | HumanApproval
            | CostEvent
            | WorkflowEvent
        ),
    ) -> None:
        if item.id is None:
            item.id = uuid.uuid4()
        if hasattr(item, "created_at") and item.created_at is None:
            item.created_at = datetime.now(UTC)
        if isinstance(item, WorkflowRun):
            if item.status is None:
                item.status = WorkflowStatus.created
            if item.retry_count is None:
                item.retry_count = 0
        if isinstance(item, AgentStep) and item.retry_count is None:
            item.retry_count = 0


class FakeLLMClient:
    def __init__(self, should_fail: bool = False, invalid_output: bool = False) -> None:
        self.should_fail = should_fail
        self.invalid_output = invalid_output
        self.messages: list[dict[str, Any]] = []

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        self.messages = messages
        if self.should_fail:
            raise RuntimeError("LLM unavailable")
        if self.invalid_output:
            return StructuredResponse(
                data={"key_findings": ["Revenue increased 12%"]},
                model="gpt-test",
                usage=LLMUsage(input_tokens=100, output_tokens=50),
            )
        return StructuredResponse(
            data={
                "key_findings": ["Revenue increased 12%"],
                "risks": ["Enterprise churn increased"],
                "opportunities": ["Analytics Suite growth remains strong"],
                "recommendations": ["Prioritize enterprise retention"],
                "supporting_evidence": ["Revenue increased from $4.2M to $4.7M"],
            },
            model="gpt-test",
            usage=LLMUsage(input_tokens=100, output_tokens=50),
        )


def make_run(
    *,
    workflow_type: WorkflowType = WorkflowType.sales_report,
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


def make_input(input_type: InputType = InputType.sales_report) -> UploadedInput:
    return UploadedInput(
        id=uuid.uuid4(),
        title="Q1 Sales Report",
        input_type=input_type,
        raw_text="Revenue increased 12%.",
        created_at=datetime.now(UTC),
    )


def make_prompt(is_active: bool = True) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.analyst,
        name="Sales Analyst Agent",
        version=1,
        template="Analyze sales reports.",
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


def override_dependencies(db: FakeSession, llm: FakeLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeLLMClient()


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_run_sales_analyst_success_creates_completed_step():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Sales Analyst Agent"
    assert body["agent_type"] == "analyst"
    assert body["status"] == AgentStepStatus.completed
    assert body["output_json"]["key_findings"] == ["Revenue increased 12%"]
    assert body["output_json"]["opportunities"] == ["Analytics Suite growth remains strong"]
    assert body["model"] == "gpt-test"
    assert body["tokens_input"] == 100
    assert body["tokens_output"] == 50
    assert body["total_tokens"] == 150
    assert body["cost"] == pytest.approx(0.00012)
    assert body["prompt_version_id"] == str(db.prompts[0].id)
    assert run.status == WorkflowStatus.reviewer_running
    assert run.total_tokens == 150
    assert run.total_cost == pytest.approx(0.00012)
    assert len(db.cost_events) == 1
    assert db.cost_events[0].agent_step_id == db.steps[0].id
    assert db.cost_events[0].total_cost == pytest.approx(0.00012)
    clear_overrides()


def test_run_sales_analyst_retry_uses_reviewer_feedback_and_increments_retry_count():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(status=WorkflowStatus.retrying, input_id=uploaded_input.id)
    reviewer_step = AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run.id,
        agent_name="Reviewer Agent",
        agent_type=AgentType.reviewer.value,
        step_order=2,
        status=AgentStepStatus.completed,
        output_json={
            "approved": False,
            "quality_score": 0.62,
            "issues": [
                {
                    "claim": "Enterprise churn doubled",
                    "problem": "Source only says churn increased",
                    "severity": "high",
                }
            ],
            "retry_recommended": True,
        },
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    human_retry = HumanApproval(
        id=uuid.uuid4(),
        workflow_run_id=run.id,
        reviewer_score=0.62,
        issues_json=reviewer_step.output_json["issues"],
        status=ApprovalStatus.retry_requested,
        human_feedback="Focus on the churn claim and cite only exact source language.",
        edited_analysis_json={"risks": ["Enterprise churn claim needs support."]},
        created_at=datetime.now(UTC),
        resolved_at=datetime.now(UTC),
    )
    llm = FakeLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.steps.append(reviewer_step)
    db.approvals.append(human_retry)
    db.prompts.append(make_prompt())
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.completed
    assert body["retry_count"] == 1
    assert body["input_json"]["retry_count"] == 1
    assert body["input_json"]["retry_reason"] == (
        "Reviewer recommended retry; Quality score is below 0.70; "
        "High severity reviewer issue"
    )
    assert body["input_json"]["reviewer_feedback"] == reviewer_step.output_json
    assert body["input_json"]["human_feedback"] == (
        "Focus on the churn claim and cite only exact source language."
    )
    assert body["input_json"]["edited_analysis_json"] == {
        "risks": ["Enterprise churn claim needs support."]
    }
    assert "This is a retry" in llm.messages[0]["content"]
    assert "Human feedback: Focus on the churn claim" in llm.messages[0]["content"]
    assert "Human-edited analysis JSON" in llm.messages[0]["content"]
    assert run.retry_count == 1
    assert run.status == WorkflowStatus.reviewer_running
    clear_overrides()


def test_run_sales_analyst_missing_workflow_returns_404():
    db = FakeSession()
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{uuid.uuid4()}/run-analyst")

    assert response.status_code == 404
    clear_overrides()


def test_run_sales_analyst_without_input_returns_422():
    db = FakeSession()
    run = make_run()
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 422
    assert response.json()["detail"] == "Workflow run must have an uploaded input"
    clear_overrides()


def test_run_sales_analyst_missing_uploaded_input_returns_422():
    db = FakeSession()
    run = make_run(input_id=uuid.uuid4())
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 422
    assert response.json()["detail"] == "Uploaded input not found"
    clear_overrides()


def test_run_sales_analyst_rejects_non_sales_workflow():
    db = FakeSession()
    uploaded_input = make_input(InputType.customer_feedback)
    run = make_run(workflow_type=WorkflowType.customer_feedback, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 422
    assert response.json()["detail"] == "Sales analyst only supports sales report workflows"
    clear_overrides()


def test_run_sales_analyst_rejects_baseline_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(run_mode=RunMode.baseline, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 422
    assert response.json()["detail"] == "Sales analyst only runs for multi-agent workflows"
    clear_overrides()


def test_run_sales_analyst_without_active_prompt_returns_422():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 422
    assert response.json()["detail"] == "Active Sales Analyst prompt not found"
    clear_overrides()


def test_run_sales_analyst_llm_failure_creates_failed_step_and_fails_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db, FakeLLMClient(should_fail=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert body["error_message"] == "LLM unavailable"
    assert run.status == WorkflowStatus.failed
    clear_overrides()


def test_run_sales_analyst_invalid_output_creates_failed_step_and_fails_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db, FakeLLMClient(invalid_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-analyst")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert "risks" in body["error_message"]
    assert run.status == WorkflowStatus.failed
    clear_overrides()


def test_list_agent_steps_returns_steps_for_run():
    db = FakeSession()
    run = make_run()
    other_run = make_run()
    first_step = AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run.id,
        agent_name="Sales Analyst Agent",
        agent_type="analyst",
        step_order=1,
        status=AgentStepStatus.completed,
        retry_count=0,
        created_at=datetime.now(UTC),
    )
    other_step = AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=other_run.id,
        agent_name="Sales Analyst Agent",
        agent_type="analyst",
        step_order=1,
        status=AgentStepStatus.completed,
        retry_count=0,
        created_at=datetime.now(UTC),
    )
    db.runs.extend([run, other_run])
    db.steps.extend([first_step, other_step])
    override_dependencies(db)
    client = TestClient(app)

    response = client.get(f"/workflow-runs/{run.id}/agent-steps")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(first_step.id)
    clear_overrides()
