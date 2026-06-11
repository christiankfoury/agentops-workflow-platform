import uuid
from datetime import UTC, datetime
from typing import Any

from src.models.evaluation_case import EvaluationCase
from src.models.workflow_run import WorkflowType
from src.services.evaluation_cases import (
    DEFAULT_CUSTOMER_FEEDBACK_EVALUATION_CASES,
    DEFAULT_INCIDENT_EVALUATION_CASES,
    DEFAULT_SALES_EVALUATION_CASES,
    seed_default_evaluation_cases,
)


class FakeQuery:
    def __init__(self, items: list[EvaluationCase]) -> None:
        self.items = items
        self.criteria: list[Any] = []

    def filter(self, *criteria: object) -> "FakeQuery":
        self.criteria.extend(criteria)
        return self

    def first(self) -> EvaluationCase | None:
        return next(iter(self.all()), None)

    def all(self) -> list[EvaluationCase]:
        return [item for item in self.items if self._matches_all(item)]

    def _matches_all(self, item: EvaluationCase) -> bool:
        return all(self._matches(item, criterion) for criterion in self.criteria)

    def _matches(self, item: EvaluationCase, criterion: object) -> bool:
        key = criterion.left.key
        right = criterion.right
        value = right.value if hasattr(right, "value") else right.effective_value
        return getattr(item, key) == value


class FakeSession:
    def __init__(self) -> None:
        self.cases: list[EvaluationCase] = []
        self.commits = 0

    def query(self, model: type[EvaluationCase]) -> FakeQuery:
        assert model is EvaluationCase
        return FakeQuery(self.cases)

    def add(self, item: EvaluationCase) -> None:
        if item not in self.cases:
            self.cases.append(item)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, item: EvaluationCase) -> None:
        if item.id is None:
            item.id = uuid.uuid4()
        if item.created_at is None:
            item.created_at = datetime.now(UTC)


def test_seed_default_evaluation_cases_creates_all_workflow_cases():
    db = FakeSession()

    cases = seed_default_evaluation_cases(db)

    assert len(cases) == 30
    assert len(db.cases) == 30
    assert db.commits == 1
    assert sum(case.workflow_type == WorkflowType.sales_report for case in cases) == 10
    assert sum(case.workflow_type == WorkflowType.customer_feedback for case in cases) == 10
    assert sum(case.workflow_type == WorkflowType.incident_log for case in cases) == 10
    assert all(case.expected_facts_json for case in cases)
    assert all(case.expected_risks_json for case in cases)
    assert all(case.expected_recommendations_json for case in cases)
    assert cases[0].expected_output_notes == "Executive summary should not say churn doubled."
    customer_cases = [
        case for case in cases if case.workflow_type == WorkflowType.customer_feedback
    ]
    assert all(case.expected_themes_json for case in customer_cases)
    incident_cases = [case for case in cases if case.workflow_type == WorkflowType.incident_log]
    assert all(case.expected_timeline_json for case in incident_cases)


def test_seed_default_evaluation_cases_is_idempotent_and_updates_existing_case():
    db = FakeSession()
    existing = EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title=DEFAULT_SALES_EVALUATION_CASES[0]["title"],
        input_text="outdated",
        expected_facts_json=[],
        expected_risks_json=[],
        expected_recommendations_json=[],
        created_at=datetime.now(UTC),
    )
    db.cases.append(existing)

    cases = seed_default_evaluation_cases(db)

    assert len(cases) == 30
    assert len(db.cases) == 30
    assert db.cases[0] is existing
    assert existing.input_text == DEFAULT_SALES_EVALUATION_CASES[0]["input_text"]
    assert existing.expected_facts_json == DEFAULT_SALES_EVALUATION_CASES[0][
        "expected_facts_json"
    ]


def test_seed_default_evaluation_cases_updates_existing_customer_feedback_case():
    db = FakeSession()
    existing = EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.customer_feedback,
        title=DEFAULT_CUSTOMER_FEEDBACK_EVALUATION_CASES[0]["title"],
        input_text="outdated",
        expected_facts_json=[],
        expected_risks_json=[],
        expected_recommendations_json=[],
        expected_themes_json=[],
        created_at=datetime.now(UTC),
    )
    db.cases.append(existing)

    seed_default_evaluation_cases(db)

    assert len(db.cases) == 30
    assert db.cases[0] is existing
    assert existing.input_text == DEFAULT_CUSTOMER_FEEDBACK_EVALUATION_CASES[0]["input_text"]
    assert existing.expected_themes_json == DEFAULT_CUSTOMER_FEEDBACK_EVALUATION_CASES[0][
        "expected_themes_json"
    ]


def test_seed_default_evaluation_cases_updates_existing_incident_case():
    db = FakeSession()
    existing = EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.incident_log,
        title=DEFAULT_INCIDENT_EVALUATION_CASES[0]["title"],
        input_text="outdated",
        expected_facts_json=[],
        expected_risks_json=[],
        expected_recommendations_json=[],
        expected_timeline_json=[],
        created_at=datetime.now(UTC),
    )
    db.cases.append(existing)

    seed_default_evaluation_cases(db)

    assert len(db.cases) == 30
    assert db.cases[0] is existing
    assert existing.input_text == DEFAULT_INCIDENT_EVALUATION_CASES[0]["input_text"]
    assert existing.expected_timeline_json == DEFAULT_INCIDENT_EVALUATION_CASES[0][
        "expected_timeline_json"
    ]
