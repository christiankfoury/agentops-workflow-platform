import uuid
from dataclasses import dataclass
from typing import Any

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.uploaded_input import UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun
from src.schemas.evaluation import (
    EvaluationComparisonRead,
    EvaluationComparisonRunRead,
    RemediationImpactRead,
)


@dataclass(frozen=True)
class _ResultPair:
    baseline: EvaluationResult
    multi_agent: EvaluationResult
    previous_multi_agent: EvaluationResult | None = None


CORRECTED_RUN_MARKER = "Corrected comparison run guidance."


def build_evaluation_comparisons(
    cases: list[EvaluationCase],
    results: list[EvaluationResult],
    runs: list[WorkflowRun],
    steps: list[AgentStep],
    uploaded_inputs: list[UploadedInput] | None = None,
) -> list[EvaluationComparisonRead]:
    case_by_id = {case.id: case for case in cases}
    run_by_id = {run.id: run for run in runs}
    input_by_id = {uploaded_input.id: uploaded_input for uploaded_input in uploaded_inputs or []}
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
        reviewer_issues = _latest_reviewer_issues(steps_by_run_id.get(multi_agent_run.id, []))
        comparisons.append(
            EvaluationComparisonRead(
                evaluation_case_id=case.id,
                workflow_type=case.workflow_type,
                title=case.title,
                input_preview=_preview(case.input_text),
                baseline=baseline,
                multi_agent=multi_agent,
                reviewer_issues=reviewer_issues,
                cost_difference=multi_agent.cost - baseline.cost,
                latency_difference_ms=multi_agent.latency_ms - baseline.latency_ms,
                remediation_impact=_remediation_impact(
                    pair=pair,
                    latest_run=multi_agent_run,
                    run_by_id=run_by_id,
                    input_by_id=input_by_id,
                    steps_by_run_id=steps_by_run_id,
                    current_reviewer_issues=reviewer_issues,
                ),
            )
        )

    return sorted(comparisons, key=lambda comparison: comparison.title)


def _latest_completed_result_pairs(
    results: list[EvaluationResult],
) -> dict[uuid.UUID, _ResultPair]:
    grouped: dict[uuid.UUID, dict[RunMode, list[EvaluationResult]]] = {}
    sorted_results = sorted(results, key=lambda result: result.created_at, reverse=True)
    for result in sorted_results:
        if (
            result.status != EvaluationRunStatus.completed
            or result.workflow_run_id is None
            or result.run_mode not in {RunMode.baseline, RunMode.multi_agent}
        ):
            continue
        mode_results = grouped.setdefault(result.evaluation_case_id, {})
        mode_results.setdefault(result.run_mode, []).append(result)

    pairs: dict[uuid.UUID, _ResultPair] = {}
    for case_id, mode_results in grouped.items():
        baseline_results = mode_results.get(RunMode.baseline, [])
        multi_agent_results = mode_results.get(RunMode.multi_agent, [])
        if not baseline_results or not multi_agent_results:
            continue
        pairs[case_id] = _ResultPair(
            baseline=baseline_results[0],
            multi_agent=multi_agent_results[0],
            previous_multi_agent=multi_agent_results[1]
            if len(multi_agent_results) > 1
            else None,
        )
    return pairs


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
        created_at=result.created_at,
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


def _remediation_impact(
    *,
    pair: _ResultPair,
    latest_run: WorkflowRun,
    run_by_id: dict[uuid.UUID, WorkflowRun],
    input_by_id: dict[uuid.UUID, UploadedInput],
    steps_by_run_id: dict[uuid.UUID, list[AgentStep]],
    current_reviewer_issues: list[dict[str, Any]],
) -> RemediationImpactRead | None:
    previous_result = pair.previous_multi_agent
    if previous_result is None or previous_result.workflow_run_id is None:
        return None
    if not _is_corrected_run(latest_run, input_by_id):
        return None
    previous_run = run_by_id.get(previous_result.workflow_run_id)
    if previous_run is None:
        return None

    latest = _comparison_run(pair.multi_agent, latest_run)
    previous = _comparison_run(previous_result, previous_run)
    previous_issues = _latest_reviewer_issues(steps_by_run_id.get(previous_run.id, []))
    accuracy_delta = _metric_delta(
        previous.factual_accuracy,
        latest.factual_accuracy,
    )
    unsupported_delta = _metric_delta(
        previous.unsupported_claim_rate,
        latest.unsupported_claim_rate,
    )
    completeness_delta = _metric_delta(
        previous.completeness_score,
        latest.completeness_score,
    )

    return RemediationImpactRead(
        previous_multi_agent_run_id=previous_run.id,
        corrected_multi_agent_run_id=latest_run.id,
        previous_reviewer_issue_count=len(previous_issues),
        current_reviewer_issue_count=len(current_reviewer_issues),
        factual_accuracy_delta=accuracy_delta,
        unsupported_claim_rate_delta=unsupported_delta,
        completeness_score_delta=completeness_delta,
        cost_delta=latest.cost - previous.cost,
        latency_delta_ms=latest.latency_ms - previous.latency_ms,
        impact_status=_impact_status(
            previous_issue_count=len(previous_issues),
            current_issue_count=len(current_reviewer_issues),
            accuracy_delta=accuracy_delta,
            unsupported_delta=unsupported_delta,
            completeness_delta=completeness_delta,
        ),
    )


def _is_corrected_run(
    run: WorkflowRun,
    input_by_id: dict[uuid.UUID, UploadedInput],
) -> bool:
    if run.input_id is None:
        return False
    uploaded_input = input_by_id.get(run.input_id)
    return uploaded_input is not None and CORRECTED_RUN_MARKER in (uploaded_input.notes or "")


def _metric_delta(previous: float | None, latest: float | None) -> float | None:
    if previous is None or latest is None:
        return None
    return latest - previous


def _impact_status(
    *,
    previous_issue_count: int,
    current_issue_count: int,
    accuracy_delta: float | None,
    unsupported_delta: float | None,
    completeness_delta: float | None,
) -> str:
    positive = 0
    negative = 0
    issue_delta = previous_issue_count - current_issue_count
    if issue_delta > 0:
        positive += 1
    elif issue_delta < 0:
        negative += 1

    for value in (accuracy_delta, completeness_delta):
        if value is None:
            continue
        if value > 0:
            positive += 1
        elif value < 0:
            negative += 1

    if unsupported_delta is not None:
        if unsupported_delta < 0:
            positive += 1
        elif unsupported_delta > 0:
            negative += 1

    if positive > 0 and negative == 0:
        return "improved"
    if negative > 0 and positive == 0:
        return "worsened"
    return "mixed"


def _preview(value: str, limit: int = 280) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}..."
