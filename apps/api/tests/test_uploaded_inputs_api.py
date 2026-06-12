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


def test_uploaded_input_rejects_blank_required_text():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs",
        json={
            "title": "   ",
            "input_type": "sales_report",
            "raw_text": "   ",
        },
    )

    assert response.status_code == 422
    app.dependency_overrides.clear()


def test_uploaded_input_rejects_oversized_raw_text():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs",
        json={
            "title": "Huge report",
            "input_type": "sales_report",
            "raw_text": "x" * 50_001,
        },
    )

    assert response.status_code == 422
    app.dependency_overrides.clear()


def test_uploaded_input_strips_text_fields():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs",
        json={
            "title": "  Q1 Sales Report  ",
            "input_type": "sales_report",
            "raw_text": "  Revenue increased 12%.  ",
            "notes": "  Review for leadership.  ",
            "file_name": "  q1.md  ",
            "file_type": "  text/markdown  ",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Q1 Sales Report"
    assert body["raw_text"] == "Revenue increased 12%."
    assert body["notes"] == "Review for leadership."
    assert body["file_name"] == "q1.md"
    assert body["file_type"] == "text/markdown"
    app.dependency_overrides.clear()


def test_create_incident_input_normalizes_timestamped_events():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs",
        json={
            "title": "Incident log",
            "input_type": "incident_log",
            "raw_text": "10:02 AM - API latency increased\n10:08 AM - Error rate exceeded",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["raw_text"] == (
        "Parsed incident events:\n"
        "Event 1: time=10:02 AM; event=API latency increased; "
        "raw_line=10:02 AM - API latency increased\n"
        "Event 2: time=10:08 AM; event=Error rate exceeded; "
        "raw_line=10:08 AM - Error rate exceeded"
    )
    app.dependency_overrides.clear()


def test_upload_text_file_creates_uploaded_input():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={
            "title": "  Q1 Sales Report  ",
            "input_type": "sales_report",
            "notes": "  Uploaded report.  ",
        },
        files={"file": ("q1.txt", b"  Revenue increased 12%.\n", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Q1 Sales Report"
    assert body["raw_text"] == "Revenue increased 12%."
    assert body["notes"] == "Uploaded report."
    assert body["file_name"] == "q1.txt"
    assert body["file_type"] == "text/plain"
    assert body["file_size"] == 25
    app.dependency_overrides.clear()


def test_upload_csv_file_creates_uploaded_input():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={"title": "Feedback CSV", "input_type": "customer_feedback"},
        files={
            "file": (
                "feedback.csv",
                b"customer_id,feedback\n1,Mobile checkout is slow\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["raw_text"] == "Feedback 1: customer_id=1. Mobile checkout is slow"
    assert body["file_name"] == "feedback.csv"
    app.dependency_overrides.clear()


def test_upload_incident_log_includes_ambiguous_lines():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={"title": "Incident Log", "input_type": "incident_log"},
        files={
            "file": (
                "incident.txt",
                b"10:02 AM - API latency increased\nNo timestamp here\n10:40 AM - Recovered\n",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert "Parsed incident events:" in body["raw_text"]
    assert "Event 2: time=10:40 AM; event=Recovered" in body["raw_text"]
    assert "Ambiguous incident log lines:\n- No timestamp here" in body["raw_text"]
    app.dependency_overrides.clear()


def test_customer_feedback_csv_upload_requires_feedback_column():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={"title": "Feedback CSV", "input_type": "customer_feedback"},
        files={
            "file": (
                "feedback.csv",
                b"customer_id,comment\n1,Mobile checkout is slow\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Customer feedback CSV uploads must include a feedback column"
    )
    app.dependency_overrides.clear()


def test_sales_csv_upload_preserves_raw_text_until_feedback_workflow():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={"title": "Sales CSV", "input_type": "sales_report"},
        files={"file": ("sales.csv", b"region,revenue\nNA,120\n", "text/csv")},
    )

    assert response.status_code == 201
    assert response.json()["raw_text"] == "region,revenue\nNA,120"
    app.dependency_overrides.clear()


def test_upload_rejects_unsupported_file_type():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={"title": "PDF", "input_type": "sales_report"},
        files={"file": ("report.pdf", b"%PDF", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Only .txt, .md, and .csv uploads are supported"
    app.dependency_overrides.clear()


def test_upload_rejects_mismatched_content_type():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={"title": "Disguised PDF", "input_type": "sales_report"},
        files={"file": ("report.txt", b"%PDF", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Uploaded file content type does not match the allowed file type"
    )
    app.dependency_overrides.clear()


def test_upload_rejects_oversized_file():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={"title": "Large report", "input_type": "sales_report"},
        files={"file": ("report.txt", b"x" * (250 * 1024 + 1), "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Uploaded file must be 250 KB or smaller"
    app.dependency_overrides.clear()


def test_upload_rejects_blank_title_after_trimming():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/upload",
        data={"title": "   ", "input_type": "sales_report"},
        files={"file": ("report.txt", b"Revenue increased 12%.", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Input title is required"
    app.dependency_overrides.clear()
