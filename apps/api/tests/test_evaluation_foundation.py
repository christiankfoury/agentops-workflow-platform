import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.evaluation_comparisons import build_evaluation_comparisons
from src.services.evaluation_metrics import calculate_sales_evaluation_scores
from src.services.evaluation_runner import run_sales_evaluation_case
from tests.test_evaluation_runner import (
    EvaluationFakeSession,
    EvaluationLLMClient,
    make_agent_prompt,
    make_case,
)
from tests.test_sales_analyst_api import make_prompt
from tests.test_sales_reviewer_api import make_reviewer_prompt
from tests.test_sales_writer_api import make_writer_prompt


def make_scoring_case() -> EvaluationCase:
    return EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="Q2 sales review",
        input_text="Revenue grew 12%. Enterprise churn rose. Expansion pipeline increased.",
        expected_facts_json=[
            "Revenue grew 12%",
            "Expansion pipeline increased",
        ],
        expected_risks_json=["Enterprise churn rose"],
        expected_recommendations_json=["Prioritize enterprise retention"],
        created_at=datetime.now(UTC),
    )


def make_comparison_case() -> EvaluationCase:
    return EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="Comparison case",
        input_text="Revenue grew 12%.",
        expected_facts_json=["Revenue grew 12%"],
        expected_risks_json=[],
        expected_recommendations_json=[],
        created_at=datetime.now(UTC),
    )


def make_run(*, run_mode: RunMode, final_output: str, created_at: datetime) -> WorkflowRun:
    return WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        run_mode=run_mode,
        status=WorkflowStatus.completed,
        final_output=final_output,
        total_cost=0.2 if run_mode == RunMode.multi_agent else 0.05,
        latency_ms=3000 if run_mode == RunMode.multi_agent else 1000,
        retry_count=0,
        created_at=created_at,
        completed_at=created_at,
    )


def make_result(
    *,
    case_id: uuid.UUID,
    run: WorkflowRun,
    accuracy: float,
    unsupported_claim_rate: float,
    completeness: float,
    created_at: datetime,
    judge_notes: str = "Captured expected deterministic checks.",
    status: EvaluationRunStatus = EvaluationRunStatus.completed,
) -> EvaluationResult:
    return EvaluationResult(
        id=uuid.uuid4(),
        evaluation_case_id=case_id,
        workflow_run_id=run.id,
        run_mode=run.run_mode,
        status=status,
        factual_accuracy=accuracy,
        unsupported_claim_rate=unsupported_claim_rate,
        completeness_score=completeness,
        judge_notes=judge_notes,
        cost=run.total_cost,
        latency_ms=run.latency_ms,
        created_at=created_at,
    )


def test_evaluation_score_math_tracks_accuracy_completeness_and_unsupported_claims():
    scores = calculate_sales_evaluation_scores(
        make_scoring_case(),
        (
            "Revenue grew 12%. Enterprise churn rose. "
            "Prioritize enterprise retention. EMEA revenue doubled."
        ),
    )

    assert scores.factual_accuracy == 0.5
    assert scores.completeness_score == 0.75
    assert scores.unsupported_claim_rate == pytest.approx(0.25)
    assert scores.deterministic_notes == "Captured 3/4 expected deterministic checks."


def test_evaluation_score_math_rejects_claims_with_unsupported_numbers():
    scores = calculate_sales_evaluation_scores(
        make_scoring_case(),
        "Revenue grew 12%. Revenue grew 99%. Enterprise churn rose.",
    )

    assert scores.factual_accuracy == 0.5
    assert scores.completeness_score == 0.5
    assert scores.unsupported_claim_rate == pytest.approx(1 / 3, abs=0.0001)


