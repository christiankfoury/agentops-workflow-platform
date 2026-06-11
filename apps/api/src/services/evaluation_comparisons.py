import uuid
from dataclasses import dataclass
from typing import Any

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.workflow_run import RunMode, WorkflowRun
from src.schemas.evaluation import (
    EvaluationComparisonRead,
    EvaluationComparisonRunRead,
)


@dataclass(frozen=True)
class _ResultPair:
    baseline: EvaluationResult
    multi_agent: EvaluationResult


def build_evaluation_comparisons(
    cases: list[EvaluationCase],
    results: list[EvaluationResult],
    runs: list[WorkflowRun],
    steps: list[AgentStep],
) -> list[EvaluationComparisonRead]:
    case_by_id = {case.id: case for case in cases}
    run_by_id = {run.id: run for run in runs}
    latest_pairs = _latest_completed_result_pairs(results)
    steps_by_run_id = _steps_by_run_id(steps)

    comparisons: list[EvaluationComparisonRead] = []
    for case_id, pair in latest_pairs.items():
        case = case_by_id.get(case_id)
        baseline_run = run_by_id.get(pair.baseline.workflow_run_id)
        multi_agent_run = run_by_id.get(pair.multi_agent.workflow_run_id)
        if case is None or baseline_run is None or multi_agent_run is None:
            continue

        baseline = _comparison_run(pair.baseline, baseline_run)
        multi_agent = _comparison_run(pair.multi_agent, multi_agent_run)
        comparisons.append(
            EvaluationComparisonRead(
                evaluation_case_id=case.id,
                workflow_type=case.workflow_type,
                title=case.title,
                input_preview=_preview(case.input_text),
                baseline=baseline,
                multi_agent=multi_agent,
                reviewer_issues=_latest_reviewer_issues(
                    steps_by_run_id.get(multi_agent_run.id, [])
                ),
                cost_difference=multi_agent.cost - baseline.cost,
                latency_difference_ms=multi_agent.latency_ms - baseline.latency_ms,
            )
        )

    return sorted(comparisons, key=lambda comparison: comparison.title)


def _latest_completed_result_pairs(
    results: list[EvaluationResult],
) -> dict[uuid.UUID, _ResultPair]:
    grouped: dict[uuid.UUID, dict[RunMode, EvaluationResult]] = {}
    sorted_results = sorted(results, key=lambda result: result.created_at, reverse=True)
    for result in sorted_results:
        if (
            result.status != EvaluationRunStatus.completed
            or result.workflow_run_id is None
            or result.run_mode not in {RunMode.baseline, RunMode.multi_agent}
        ):
            continue
        mode_results = grouped.setdefault(result.evaluation_case_id, {})
        mode_results.setdefault(result.run_mode, result)

    return {
        case_id: _ResultPair(
            baseline=mode_results[RunMode.baseline],
            multi_agent=mode_results[RunMode.multi_agent],
        )
        for case_id, mode_results in grouped.items()
        if RunMode.baseline in mode_results and RunMode.multi_agent in mode_results
    }


def _comparison_run(
    result: EvaluationResult,
    run: WorkflowRun,
) -> EvaluationComparisonRunRead:
    return EvaluationComparisonRunRead(
        workflow_run_id=run.id,
        final_output=run.final_output,
        factual_accuracy=result.factual_accuracy,
        unsupported_claim_rate=result.unsupported_claim_rate,
        completeness_score=result.completeness_score,
        cost=result.cost if result.cost is not None else run.total_cost or 0.0,
        latency_ms=result.latency_ms if result.latency_ms is not None else run.latency_ms or 0,
    )


def _steps_by_run_id(steps: list[AgentStep]) -> dict[uuid.UUID, list[AgentStep]]:
    grouped: dict[uuid.UUID, list[AgentStep]] = {}
    for step in steps:
        grouped.setdefault(step.workflow_run_id, []).append(step)
    return grouped


def _latest_reviewer_issues(steps: list[AgentStep]) -> list[dict[str, Any]]:
    reviewer_steps = [
        step
        for step in steps
        if step.agent_type == "reviewer"
        and step.status == AgentStepStatus.completed
        and isinstance(step.output_json, dict)
    ]
    if not reviewer_steps:
        return []

    latest = max(
        reviewer_steps,
        key=lambda step: (step.completed_at or step.created_at, step.step_order),
    )
    issues = latest.output_json.get("issues") if latest.output_json is not None else None
    if not isinstance(issues, list):
        return []
    return [issue for issue in issues if isinstance(issue, dict)]


def _preview(value: str, limit: int = 280) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}..."
