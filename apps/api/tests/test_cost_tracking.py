import uuid
from datetime import UTC, datetime

import pytest

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.services.cost_tracking import estimate_token_cost, record_agent_cost
from tests.test_sales_analyst_api import FakeSession, make_run


def make_completed_step(run_id: uuid.UUID) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Sales Analyst Agent",
        agent_type=AgentType.analyst.value,
        step_order=1,
        status=AgentStepStatus.completed,
        model="gpt-4.1-mini",
        tokens_input=100,
        tokens_output=50,
        total_tokens=150,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def test_estimate_token_cost_uses_model_pricing():
    cost_input, cost_output, total_cost = estimate_token_cost("gpt-4.1-mini", 100, 50)

    assert cost_input == pytest.approx(0.00004)
    assert cost_output == pytest.approx(0.00008)
    assert total_cost == pytest.approx(0.00012)


def test_record_agent_cost_persists_one_event_per_step():
    db = FakeSession()
    run = make_run()
    step = make_completed_step(run.id)
    db.runs.append(run)
    db.steps.append(step)

    first_event = record_agent_cost(db, step)
    second_event = record_agent_cost(db, step)

    assert first_event is not None
    assert second_event is None
    assert step.cost == pytest.approx(0.00012)
    assert len(db.cost_events) == 1
    assert db.cost_events[0].workflow_run_id == run.id
    assert db.cost_events[0].agent_step_id == step.id
    assert db.cost_events[0].tokens_input == 100
    assert db.cost_events[0].tokens_output == 50
    assert db.cost_events[0].total_tokens == 150
    assert db.cost_events[0].total_cost == pytest.approx(0.00012)
