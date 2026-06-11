import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.workflow_event import WorkflowEvent, WorkflowEventType


class FakeQuery:
    def __init__(self, items: list[AgentStep] | list[WorkflowEvent]) -> None:
        self.items = items

    def all(self) -> list[AgentStep] | list[WorkflowEvent]:
        return self.items


class FakeSession:
    def __init__(self) -> None:
        self.steps: list[AgentStep] = []
        self.events: list[WorkflowEvent] = []

    def query(self, model: type[AgentStep] | type[WorkflowEvent]) -> FakeQuery:
        if model is AgentStep:
            return FakeQuery(self.steps)
        if model is WorkflowEvent:
            return FakeQuery(self.events)
        raise AssertionError(f"Unexpected model: {model}")


def make_step(
    *,
    agent_type: str,
    agent_name: str,
    status: AgentStepStatus = AgentStepStatus.completed,
    latency_ms: int | None = 1000,
    cost: float | None = 0.1,
    retry_count: int = 0,
    output_json: dict | None = None,
    error_message: str | None = None,
) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=uuid.uuid4(),
        agent_name=agent_name,
        agent_type=agent_type,
        step_order=1,
        status=status,
        output_json=output_json,
        latency_ms=latency_ms,
        cost=cost,
        retry_count=retry_count,
        error_message=error_message,
        created_at=datetime.now(UTC),
    )


def override_db(db: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: db


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_get_agent_performance_summary_groups_agent_metrics():
    db = FakeSession()
    analyst_retry = make_step(
        agent_type="analyst",
        agent_name="Sales Analyst Agent",
        latency_ms=3000,
        cost=0.3,
        retry_count=1,
    )
    failed_classifier = make_step(
        agent_type="classifier",
        agent_name="Customer Feedback Classifier Agent",
        status=AgentStepStatus.failed,
        latency_ms=500,
        cost=0.0,
        error_message="Structured output failed validation after repair attempt",
    )
    db.steps.extend(
        [
            make_step(
                agent_type="analyst",
                agent_name="Sales Analyst Agent",
                latency_ms=1000,
                cost=0.1,
            ),
            analyst_retry,
            make_step(
                agent_type="reviewer",
                agent_name="Reviewer Agent",
                latency_ms=2000,
                cost=0.2,
                output_json={"quality_score": 0.8},
            ),
            make_step(
                agent_type="reviewer",
                agent_name="Reviewer Agent",
                latency_ms=4000,
                cost=0.4,
                output_json={"quality_score": 0.9},
            ),
            failed_classifier,
        ]
    )
    db.events.append(
        WorkflowEvent(
            id=uuid.uuid4(),
            workflow_run_id=failed_classifier.workflow_run_id,
            agent_step_id=failed_classifier.id,
            event_type=WorkflowEventType.agent_failed,
            message="Customer Feedback Classifier Agent failed.",
            error_message="Structured output failed validation after repair attempt",
            created_at=datetime.now(UTC),
        )
    )
    override_db(db)
    client = TestClient(app)

    response = client.get("/agent-performance")

    assert response.status_code == 200
    body = {item["agent_type"]: item for item in response.json()}
    assert body["analyst"]["step_count"] == 2
    assert body["analyst"]["retry_rate"] == 0.5
    assert body["analyst"]["average_latency_ms"] == 2000
    assert body["analyst"]["average_cost"] == 0.2
    assert body["reviewer"]["average_reviewer_score"] == pytest.approx(0.85)
    assert body["classifier"]["failure_rate"] == 1.0
    assert body["classifier"]["schema_validation_failure_rate"] == 1.0
    clear_overrides()
