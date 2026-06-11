import uuid
from datetime import UTC, datetime

import pytest

from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.workflow_run import RunMode, WorkflowType
from src.services.evaluation_metrics import (
    calculate_sales_evaluation_scores,
    summarize_evaluation_results,
)


def make_case() -> EvaluationCase:
    return EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="Q1 Sales Report",
        input_text="Revenue increased 12%. Enterprise churn increased.",
        expected_facts_json=[
            "Revenue increased 12%",
            "North America was strongest region",
        ],
        expected_risks_json=["Enterprise churn increased"],
        expected_recommendations_json=["Prioritize enterprise retention"],
        created_at=datetime.now(UTC),
    )


def test_calculate_sales_evaluation_scores_counts_expected_items():
    scores = calculate_sales_evaluation_scores(
        make_case(),
        (
            "Revenue increased 12%. Enterprise churn increased. "
            "Prioritize enterprise retention."
        ),
    )

    assert scores.factual_accuracy == 0.5
    assert scores.completeness_score == 0.75
    assert scores.unsupported_claim_rate == 0.0


def test_calculate_sales_evaluation_scores_flags_unsupported_claims():
    scores = calculate_sales_evaluation_scores(
        make_case(),
        "Revenue increased 12%. EMEA doubled revenue.",
    )

    assert scores.factual_accuracy == 0.5
    assert scores.completeness_score == 0.25
    assert scores.unsupported_claim_rate == pytest.approx(0.5)


def test_calculate_sales_evaluation_scores_ignores_headings_and_decimal_splits():
    case = EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="Q1 Sales Report",
        input_text="Revenue increased from $4.2M to $4.7M.",
        expected_facts_json=["Revenue increased from $4.2M to $4.7M"],
        expected_risks_json=[],
        expected_recommendations_json=[],
        created_at=datetime.now(UTC),
    )

    scores = calculate_sales_evaluation_scores(
        case,
        "Executive Summary\n\nRevenue increased from $4.2M to $4.7M.\n\nKey Risks:\nNone.",
    )

    assert scores.unsupported_claim_rate == 0.0


def test_calculate_sales_evaluation_scores_handles_empty_output():
    scores = calculate_sales_evaluation_scores(make_case(), "")

    assert scores.factual_accuracy == 0.0
    assert scores.completeness_score == 0.0
    assert scores.unsupported_claim_rate == 0.0


def test_summarize_evaluation_results_averages_completed_runs():
    first = EvaluationResult(
        evaluation_case_id=uuid.uuid4(),
        run_mode=RunMode.baseline,
        status=EvaluationRunStatus.completed,
        factual_accuracy=0.5,
        unsupported_claim_rate=0.2,
        completeness_score=0.4,
        router_confidence=0.9,
        router_correct=True,
        human_approval_required=False,
        retry_count=0,
        cost=0.1,
        latency_ms=1000,
    )
    second = EvaluationResult(
        evaluation_case_id=uuid.uuid4(),
        run_mode=RunMode.multi_agent,
        status=EvaluationRunStatus.completed,
        factual_accuracy=1.0,
        unsupported_claim_rate=0.0,
        completeness_score=0.8,
        router_confidence=0.7,
        router_correct=False,
        human_approval_required=True,
        human_approved=True,
        retry_count=1,
        cost=0.3,
        latency_ms=3000,
    )
    failed = EvaluationResult(
        evaluation_case_id=uuid.uuid4(),
        run_mode=RunMode.multi_agent,
        status=EvaluationRunStatus.failed,
        factual_accuracy=0.0,
        unsupported_claim_rate=1.0,
        completeness_score=0.0,
        human_approval_required=True,
        human_approved=False,
        retry_count=2,
        cost=9.0,
        latency_ms=9000,
    )

    summary = summarize_evaluation_results([first, second, failed])

    assert summary.run_count == 2
    assert summary.factual_accuracy == 0.75
    assert summary.unsupported_claim_rate == 0.1
    assert summary.completeness_score == 0.6
    assert summary.router_accuracy == 0.5
    assert summary.average_router_confidence == 0.8
    assert summary.human_approval_rate == 1.0
    assert summary.average_cost == 0.2
    assert summary.average_latency_ms == 2000.0
    assert summary.average_retries == 0.5
