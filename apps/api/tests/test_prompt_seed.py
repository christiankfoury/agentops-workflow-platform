import uuid
from datetime import UTC, datetime
from typing import Any

from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.services.prompt_versions import DEFAULT_PROMPTS, seed_default_prompt_versions


class FakeQuery:
    def __init__(self, prompts: list[PromptVersion]) -> None:
        self.prompts = prompts
        self.criteria: list[Any] = []

    def filter(self, *criteria: object) -> "FakeQuery":
        self.criteria.extend(criteria)
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

    def refresh(self, prompt: PromptVersion) -> None:
        if prompt.id is None:
            prompt.id = uuid.uuid4()
        if prompt.created_at is None:
            prompt.created_at = datetime.now(UTC)


def test_seed_default_prompt_versions_is_idempotent():
    db = FakeSession()

    first_seed = seed_default_prompt_versions(db)
    second_seed = seed_default_prompt_versions(db)

    assert len(first_seed) == len(DEFAULT_PROMPTS)
    assert len(second_seed) == len(DEFAULT_PROMPTS)
    assert len(db.prompts) == len(DEFAULT_PROMPTS)


def test_seed_default_prompt_versions_marks_v1_prompts_active():
    db = FakeSession()

    seed_default_prompt_versions(db)

    assert {prompt.agent_type for prompt in db.prompts} == set(AgentType)
    assert all(prompt.version == 1 for prompt in db.prompts)
    assert all(prompt.is_active for prompt in db.prompts)


def test_seed_default_prompt_versions_preserves_active_custom_prompt():
    db = FakeSession()
    custom_writer = PromptVersion(
        id=uuid.uuid4(),
        agent_type=AgentType.writer,
        name="Evidence Strict Writer",
        version=2,
        template="Strict writer",
        is_active=True,
        notes=None,
        created_at=datetime.now(UTC),
    )
    db.prompts.append(custom_writer)

    seed_default_prompt_versions(db)

    default_writer = next(
        prompt
        for prompt in db.prompts
        if prompt.agent_type == AgentType.writer and prompt.version == 1
    )
    assert custom_writer.is_active is True
    assert default_writer.is_active is False
