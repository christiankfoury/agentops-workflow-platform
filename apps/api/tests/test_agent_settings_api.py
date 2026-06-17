import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from tests.test_sales_analyst_api import FakeSession


def make_prompt(agent_type: AgentType = AgentType.analyst) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=agent_type,
        name=f"{agent_type.value} prompt",
        version=1,
        template="Do the work.",
        is_active=True,
        created_at=datetime.now(UTC),
    )


def override_db(db: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: db


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_list_agent_settings_returns_effective_defaults_for_all_agents():
    db = FakeSession()
    db.prompts.extend([make_prompt(agent_type) for agent_type in AgentType])
    override_db(db)
    client = TestClient(app)

    response = client.get("/agent-settings")

    assert response.status_code == 200
    body = response.json()
    assert {item["agent_type"] for item in body} == {agent_type.value for agent_type in AgentType}
    analyst = next(item for item in body if item["agent_type"] == AgentType.analyst.value)
    assert analyst["id"] is None
    assert analyst["model"] == "gpt-4.1-mini"
    assert analyst["max_tokens"] == 2048
    assert analyst["max_retries"] == 2
    assert analyst["active_prompt_name"] == "analyst prompt"
    clear_overrides()


def test_update_agent_setting_persists_model_and_thresholds():
    db = FakeSession()
    prompt = make_prompt(AgentType.reviewer)
    db.prompts.append(prompt)
    override_db(db)
    client = TestClient(app)

    response = client.put(
        "/agent-settings/reviewer",
        json={
            "model": "gpt-4.1",
            "temperature": 0.2,
            "max_tokens": 900,
            "timeout_seconds": 45,
            "max_retries": 3,
            "active_prompt_version_id": str(prompt.id),
            "reviewer_approval_threshold": 0.9,
            "human_approval_threshold": 0.65,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_type"] == "reviewer"
    assert body["model"] == "gpt-4.1"
    assert body["active_prompt_version_id"] == str(prompt.id)
    assert body["reviewer_approval_threshold"] == 0.9
    assert body["human_approval_threshold"] == 0.65
    assert len(db.agent_settings) == 1
    assert db.agent_settings[0].max_retries == 3
    clear_overrides()


def test_update_agent_setting_rejects_prompt_for_different_agent():
    db = FakeSession()
    prompt = make_prompt(AgentType.writer)
    db.prompts.append(prompt)
    override_db(db)
    client = TestClient(app)

    response = client.put(
        "/agent-settings/reviewer",
        json={
            "model": "gpt-4.1",
            "max_tokens": 900,
            "max_retries": 3,
            "active_prompt_version_id": str(prompt.id),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Prompt version agent type does not match setting agent type"
    )
    clear_overrides()


def test_update_agent_setting_rejects_unsupported_model():
    db = FakeSession()
    override_db(db)
    client = TestClient(app)

    response = client.put(
        "/agent-settings/reviewer",
        json={
            "model": "gpt-reviewer",
            "max_tokens": 900,
            "max_retries": 3,
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Model must be one of" in detail[0]["msg"]
    clear_overrides()
