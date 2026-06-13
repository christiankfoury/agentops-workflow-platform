import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType


class FakeQuery:
    def __init__(
        self, items: list[WorkflowRun] | list[UploadedInput] | list[WorkflowEvent] | list[AgentStep]
    ) -> None:
        self.items = items
        self.criteria: list[object] = []

    def order_by(self, *_args: object) -> "FakeQuery":
        return self

    def filter(self, *criteria: object) -> "FakeQuery":
        self.criteria.extend(criteria)
        return self

    def all(
        self,
    ) -> list[WorkflowRun] | list[UploadedInput] | list[WorkflowEvent] | list[AgentStep]:
        return [item for item in self.items if self._matches_all(item)]

    def first(self) -> WorkflowRun | UploadedInput | WorkflowEvent | AgentStep | None:
        return next(iter(self.all()), None)

    def _matches_all(self, item: object) -> bool:
        return all(self._matches(item, criterion) for criterion in self.criteria)

    def _matches(self, item: object, criterion: object) -> bool:
        key = criterion.left.key
        right = criterion.right
        value = right.value if hasattr(right, "value") else right.effective_value
        return getattr(item, key) == value


class FakeSession:
    def __init__(self) -> None:
        self.runs: list[WorkflowRun] = []
        self.inputs: list[UploadedInput] = []
        self.workflow_events: list[WorkflowEvent] = []
        self.steps: list[AgentStep] = []

    def query(
        self,
        model: type[WorkflowRun] | type[UploadedInput] | type[WorkflowEvent] | type[AgentStep],
    ) -> FakeQuery:
        if model is UploadedInput:
            return FakeQuery(self.inputs)
        if model is WorkflowEvent:
            return FakeQuery(self.workflow_events)
        if model is AgentStep:
            return FakeQuery(self.steps)
        return FakeQuery(self.runs)

    def add(self, item: WorkflowRun | WorkflowEvent | AgentStep) -> None:
        if isinstance(item, WorkflowEvent):
            self.workflow_events.append(item)
            return
        if isinstance(item, AgentStep):
            self.steps.append(item)
            return
        self.runs.append(item)

    def commit(self) -> None:
        pass

    def refresh(self, item: WorkflowRun | WorkflowEvent | AgentStep) -> None:
        if item.id is None:
            item.id = uuid.uuid4()
        if item.created_at is None:
            item.created_at = datetime.now(UTC)
        if isinstance(item, WorkflowRun):
            if item.status is None:
                item.status = WorkflowStatus.created
            if item.retry_count is None:
                item.retry_count = 0


def test_create_list_and_get_workflow_run():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    created = client.post(
        "/workflow-runs",
        json={"workflow_type": "sales_report", "run_mode": "multi_agent"},
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    listed = client.get("/workflow-runs")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == run_id

    detail = client.get(f"/workflow-runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["workflow_type"] == WorkflowType.sales_report

    app.dependency_overrides.clear()


def test_create_workflow_run_with_input_id():
    uploaded_input = UploadedInput(
        id=uuid.uuid4(),
        title="Q1 Sales Report",
        input_type=InputType.sales_report,
        raw_text="Revenue increased 12%.",
        created_at=datetime.now(UTC),
    )
    db = FakeSession()
    db.inputs.append(uploaded_input)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    created = client.post(
        "/workflow-runs",
        json={
            "workflow_type": "sales_report",
            "run_mode": "multi_agent",
            "input_id": str(uploaded_input.id),
        },
    )

    assert created.status_code == 201
    assert created.json()["input_id"] == str(uploaded_input.id)

    listed = client.get("/workflow-runs")
    assert listed.status_code == 200
    assert listed.json()[0]["input_title"] == "Q1 Sales Report"

    detail = client.get(f"/workflow-runs/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["input_title"] == "Q1 Sales Report"
    app.dependency_overrides.clear()


def test_create_workflow_run_with_missing_input_id_returns_422():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(
        "/workflow-runs",
        json={
            "workflow_type": "sales_report",
            "run_mode": "multi_agent",
            "input_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 422
    app.dependency_overrides.clear()


def test_create_workflow_run_with_mismatched_input_type_returns_422():
    uploaded_input = UploadedInput(
        id=uuid.uuid4(),
        title="Feedback Export",
        input_type=InputType.customer_feedback,
        raw_text="Customers requested export improvements.",
        created_at=datetime.now(UTC),
    )
    db = FakeSession()
    db.inputs.append(uploaded_input)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(
        "/workflow-runs",
        json={
            "workflow_type": "sales_report",
            "run_mode": "multi_agent",
            "input_id": str(uploaded_input.id),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Uploaded input type must match workflow type"
    app.dependency_overrides.clear()


def test_missing_workflow_run_returns_404():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.get(f"/workflow-runs/{uuid.uuid4()}")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_invalid_status_transition_returns_422():
    run = WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        run_mode=RunMode.multi_agent,
        status=WorkflowStatus.created,
        retry_count=0,
        created_at=datetime.now(UTC),
    )
    db = FakeSession()
    db.runs.append(run)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.patch(f"/workflow-runs/{run.id}/status", json={"status": "completed"})

    assert response.status_code == 422
    app.dependency_overrides.clear()


def test_cancel_workflow_run_marks_running_steps_and_logs_event():
    run = WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        run_mode=RunMode.multi_agent,
        status=WorkflowStatus.running,
        retry_count=0,
        created_at=datetime.now(UTC),
    )
    step = AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run.id,
        agent_name="Analyst Agent",
        agent_type="analyst",
        step_order=1,
        status=AgentStepStatus.running,
        retry_count=0,
        created_at=datetime.now(UTC),
    )
    db = FakeSession()
    db.runs.append(run)
    db.steps.append(step)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == WorkflowStatus.cancelled
    assert run.completed_at is not None
    assert step.status == AgentStepStatus.failed
    assert step.error_message == "Workflow was cancelled before this step completed."
    assert db.workflow_events[-1].event_type == WorkflowEventType.workflow_cancelled
    app.dependency_overrides.clear()


def test_cancel_completed_workflow_run_returns_422():
    run = WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        run_mode=RunMode.multi_agent,
        status=WorkflowStatus.completed,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db = FakeSession()
    db.runs.append(run)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(f"/workflow-runs/{run.id}/cancel")

    assert response.status_code == 422
    app.dependency_overrides.clear()