def test_evaluation_comparison_uses_latest_completed_baseline_and_multi_agent_pair():
    case = make_comparison_case()
    now = datetime.now(UTC)
    old_baseline = make_run(
        run_mode=RunMode.baseline,
        final_output="Old baseline output",
        created_at=now - timedelta(days=2),
    )
    latest_baseline = make_run(
        run_mode=RunMode.baseline,
        final_output="Latest baseline output",
        created_at=now,
    )
    failed_multi_agent = make_run(
        run_mode=RunMode.multi_agent,
        final_output="Failed multi-agent output",
        created_at=now + timedelta(minutes=1),
    )
    latest_multi_agent = make_run(
        run_mode=RunMode.multi_agent,
        final_output="Latest multi-agent output",
        created_at=now - timedelta(hours=1),
    )
    reviewer_step = AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=latest_multi_agent.id,
        agent_name="Reviewer Agent",
        agent_type="reviewer",
        step_order=2,
        status=AgentStepStatus.completed,
        output_json={"issues": [{"claim": "Unsupported uplift", "severity": "medium"}]},
        created_at=now,
        completed_at=now,
    )

    comparisons = build_evaluation_comparisons(
        [case],
        [
            make_result(
                case_id=case.id,
                run=old_baseline,
                accuracy=0.4,
                unsupported_claim_rate=0.5,
                completeness=0.4,
                created_at=now - timedelta(days=2),
            ),
            make_result(
                case_id=case.id,
                run=latest_baseline,
                accuracy=0.6,
                unsupported_claim_rate=0.25,
                completeness=0.6,
                created_at=now,
            ),
            make_result(
                case_id=case.id,
                run=failed_multi_agent,
                accuracy=0.95,
                unsupported_claim_rate=0.0,
                completeness=0.95,
                created_at=now + timedelta(minutes=1),
                status=EvaluationRunStatus.failed,
            ),
            make_result(
                case_id=case.id,
                run=latest_multi_agent,
                accuracy=0.9,
                unsupported_claim_rate=0.0,
                completeness=0.9,
                created_at=now - timedelta(hours=1),
            ),
        ],
        [old_baseline, latest_baseline, failed_multi_agent, latest_multi_agent],
        [reviewer_step],
    )

    assert len(comparisons) == 1
    comparison = comparisons[0]
    assert comparison.baseline.final_output == "Latest baseline output"
    assert comparison.baseline.factual_accuracy == 0.6
    assert comparison.baseline.judge_notes == "Captured expected deterministic checks."
    assert comparison.multi_agent.final_output == "Latest multi-agent output"
    assert comparison.multi_agent.factual_accuracy == 0.9
    assert comparison.multi_agent.judge_notes == "Captured expected deterministic checks."
    assert comparison.reviewer_issues == [{"claim": "Unsupported uplift", "severity": "medium"}]
    assert comparison.cost_difference == pytest.approx(0.15)
    assert comparison.latency_difference_ms == 2000


def test_evaluation_runner_stores_multi_agent_scores_and_metadata():
    db = EvaluationFakeSession()
    db.prompts.extend(
        [
            make_prompt(),
            make_reviewer_prompt(),
            make_writer_prompt(),
            make_agent_prompt(AgentType.router),
        ]
    )

    result = run_sales_evaluation_case(
        db,
        make_case(),
        RunMode.multi_agent,
        EvaluationLLMClient(),
    )

    assert result.status == EvaluationRunStatus.completed
    assert result.workflow_run_id == db.runs[0].id
    assert result.factual_accuracy == 1.0
    assert result.unsupported_claim_rate == 0.0
    assert result.completeness_score == 0.3333
    assert result.judge_notes == "Captured 1/3 expected deterministic checks."
    assert result.router_correct is True
    assert result.router_detected_workflow_type == WorkflowType.sales_report
    assert result.human_approval_required is True
    assert result.human_approved is True
    assert result.prompt_version_summary_json == {
        "analyst": str(db.prompts[0].id),
        "reviewer": str(db.prompts[1].id),
        "writer": str(db.prompts[2].id),
    }
