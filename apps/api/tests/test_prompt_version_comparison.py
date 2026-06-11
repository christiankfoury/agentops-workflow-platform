import uuid

from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.workflow_run import RunMode
from src.services.prompt_version_comparison import compare_prompt_version_performance


def make_result(
    *,
    run_mode: RunMode = RunMode.multi_agent,
    summary: dict[str, object],
    factual_accuracy: float,
) -> EvaluationResult:
    return EvaluationResult(
        evaluation_case_id=uuid.uuid4(),
        run_mode=run_mode,
        status=EvaluationRunStatus.completed,
        prompt_version_summary_json=summary,
        factual_accuracy=factual_accuracy,
        unsupported_claim_rate=0.1,
        completeness_score=0.8,
        retry_count=1,
        cost=0.2,
        latency_ms=2000,
    )


def test_compare_prompt_version_performance_groups_by_mode_and_summary():
    first_summary = {"analyst": "prompt-a", "reviewer": "prompt-r1", "writer": "prompt-w"}
    second_summary = {"analyst": "prompt-b", "reviewer": "prompt-r1", "writer": "prompt-w"}
    results = [
        make_result(summary=first_summary, factual_accuracy=0.8),
        make_result(summary=first_summary, factual_accuracy=1.0),
        make_result(summary=second_summary, factual_accuracy=0.6),
        make_result(
            run_mode=RunMode.baseline,
            summary={"baseline": None},
            factual_accuracy=0.5,
        ),
    ]

    comparisons = compare_prompt_version_performance(results)

    assert len(comparisons) == 3
    baseline = comparisons[0]
    assert baseline.run_mode == RunMode.baseline
    assert baseline.prompt_version_summary == {"baseline": None}
    assert baseline.factual_accuracy == 0.5
    first = comparisons[1]
    assert first.prompt_version_summary == first_summary
    assert first.run_count == 2
    assert first.factual_accuracy == 0.9
    second = comparisons[2]
    assert second.prompt_version_summary == second_summary
    assert second.run_count == 1
    assert second.factual_accuracy == 0.6
