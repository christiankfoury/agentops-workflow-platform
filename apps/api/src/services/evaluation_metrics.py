from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus


@dataclass(frozen=True)
class EvaluationScores:
    factual_accuracy: float
    unsupported_claim_rate: float
    completeness_score: float


@dataclass(frozen=True)
class EvaluationAggregateMetrics:
    run_count: int
    factual_accuracy: float
    unsupported_claim_rate: float
    completeness_score: float
    router_accuracy: float
    average_router_confidence: float
    human_approval_rate: float
    average_cost: float
    average_latency_ms: float
    average_retries: float


def calculate_sales_evaluation_scores(
    evaluation_case: EvaluationCase,
    final_output: str | None,
) -> EvaluationScores:
    output = final_output or ""
    facts = evaluation_case.expected_facts_json or []
    risks = evaluation_case.expected_risks_json or []
    recommendations = evaluation_case.expected_recommendations_json or []

    captured_facts = _count_captured(output, facts)
    captured_all = (
        captured_facts
        + _count_captured(output, risks)
        + _count_captured(output, recommendations)
    )
    expected_total = len(facts) + len(risks) + len(recommendations)
    return EvaluationScores(
        factual_accuracy=_safe_ratio(captured_facts, len(facts)),
        unsupported_claim_rate=_unsupported_claim_rate(
            output,
            facts + risks + recommendations,
        ),
        completeness_score=_safe_ratio(captured_all, expected_total),
    )


def summarize_evaluation_results(results: list[EvaluationResult]) -> EvaluationAggregateMetrics:
    completed = [result for result in results if result.status == EvaluationRunStatus.completed]
    approvals = [
        result
        for result in completed
        if result.human_approval_required is not None and result.human_approval_required
    ]
    approved = [result for result in approvals if result.human_approved]
    router_tracked = [result for result in completed if result.router_correct is not None]
    router_correct = [result for result in router_tracked if result.router_correct]
    return EvaluationAggregateMetrics(
        run_count=len(completed),
        factual_accuracy=_average(
            result.factual_accuracy for result in completed if result.factual_accuracy is not None
        ),
        unsupported_claim_rate=_average(
            result.unsupported_claim_rate
            for result in completed
            if result.unsupported_claim_rate is not None
        ),
        completeness_score=_average(
            result.completeness_score
            for result in completed
            if result.completeness_score is not None
        ),
        router_accuracy=_safe_ratio(len(router_correct), len(router_tracked)),
        average_router_confidence=_average(
            result.router_confidence
            for result in completed
            if result.router_confidence is not None
        ),
        human_approval_rate=_safe_ratio(len(approved), len(approvals)),
        average_cost=_average(result.cost for result in completed if result.cost is not None),
        average_latency_ms=_average(
            result.latency_ms for result in completed if result.latency_ms is not None
        ),
        average_retries=_average(
            result.retry_count for result in completed if result.retry_count is not None
        ),
    )


def _count_captured(output: str, expected_items: list[str]) -> int:
    normalized_output = _normalize(output)
    return sum(1 for item in expected_items if _expected_item_is_captured(normalized_output, item))


def _expected_item_is_captured(normalized_output: str, expected_item: str) -> bool:
    normalized_item = _normalize(expected_item)
    if normalized_item in normalized_output:
        return True
    item_terms = _important_terms(normalized_item)
    if not item_terms:
        return False
    return len(item_terms.intersection(_important_terms(normalized_output))) >= min(
        3,
        len(item_terms),
    )


def _unsupported_claim_rate(output: str, expected_items: list[str]) -> float:
    claims = _split_claims(output)
    if not claims:
        return 0.0
    supported = sum(1 for claim in claims if _claim_is_supported(claim, expected_items))
    return round((len(claims) - supported) / len(claims), 4)


def _claim_is_supported(claim: str, expected_items: list[str]) -> bool:
    normalized_claim = _normalize(claim)
    claim_terms = _important_terms(normalized_claim)
    if not claim_terms:
        return True
    for expected_item in expected_items:
        normalized_item = _normalize(expected_item)
        if normalized_item and normalized_item in normalized_claim:
            return True
        if len(claim_terms.intersection(_important_terms(normalized_item))) >= 2:
            return True
    return False


def _split_claims(output: str) -> list[str]:
    protected_output = re.sub(r"(?<=\d)\.(?=\d)", "<decimal>", output)
    return [
        claim.strip().replace("<decimal>", ".")
        for claim in re.split(r"[\n;]+|(?<!\d)\.(?!\d)", protected_output)
        if _is_scored_claim(claim.strip().replace("<decimal>", "."))
    ]


def _is_scored_claim(claim: str) -> bool:
    normalized = _normalize(claim)
    if not normalized:
        return False
    if normalized in {"executive summary", "summary"}:
        return False
    if normalized in {"none", "n a", "not applicable"}:
        return False
    if normalized.endswith("summary"):
        return False
    if normalized in {"key risks", "risks", "recommended actions", "recommendations"}:
        return False
    if normalized.endswith("include"):
        return False
    return True


def _important_terms(value: str) -> set[str]:
    return {
        term
        for term in value.split()
        if len(term) >= 4 or any(char.isdigit() for char in term)
    }


def _normalize(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9.%$]+", " ", value.lower()).split())


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _average(values: Iterable[float | int]) -> float:
    items = [float(value) for value in values]
    if not items:
        return 0.0
    return round(sum(items) / len(items), 4)
