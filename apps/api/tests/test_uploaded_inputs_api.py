import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.uploaded_input import InputType, UploadedInput


class FakeQuery:
    def __init__(self, inputs: list[UploadedInput]) -> None:
        self.inputs = inputs
        self.input_id: uuid.UUID | None = None

    def filter(self, criterion: object) -> "FakeQuery":
        self.input_id = criterion.right.value
        return self

    def first(self) -> UploadedInput | None:
        return next(
            (
                uploaded_input
                for uploaded_input in self.inputs
                if uploaded_input.id == self.input_id
            ),
            None,
        )


class FakeSession:
    def __init__(self) -> None:
        self.inputs: list[UploadedInput] = []

    def query(self, _model: type[UploadedInput]) -> FakeQuery:
        return FakeQuery(self.inputs)

    def add(self, uploaded_input: UploadedInput) -> None:
        self.inputs.append(uploaded_input)

    def commit(self) -> None:
        pass

    def refresh(self, uploaded_input: UploadedInput) -> None:
        if uploaded_input.id is None:
            uploaded_input.id = uuid.uuid4()
        if uploaded_input.created_at is None:
            uploaded_input.created_at = datetime.now(UTC)


def test_create_and_get_uploaded_input():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    created = client.post(
        "/uploaded-inputs",
        json={
            "title": "Q1 Sales Report",
            "input_type": "sales_report",
            "raw_text": "Revenue increased 12%.",
            "notes": "Leadership summary input.",
            "file_name": "q1.md",
            "file_type": "text/markdown",
            "file_size": 23,
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Q1 Sales Report"
    assert body["input_type"] == InputType.sales_report
    assert body["raw_text"] == "Revenue increased 12%."
    assert body["notes"] == "Leadership summary input."

    detail = client.get(f"/uploaded-inputs/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["file_name"] == "q1.md"

    app.dependency_overrides.clear()


def test_missing_uploaded_input_returns_404():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.get(f"/uploaded-inputs/{uuid.uuid4()}")

    assert response.status_code == 404
    app.dependency_overrides.clear()
