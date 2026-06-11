import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.workflow_events import log_workflow_event
from tests.test_sales_analyst_api import FakeSession, make_input


def override_db(db: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: db


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def make_run(status: WorkflowStatus = WorkflowStatus.created) -> WorkflowRun:
    return WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        run_mode=RunMode.multi_agent,
        status=status,
        retry_count=0,
        created_at=datetime.now(UTC),
    )


def test_create_workflow_run_logs_started_event():
    db = FakeSession()
    uploaded_input = make_input()
    db.inputs.append(uploaded_input)
    override_db(db)
    client = TestClient(app)

    response = client.post(
        "/workflow-runs",
        json={
            "workflow_type": "sales_report",
            "run_mode": "multi_agent",
            "input_id": str(uploaded_input.id),
        },
    )

    assert response.status_code == 201
    assert len(db.workflow_events) == 1
    event = db.workflow_events[0]
    assert event.event_type == WorkflowEventType.workflow_started
    assert event.workflow_run_id == db.runs[0].id
    assert event.agent_step_id is None
    assert event.metadata_json == {
        "workflow_type": "sales_report",
        "run_mode": "multi_agent",
        "status": "created",
        "input_id": str(uploaded_input.id),
    }
    clear_overrides()


def test_list_workflow_events_returns_events_for_run_in_creation_order():
    db = FakeSession()
    run = make_run()
    other_run = make_run()
    db.runs.extend([run, other_run])
    first = WorkflowEvent(
        id=uuid.uuid4(),
        workflow_run_id=run.id,
        event_type=WorkflowEventType.workflow_started,
        message="Workflow run created.",
        created_at=datetime.now(UTC),
    )
    second = WorkflowEvent(
        id=uuid.uuid4(),
        workflow_run_id=run.id,
        event_type=WorkflowEventType.agent_started,
        message="Sales Analyst Agent started.",
        metadata_json={"agent_type": "analyst"},
        created_at=datetime.now(UTC),
    )
    other = WorkflowEvent(
        id=uuid.uuid4(),
        workflow_run_id=other_run.id,
        event_type=WorkflowEventType.workflow_started,
        message="Other workflow run created.",
        created_at=datetime.now(UTC),
    )
    db.workflow_events.extend([first, second, other])
    override_db(db)
    client = TestClient(app)

    response = client.get(f"/workflow-runs/{run.id}/events")

    assert response.status_code == 200
    body = response.json()
    assert [event["id"] for event in body] == [str(first.id), str(second.id)]
    assert body[1]["metadata_json"] == {"agent_type": "analyst"}
    clear_overrides()


def test_missing_workflow_run_events_returns_404():
    db = FakeSession()
    override_db(db)
    client = TestClient(app)

    response = client.get(f"/workflow-runs/{uuid.uuid4()}/events")

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow run not found"
    clear_overrides()


def test_log_workflow_event_persists_metadata_and_error_message():
    db = FakeSession()
    run = make_run(status=WorkflowStatus.failed)
    db.runs.append(run)

    event = log_workflow_event(
        db,
        run,
        WorkflowEventType.workflow_failed,
        "Workflow failed.",
        metadata={"retry_count": 2, "input_id": uuid.UUID(int=1)},
        error_message="LLM unavailable",
    )

    assert event in db.workflow_events
    assert event.event_type == WorkflowEventType.workflow_failed
    assert event.error_message == "LLM unavailable"
    assert event.metadata_json == {
        "retry_count": 2,
        "input_id": "00000000-0000-0000-0000-000000000001",
    }
