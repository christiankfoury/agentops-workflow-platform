import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.services.llm_client import LLMUsage, StructuredResponse
from tests.test_sales_analyst_api import FakeSession


class FakeRouterLLMClient:
    def __init__(
        self,
        data: dict[str, Any] | None = None,
        should_fail: bool = False,
    ) -> None:
        self.data = data or {
            "workflow_type": "incident_log",
            "confidence": 0.91,
            "reasoning_summary": "Input contains timestamped operational events.",
        }
        self.should_fail = should_fail
        self.messages: list[dict[str, Any]] = []
        self.system: str | None = None
        self.schema: dict[str, Any] | None = None

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        self.messages = messages
        self.system = system
        self.schema = schema
        if self.should_fail:
            raise RuntimeError("LLM unavailable")
        return StructuredResponse(
            data=self.data,
            model="gpt-router-test",
            usage=LLMUsage(input_tokens=40, output_tokens=12),
        )


def make_router_prompt(is_active: bool = True) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.router,
        name="Router Agent",
        version=1,
        template="Detect workflow type.",
        is_active=is_active,
        created_at=datetime.now(UTC),
    )


def override_dependencies(db: FakeSession, llm: FakeRouterLLMClient | None = None) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm or FakeRouterLLMClient()


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_detect_workflow_type_returns_router_suggestion():
    db = FakeSession()
    llm = FakeRouterLLMClient()
    db.prompts.append(make_router_prompt())
    override_dependencies(db, llm)
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/detect-workflow",
        json={
            "title": "Checkout incident",
            "raw_text": "10:04 - API latency rose. 10:27 - API recovered.",
            "notes": "Production incident",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "workflow_type": "incident_log",
        "confidence": 0.91,
        "reasoning_summary": "Input contains timestamped operational events.",
        "recommended_action": "auto_select",
    }
    assert llm.system == "Detect workflow type."
    assert "Checkout incident" in llm.messages[0]["content"]
    assert "incident_log" in llm.schema["properties"]["workflow_type"]["enum"]
    clear_overrides()


def test_detect_workflow_type_marks_medium_confidence_for_confirmation():
    db = FakeSession()
    db.prompts.append(make_router_prompt())
    override_dependencies(
        db,
        FakeRouterLLMClient(
            data={
                "workflow_type": "customer_feedback",
                "confidence": 0.72,
                "reasoning_summary": "Input contains reviews and feature requests.",
            }
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/detect-workflow",
        json={"title": "Feedback", "raw_text": "Review: Please add exports."},
    )

    assert response.status_code == 200
    assert response.json()["recommended_action"] == "confirm"
    clear_overrides()


def test_detect_workflow_type_requires_manual_selection_for_low_confidence():
    db = FakeSession()
    db.prompts.append(make_router_prompt())
    override_dependencies(
        db,
        FakeRouterLLMClient(
            data={
                "workflow_type": "sales_report",
                "confidence": 0.42,
                "reasoning_summary": "Input is too ambiguous to route confidently.",
            }
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/detect-workflow",
        json={"title": "Ambiguous", "raw_text": "A short note."},
    )

    assert response.status_code == 200
    assert response.json()["recommended_action"] == "manual_required"
    clear_overrides()


def test_detect_workflow_type_requires_active_router_prompt():
    db = FakeSession()
    override_dependencies(db)
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/detect-workflow",
        json={"title": "Input", "raw_text": "Revenue increased 12%."},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Active Router prompt not found"
    clear_overrides()


def test_detect_workflow_type_rejects_invalid_router_output():
    db = FakeSession()
    db.prompts.append(make_router_prompt())
    override_dependencies(
        db,
        FakeRouterLLMClient(
            data={
                "workflow_type": "unknown",
                "confidence": 1.4,
                "reasoning_summary": "",
            }
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs/detect-workflow",
        json={"title": "Input", "raw_text": "Revenue increased 12%."},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Router returned invalid workflow detection output"
    clear_overrides()
