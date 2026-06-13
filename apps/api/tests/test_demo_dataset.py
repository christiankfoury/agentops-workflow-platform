import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.uploaded_input import UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.demo_dataset import DEMO_TITLE_PREFIX, seed_demo_dataset


class FakeQuery:
    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.criteria: list[Any] = []

    def filter(self, *criteria: object) -> "FakeQuery":
        self.criteria.extend(criteria)
        return self

    def first(self) -> Any | None:
        return next(iter(self.all()), None)

    def all(self) -> list[Any]:
        return [item for item in self.items if self._matches_all(item)]

    def _matches_all(self, item: Any) -> bool:
        return all(self._matches(item, criterion) for criterion in self.criteria)

    def _matches(self, item: Any, criterion: object) -> bool:
        key = criterion.left.key
        right = criterion.right
        value = right.value if hasattr(right, "value") else right.effective_value
        return getattr(item, key) == value


class FakeSession:
    def __init__(self) -> None:
        self.cases: list[EvaluationCase] = []
        self.uploaded_inputs: list[UploadedInput] = []
        self.runs: list[WorkflowRun] = []
        self.results: list[EvaluationResult] = []
        self.steps: list[AgentStep] = []
        self.commits = 0

    def query(self, model: type[Any]) -> FakeQuery:
        if model is EvaluationCase:
            return FakeQuery(self.cases)
        if model is UploadedInput:
            return FakeQuery(self.uploaded_inputs)
        if model is WorkflowRun:
            return FakeQuery(self.runs)
        if model is EvaluationResult:
            return FakeQuery(self.results)
        if model is AgentStep:
            return FakeQuery(self.steps)
        raise AssertionError(f"Unexpected model: {model}")

    def add(self, item: Any) -> None:
        collection = self._collection_for(item)
        if item not in collection:
            collection.append(item)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, item: Any) -> None:
        if item.id is None:
            item.id = uuid.uuid4()
        if item.created_at is None:
            item.created_at = datetime.now(UTC)

    def _collection_for(self, item: Any) -> list[Any]:
        if isinstance(item, EvaluationCase):
            return self.cases
        if isinstance(item, UploadedInput):
            return self.uploaded_inputs
        if isinstance(item, WorkflowRun):
            return self.runs
        if isinstance(item, EvaluationResult):
            return self.results
        if isinstance(item, AgentStep):
            return self.steps
        raise AssertionError(f"Unexpected item: {item}")


def test_seed_demo_dataset_creates_polished_demo_records():
    db = FakeSession()

    summary = seed_demo_dataset(db)

    assert summary.evaluation_cases == 32
    assert summary.uploaded_inputs == 33
    assert summary.workflow_runs == 65
    assert summary.evaluation_results == 65
    assert summary.agent_steps == 99
    assert len(db.cases) == 32
    assert len(db.uploaded_inputs) == 33
    assert len(db.runs) == 65
    assert len(db.results) == 65
    assert len(db.steps) == 99
    assert all(
        input_record.title.startswith(DEMO_TITLE_PREFIX)
        for input_record in db.uploaded_inputs
    )
    assert sum(case.workflow_type == WorkflowType.sales_report for case in db.cases) == 12
    assert {run.run_mode for run in db.runs} == {RunMode.baseline, RunMode.multi_agent}
    assert all(run.status == WorkflowStatus.completed for run in db.runs)
    assert all(result.status == EvaluationRunStatus.completed for result in db.results)
    assert all(step.status == AgentStepStatus.completed for step in db.steps)

    showcase_titles = {
        "[Demo] Reviewer issue correction path",
        "[Demo] Remediation impact showcase",
    }
    case_by_id = {case.id: case for case in db.cases}
    baseline_results = [
        result
        for result in db.results
        if result.run_mode == RunMode.baseline
        and case_by_id[result.evaluation_case_id].title not in showcase_titles
    ]
    multi_agent_results = [
        result for result in db.results if result.run_mode == RunMode.multi_agent
    ]
    assert all(result.factual_accuracy == 0.70 for result in baseline_results)
    default_multi_agent_results = [
        result
        for result in multi_agent_results
        if case_by_id[result.evaluation_case_id].title not in showcase_titles
    ]
    assert all(result.factual_accuracy == 0.92 for result in default_multi_agent_results)
    assert all(
        result.unsupported_claim_rate == 0.05 for result in default_multi_agent_results
    )
    assert all(result.prompt_version_summary_json for result in db.results)


