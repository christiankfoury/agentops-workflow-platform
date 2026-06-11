import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.workflow_run import RunMode, WorkflowType


class FakeQuery:
    def __init__(self, items: list[EvaluationResult] | list[EvaluationCase]) -> None:
        self.items = items

    def order_by(self, *_args: object) -> "FakeQuery":
        self.items = sorted(self.items, key=lambda item: item.created_at, reverse=True)
        return self

    def all(self) -> list[EvaluationResult] | list[EvaluationCase]:
        return self.items


class FakeSession:
    def __init__(self) -> None:
        self.results: list[EvaluationResult] = []
        self.cases: list[EvaluationCase] = []

    def query(self, model: type[EvaluationResult] | type[EvaluationCase]) -> FakeQuery:
        if model is EvaluationCase:
            return FakeQuery(self.cases)
        if model is EvaluationResult:
            return FakeQuery(self.results)
        raise AssertionError(f"Unexpected model: {model}")


def make_case(workflow_type: WorkflowType = WorkflowType.sales_report) -> EvaluationCase:
    return EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=workflow_type,
        title="Evaluation case",
        input_text="input",
        expected_facts_json=[],
        expected_risks_json=[],
        expected_recommendations_json=[],
        created_at=datetime.now(UTC),
    )


def make_result(
    *,
    run_mode: RunMode,
    evaluation_case_id: uuid.UUID | None = None,
    status: EvaluationRunStatus = EvaluationRunStatus.completed,
    factual_accuracy: float = 1.0,
    unsupported_claim_rate: float = 0.0,
    completeness_score: float = 1.0,
    human_approval_required: bool = False,
    human_approved: bool | None = None,
    retry_count: int = 0,
    cost: float = 0.1,
    latency_ms: int = 1000,
    created_at: datetime | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        id=uuid.uuid4(),
        evaluation_case_id=evaluation_case_id or uuid.uuid4(),
        workflow_run_id=uuid.uuid4(),
        run_mode=run_mode,
        status=status,
        factual_accuracy=factual_accuracy,
        unsupported_claim_rate=unsupported_claim_rate,
        completeness_score=completeness_score,
        human_approval_required=human_approval_required,
        human_approved=human_approved,
        retry_count=retry_count,
        cost=cost,
        latency_ms=latency_ms,
        created_at=created_at or datetime.now(UTC),
    )


def override_db(db: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: db


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_list_evaluation_results_returns_newest_first():
    db = FakeSession()
    older = make_result(
        run_mode=RunMode.baseline,
        created_at=datetime.now(UTC) - timedelta(days=1),
    )
    newer = make_result(run_mode=RunMode.multi_agent)
    db.results.extend([older, newer])
    override_db(db)
    client = TestClient(app)

    response = client.get("/evaluation-results")

    assert response.status_code == 200
    body = response.json()
    assert [result["id"] for result in body] == [str(newer.id), str(older.id)]
    clear_overrides()


def test_get_evaluation_summary_groups_by_workflow_type_and_run_mode():
    db = FakeSession()
    sales_case = make_case(WorkflowType.sales_report)
    feedback_case = make_case(WorkflowType.customer_feedback)
    db.cases.extend([sales_case, feedback_case])
    db.results.extend(
        [
            make_result(
                run_mode=RunMode.baseline,
                evaluation_case_id=sales_case.id,
                factual_accuracy=0.5,
                cost=0.1,
            ),
            make_result(
                run_mode=RunMode.multi_agent,
                evaluation_case_id=sales_case.id,
                factual_accuracy=0.9,
                completeness_score=0.8,
                human_approval_required=True,
                human_approved=True,
                retry_count=1,
                cost=0.3,
                latency_ms=3000,
            ),
            make_result(
                run_mode=RunMode.multi_agent,
                evaluation_case_id=sales_case.id,
                status=EvaluationRunStatus.failed,
                factual_accuracy=0.0,
                cost=9.0,
            ),
            make_result(
                run_mode=RunMode.baseline,
                evaluation_case_id=feedback_case.id,
                factual_accuracy=0.7,
                cost=0.2,
            ),
        ]
    )
    override_db(db)
    client = TestClient(app)

    response = client.get("/evaluation-results/summary")

    assert response.status_code == 200
    body = {
        (item["workflow_type"], item["run_mode"]): item for item in response.json()
    }
    assert body[("sales_report", "baseline")]["run_count"] == 1
    assert body[("sales_report", "baseline")]["factual_accuracy"] == 0.5
    assert body[("sales_report", "baseline")]["average_cost"] == 0.1
    assert body[("sales_report", "multi_agent")]["run_count"] == 1
    assert body[("sales_report", "multi_agent")]["factual_accuracy"] == 0.9
    assert body[("sales_report", "multi_agent")]["completeness_score"] == 0.8
    assert body[("sales_report", "multi_agent")]["human_approval_rate"] == 1.0
    assert body[("sales_report", "multi_agent")]["average_retries"] == 1.0
    assert body[("customer_feedback", "baseline")]["run_count"] == 1
    assert body[("customer_feedback", "baseline")]["factual_accuracy"] == 0.7
    assert body[("customer_feedback", "multi_agent")]["run_count"] == 0
    clear_overrides()
