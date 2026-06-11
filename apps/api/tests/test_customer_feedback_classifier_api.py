import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_setting import AgentSetting
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.cost_event import CostEvent
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
        raise AssertionError(f"Unsupported fake query operator: {operator_name}")

    def _criterion_value(self, criterion: object) -> object:
        right = criterion.right
        if hasattr(right, "value"):
            return right.value
        if right.__class__.__name__ == "True_":
            return True
        raise AssertionError(f"Unsupported fake query value: {right!r}")


class FakeSession:
    def __init__(self) -> None:
        self.runs: list[WorkflowRun] = []
        self.inputs: list[UploadedInput] = []
        self.prompts: list[PromptVersion] = []
        self.agent_settings: list[AgentSetting] = []
        self.steps: list[AgentStep] = []
        self.cost_events: list[CostEvent] = []
        self.workflow_events: list[WorkflowEvent] = []

    def query(
        self,
        model: (
            type[WorkflowRun]
            | type[UploadedInput]
            | type[PromptVersion]
            | type[AgentSetting]
            | type[AgentStep]
            | type[CostEvent]
            | type[WorkflowEvent]
        ),
    ) -> FakeQuery:
        if model is UploadedInput:
            return FakeQuery(self.inputs)
        if model is PromptVersion:
            return FakeQuery(self.prompts)
        if model is AgentSetting:
            return FakeQuery(self.agent_settings)
        if model is AgentStep:
            return FakeQuery(self.steps)
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
            | AgentSetting
            | AgentStep
            | CostEvent
            | WorkflowEvent
        ),
    ) -> None:
        if isinstance(item, AgentStep) and item not in self.steps:
            self.steps.append(item)
        if isinstance(item, AgentSetting) and item not in self.agent_settings:
            self.agent_settings.append(item)
        if isinstance(item, WorkflowRun) and item not in self.runs:
            self.runs.append(item)
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
            | AgentSetting
            | AgentStep
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
                data={"themes": [{"name": "not_a_category", "count": 1}]},
                model="gpt-test",
                usage=LLMUsage(input_tokens=120, output_tokens=80),
            )
        return StructuredResponse(
            data={
                "themes": [
                    {
                        "name": "performance",
                        "count": 2,
                        "sentiment": "negative",
                        "examples": [
                            {
                                "text": "The mobile app is slow during checkout.",
                                "source": "review-1",
                            }
                        ],
                    },
                    {
                        "name": "feature_requests",
                        "count": 1,
                        "sentiment": "neutral",
                        "examples": [
                            {"text": "Please add bulk export.", "source": "ticket-9"}
                        ],
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
                        "supporting_examples": [
                            {"text": "Please add bulk export.", "source": "ticket-9"}
                        ],
                    }
                ],
                "bug_reports": [
                    {
                        "issue": "Checkout slowdown",
                        "count": 2,
                        "severity": "medium",
                        "supporting_examples": [
                            {
                                "text": "The mobile app is slow during checkout.",
                                "source": "review-1",
                            }
                        ],
                    }
                ],
            },
            model="gpt-test",
            usage=LLMUsage(input_tokens=120, output_tokens=80),
        )


def make_run(
    *,
    workflow_type: WorkflowType = WorkflowType.customer_feedback,
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


def make_input(input_type: InputType = InputType.customer_feedback) -> UploadedInput:
    return UploadedInput(
        id=uuid.uuid4(),
        title="Customer Feedback Batch",
        input_type=input_type,
        raw_text="Review 1: The mobile app is slow. Ticket 9: Please add bulk export.",
        notes="Q1 feedback",
        created_at=datetime.now(UTC),
    )


def make_prompt(is_active: bool = True) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.classifier,
        name="Classifier Agent",
        version=1,
        template="Classify customer feedback.",
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


def override_dependencies(db: FakeSession, llm: FakeLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeLLMClient()


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_run_customer_feedback_classifier_success_creates_completed_step():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    llm = FakeLLMClient()
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-classifier")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Customer Feedback Classifier Agent"
    assert body["agent_type"] == "classifier"
    assert body["status"] == AgentStepStatus.completed
    assert body["output_json"]["themes"][0]["name"] == "performance"
    assert body["output_json"]["feature_requests"][0]["request"] == "Bulk export"
    assert body["model"] == "gpt-test"
    assert body["tokens_input"] == 120
    assert body["tokens_output"] == 80
    assert body["total_tokens"] == 200
    assert body["cost"] == pytest.approx(0.000176)
    assert body["prompt_version_id"] == str(db.prompts[0].id)
    assert body["input_json"]["notes"] == "Q1 feedback"
    assert run.status == WorkflowStatus.running
    assert run.total_tokens == 200
    assert run.total_cost == pytest.approx(0.000176)
    assert len(db.cost_events) == 1
    assert db.cost_events[0].agent_step_id == db.steps[0].id
    assert "Customer feedback:" in llm.messages[0]["content"]
    assert llm.schema is not None
    assert llm.system == "Classify customer feedback."
    clear_overrides()


def test_run_customer_feedback_classifier_rejects_non_customer_feedback_workflow():
    db = FakeSession()
    uploaded_input = make_input(InputType.sales_report)
    run = make_run(workflow_type=WorkflowType.sales_report, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-classifier")

    assert response.status_code == 422
    assert response.json()["detail"] == "Classifier only supports customer feedback workflows"
    clear_overrides()


def test_run_customer_feedback_classifier_rejects_non_customer_feedback_input():
    db = FakeSession()
    uploaded_input = make_input(InputType.sales_report)
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-classifier")

    assert response.status_code == 422
    assert response.json()["detail"] == "Uploaded input must be customer feedback"
    clear_overrides()


def test_run_customer_feedback_classifier_rejects_baseline_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(run_mode=RunMode.baseline, input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-classifier")

    assert response.status_code == 422
    assert response.json()["detail"] == "Classifier only runs for multi-agent workflows"
    clear_overrides()


def test_run_customer_feedback_classifier_without_active_prompt_returns_422():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-classifier")

    assert response.status_code == 422
    assert response.json()["detail"] == "Active Classifier prompt not found"
    clear_overrides()


def test_run_customer_feedback_classifier_invalid_output_fails_step_and_run():
    db = FakeSession()
    uploaded_input = make_input()
    run = make_run(input_id=uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    db.prompts.append(make_prompt())
    override_dependencies(db, FakeLLMClient(invalid_output=True))
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/run-classifier")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == AgentStepStatus.failed
    assert "sentiment" in body["error_message"]
    assert run.status == WorkflowStatus.failed
    clear_overrides()
