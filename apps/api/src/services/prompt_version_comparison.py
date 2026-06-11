from __future__ import annotations

import json
from dataclasses import dataclass

from src.models.evaluation_result import EvaluationResult
from src.models.workflow_run import RunMode
from src.services.evaluation_metrics import summarize_evaluation_results


@dataclass(frozen=True)
class PromptVersionPerformance:
    prompt_version_key: str
    prompt_version_summary: dict[str, object]
    run_mode: RunMode
    run_count: int
    factual_accuracy: float
    unsupported_claim_rate: float
    completeness_score: float
    average_cost: float
    average_latency_ms: float
    average_retries: float


def compare_prompt_version_performance(
    results: list[EvaluationResult],
) -> list[PromptVersionPerformance]:
    grouped: dict[tuple[RunMode, str], list[EvaluationResult]] = {}
    summaries: dict[tuple[RunMode, str], dict[str, object]] = {}
    for result in results:
        summary = result.prompt_version_summary_json or {}
        key = json.dumps(summary, sort_keys=True)
        group_key = (result.run_mode, key)
        grouped.setdefault(group_key, []).append(result)
        summaries[group_key] = summary

    comparisons: list[PromptVersionPerformance] = []
    for (run_mode, key), group_results in grouped.items():
        metrics = summarize_evaluation_results(group_results)
        comparisons.append(
            PromptVersionPerformance(
                prompt_version_key=key,
                prompt_version_summary=summaries[(run_mode, key)],
                run_mode=run_mode,
                run_count=metrics.run_count,
                factual_accuracy=metrics.factual_accuracy,
                unsupported_claim_rate=metrics.unsupported_claim_rate,
                completeness_score=metrics.completeness_score,
                average_cost=metrics.average_cost,
                average_latency_ms=metrics.average_latency_ms,
                average_retries=metrics.average_retries,
            )
        )
    return sorted(
        comparisons,
        key=lambda item: (item.run_mode.value, item.prompt_version_key),
    )