def test_seed_demo_dataset_adds_reviewer_issue_and_impact_showcases():
    db = FakeSession()

    seed_demo_dataset(db)

    action_case = next(
        case for case in db.cases if case.title == "[Demo] Reviewer issue correction path"
    )
    action_results = [
        result for result in db.results if result.evaluation_case_id == action_case.id
    ]
    action_multi_result = next(
        result for result in action_results if result.run_mode == RunMode.multi_agent
    )
    action_reviewer_step = next(
        step
        for step in db.steps
        if step.workflow_run_id == action_multi_result.workflow_run_id
        and step.agent_type == "reviewer"
    )
    assert action_reviewer_step.output_json["issues"][0]["severity"] == "medium"

    impact_case = next(
        case for case in db.cases if case.title == "[Demo] Remediation impact showcase"
    )
    impact_multi_results = [
        result
        for result in db.results
        if result.evaluation_case_id == impact_case.id
        and result.run_mode == RunMode.multi_agent
    ]
    assert len(impact_multi_results) == 2
    corrected_result = max(impact_multi_results, key=lambda result: result.created_at)
    corrected_run = next(
        run for run in db.runs if run.id == corrected_result.workflow_run_id
    )
    corrected_input = next(
        input_record
        for input_record in db.uploaded_inputs
        if input_record.id == corrected_run.input_id
    )
    assert "Corrected comparison run guidance." in corrected_input.notes


def test_seed_demo_dataset_is_idempotent_and_refreshes_existing_records():
    db = FakeSession()
    seed_demo_dataset(db)
    first_input = db.uploaded_inputs[0]
    first_input.raw_text = "outdated"

    summary = seed_demo_dataset(db)

    assert summary.evaluation_cases == 32
    assert len(db.cases) == 32
    assert len(db.uploaded_inputs) == 33
    assert len(db.runs) == 65
    assert len(db.results) == 65
    assert len(db.steps) == 99
    assert first_input.raw_text != "outdated"
    assert db.commits == 4


def test_seed_demo_dataset_does_not_overwrite_non_demo_evaluation_results():
    db = FakeSession()
    existing_case = EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="Q1 regional growth and churn",
        input_text="outdated",
        expected_facts_json=[],
        expected_risks_json=[],
        expected_recommendations_json=[],
        created_at=datetime.now(UTC),
    )
    non_demo_result = EvaluationResult(
        id=uuid.uuid4(),
        evaluation_case_id=existing_case.id,
        workflow_run_id=uuid.uuid4(),
        run_mode=RunMode.baseline,
        status=EvaluationRunStatus.completed,
        factual_accuracy=0.11,
        unsupported_claim_rate=0.99,
        completeness_score=0.22,
        created_at=datetime.now(UTC),
    )
    db.cases.append(existing_case)
    db.results.append(non_demo_result)

    seed_demo_dataset(db)

    assert len(db.results) == 66
    assert non_demo_result.factual_accuracy == 0.11
    assert non_demo_result.unsupported_claim_rate == 0.99
    assert non_demo_result.completeness_score == 0.22


def test_seed_demo_dataset_can_seed_one_workflow_type():
    db = FakeSession()

    summary = seed_demo_dataset(db, {WorkflowType.sales_report})

    assert summary.evaluation_cases == 12
    assert summary.uploaded_inputs == 13
    assert summary.workflow_runs == 25
    assert summary.evaluation_results == 25
    assert summary.agent_steps == 39
    assert len(db.cases) == 32
    assert len(db.uploaded_inputs) == 13
    assert len(db.runs) == 25
    assert len(db.results) == 25
    assert {input_record.input_type.value for input_record in db.uploaded_inputs} == {
        WorkflowType.sales_report.value
    }


def test_demo_sales_endpoint_seeds_sales_demo_records():
    db = FakeSession()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post("/demo/sales-report")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "evaluation_cases": 12,
        "uploaded_inputs": 13,
        "workflow_runs": 25,
        "evaluation_results": 25,
        "agent_steps": 39,
    }
    assert len(db.uploaded_inputs) == 13
