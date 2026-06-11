import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType


class FakeQuery:
    def __init__(
        self,
        items: list[EvaluationCase]
        | list[EvaluationResult]
        | list[WorkflowRun]
        | list[AgentStep],
    ) -> None:
        self.items = items

    def all(
        self,
    ) -> list[EvaluationCase] | list[EvaluationResult] | list[WorkflowRun] | list[AgentStep]:
        return self.items


class FakeSession:
    def __init__(self) -> None:
        self.cases: list[EvaluationCase] = []
        self.results: list[EvaluationResult] = []
        self.runs: list[WorkflowRun] = []
        self.steps: list[AgentStep] = []

    def query(
        self,
        model: type[EvaluationCase]
        | type[EvaluationResult]
        | type[WorkflowRun]
        | type[AgentStep],
    ) -> FakeQuery:
        if model is EvaluationCase:
            return FakeQuery(self.cases)
        if model is EvaluationResult:
            return FakeQuery(self.results)
        if model is WorkflowRun:
            return FakeQuery(self.runs)
        if model is AgentStep:
            return FakeQuery(self.steps)
        raise AssertionError(f"Unexpected model: {model}")


def make_case() -> EvaluationCase:
    return EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="Q1 sales retention risk",
        input_text="Revenue grew 12% but enterprise churn increased in EMEA.",
        expected_facts_json=[],
        expected_risks_json=[],
        expected_recommendations_json=[],
        created_at=datetime.now(UTC),
    )


def make_run(
    *,
    run_mode: RunMode,
    final_output: str,
    total_cost: float,
    latency_ms: int,
) -> WorkflowRun:
    return WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        run_mode=run_mode,
        status=WorkflowStatus.completed,
        final_output=final_output,
        total_cost=total_cost,
        latency_ms=latency_ms,
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def make_result(
    *,
    case_id: uuid.UUID,
    run: WorkflowRun,
    factual_accuracy: float,
    cost: float,
    latency_ms: int,
    created_at: datetime | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        id=uuid.uuid4(),
        evaluation_case_id=case_id,
        workflow_run_id=run.id,
        run_mode=run.run_mode,
        status=EvaluationRunStatus.completed,
        factual_accuracy=factual_accuracy,
        unsupported_claim_rate=0.1,
        completeness_score=0.8,
        cost=cost,
        latency_ms=latency_ms,
        created_at=created_at or datetime.now(UTC),
    )


def make_reviewer_step(run_id: uuid.UUID) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Reviewer Agent",
        agent_type="reviewer",
        step_order=2,
        status=AgentStepStatus.completed,
        output_json={
            "issues": [
                {
                    "claim": "Enterprise churn doubled",
                    "problem": "Source only says churn increased.",
                    "severity": "high",
                }
            ]
        },
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def override_db(db: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: db


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_get_evaluation_comparisons_pairs_latest_completed_results():
    db = FakeSession()
    case = make_case()
    baseline_run = make_run(
        run_mode=RunMode.baseline,
        final_output="Baseline summary",
        total_cost=0.04,
        latency_ms=1000,
    )
    multi_agent_run = make_run(
        run_mode=RunMode.multi_agent,
        final_output="Reviewed executive summary",
        total_cost=0.12,
        latency_ms=3000,
    )
    stale_multi_agent_run = make_run(
        run_mode=RunMode.multi_agent,
        final_output="Older summary",
        total_cost=0.08,
        latency_ms=2500,
    )
    db.cases.append(case)
    db.runs.extend([baseline_run, multi_agent_run, stale_multi_agent_run])
    db.results.extend(
        [
            make_result(
                case_id=case.id,
                run=baseline_run,
                factual_accuracy=0.7,
                cost=0.04,
                latency_ms=1000,
            ),
            make_result(
                case_id=case.id,
                run=stale_multi_agent_run,
                factual_accuracy=0.75,
                cost=0.08,
                latency_ms=2500,
                created_at=datetime.now(UTC) - timedelta(days=1),
            ),
            make_result(
                case_id=case.id,
                run=multi_agent_run,
                factual_accuracy=0.9,
                cost=0.12,
                latency_ms=3000,
            ),
        ]
    )
    db.steps.append(make_reviewer_step(multi_agent_run.id))
    override_db(db)
    client = TestClient(app)

    response = client.get("/evaluation-results/comparisons")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    comparison = body[0]
    assert comparison["title"] == "Q1 sales retention risk"
    assert comparison["baseline"]["final_output"] == "Baseline summary"
    assert comparison["multi_agent"]["final_output"] == "Reviewed executive summary"
    assert comparison["multi_agent"]["factual_accuracy"] == 0.9
    assert comparison["reviewer_issues"][0]["severity"] == "high"
    assert comparison["cost_difference"] == pytest.approx(0.08)
    assert comparison["latency_difference_ms"] == 2000
    clear_overrides()
