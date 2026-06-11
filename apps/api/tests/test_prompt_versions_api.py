import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion


class FakeQuery:
    def __init__(self, prompts: list[PromptVersion]) -> None:
        self.prompts = prompts
        self.criteria: list[Any] = []

    def filter(self, *criteria: object) -> "FakeQuery":
        self.criteria.extend(criteria)
        return self

    def order_by(self, *_args: object) -> "FakeQuery":
        return self

    def all(self) -> list[PromptVersion]:
        return [prompt for prompt in self.prompts if self._matches_all(prompt)]

    def first(self) -> PromptVersion | None:
        return next(iter(self.all()), None)

    def _matches_all(self, prompt: PromptVersion) -> bool:
        return all(self._matches(prompt, criterion) for criterion in self.criteria)

    def _matches(self, prompt: PromptVersion, criterion: object) -> bool:
        key = criterion.left.key
        value = self._criterion_value(criterion)
        current = getattr(prompt, key)
        operator_name = criterion.operator.__name__
        if operator_name == "eq":
            return current == value
        if operator_name == "ne":
            return current != value
        raise AssertionError(f"Unsupported fake query operator: {operator_name}")

    def _criterion_value(self, criterion: object) -> object:
        right = criterion.right
        if hasattr(right, "value"):
            return right.value
        if right.__class__.__name__ == "True_":
            return True
        if right.__class__.__name__ == "False_":
            return False
        raise AssertionError(f"Unsupported fake query value: {right!r}")


class FakeSession:
    def __init__(self) -> None:
        self.prompts: list[PromptVersion] = []

    def query(self, _model: type[PromptVersion]) -> FakeQuery:
        return FakeQuery(self.prompts)

    def add(self, prompt: PromptVersion) -> None:
        if prompt not in self.prompts:
            self.prompts.append(prompt)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, prompt: PromptVersion) -> None:
        if prompt.id is None:
            prompt.id = uuid.uuid4()
        if prompt.created_at is None:
            prompt.created_at = datetime.now(UTC)
        if prompt.is_active is None:
            prompt.is_active = False


def make_prompt(
    *,
    agent_type: AgentType = AgentType.analyst,
    name: str = "Sales Analyst Agent",
    version: int = 1,
    is_active: bool = False,
) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=agent_type,
        name=name,
        version=version,
        template=f"{name} v{version}",
        is_active=is_active,
        notes=None,
        created_at=datetime.now(UTC),
    )


def test_create_list_and_get_prompt_version():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    created = client.post(
        "/prompt-versions",
        json={
            "agent_type": "analyst",
            "name": "Sales Analyst Agent",
            "version": 1,
            "template": "Extract structured sales insights.",
            "is_active": True,
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["agent_type"] == "analyst"
    assert body["is_active"] is True

    listed = client.get("/prompt-versions")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]

    detail = client.get(f"/prompt-versions/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Sales Analyst Agent"

    app.dependency_overrides.clear()


def test_list_prompt_versions_filters_by_agent_name_and_active_status():
    db = FakeSession()
    db.prompts.extend(
        [
            make_prompt(agent_type=AgentType.analyst, name="Sales Analyst Agent", is_active=True),
            make_prompt(agent_type=AgentType.reviewer, name="Reviewer Agent", is_active=True),
            make_prompt(agent_type=AgentType.analyst, name="Legacy Analyst Agent"),
        ]
    )
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.get(
        "/prompt-versions",
        params={
            "agent_type": "analyst",
            "name": "Sales Analyst Agent",
            "is_active": True,
        },
    )

    assert response.status_code == 200
    prompts = response.json()
    assert len(prompts) == 1
    assert prompts[0]["agent_type"] == "analyst"
    assert prompts[0]["name"] == "Sales Analyst Agent"
    assert prompts[0]["is_active"] is True

    app.dependency_overrides.clear()


def test_missing_prompt_version_returns_404():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.get(f"/prompt-versions/{uuid.uuid4()}")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_activate_prompt_deactivates_matching_prompt_only():
    db = FakeSession()
    previous = make_prompt(name="Sales Analyst Agent", version=1, is_active=True)
    next_version = make_prompt(name="Sales Analyst Agent", version=2)
    other_name = make_prompt(name="Other Analyst Agent", version=1, is_active=True)
    other_agent = make_prompt(
        agent_type=AgentType.reviewer,
        name="Reviewer Agent",
        version=1,
        is_active=True,
    )
    db.prompts.extend([previous, next_version, other_name, other_agent])
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(f"/prompt-versions/{next_version.id}/activate")

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert previous.is_active is False
    assert next_version.is_active is True
    assert other_name.is_active is True
    assert other_agent.is_active is True

    app.dependency_overrides.clear()


def test_activate_missing_prompt_version_returns_404():
    app.dependency_overrides[get_db] = lambda: FakeSession()
    client = TestClient(app)

    response = client.post(f"/prompt-versions/{uuid.uuid4()}/activate")

    assert response.status_code == 404
    app.dependency_overrides.clear()
