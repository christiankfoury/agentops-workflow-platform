import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType


class FakeQuery:
    def __init__(self, items: list[WorkflowRun] | list[UploadedInput]) -> None:
        self.items = items
        self.item_id: uuid.UUID | None = None

    def order_by(self, *_args: object) -> "FakeQuery":
        return self

    def filter(self, criterion: object) -> "FakeQuery":
        self.item_id = criterion.right.value
        return self

    def all(self) -> list[WorkflowRun] | list[UploadedInput]:
        return self.items

    def first(self) -> WorkflowRun | UploadedInput | None:
        return next((item for item in self.items if item.id == self.item_id), None)


class FakeSession:
    def __init__(self) -> None:
        self.runs: list[WorkflowRun] = []
        self.inputs: list[UploadedInput] = []

    def query(self, model: type[WorkflowRun] | type[UploadedInput]) -> FakeQuery:
        if model is UploadedInput:
            return FakeQuery(self.inputs)
        return FakeQuery(self.runs)

    def add(self, run: WorkflowRun) -> None:
        self.runs.append(run)

    def commit(self) -> None:
        pass

    def refresh(self, run: WorkflowRun) -> None:
        if run.id is None:
            run.id = uuid.uuid4()
        if run.status is None:
            run.status = WorkflowStatus.created
        if run.retry_count is None:
            run.retry_count = 0
        if run.created_at is None:
            run.created_at = datetime.now(UTC)


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
