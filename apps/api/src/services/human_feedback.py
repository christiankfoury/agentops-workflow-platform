from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from src.models.human_approval import ApprovalStatus, HumanApproval


@dataclass(frozen=True)
class ReviewerIssueSummary:
    label: str
    severity: str | None
    count: int


@dataclass(frozen=True)
class HumanEditSummary:
    field: str
    count: int
    examples: list[str]


@dataclass(frozen=True)
class HumanApprovalTrendPoint:
    date: str
    total: int
    approved: int
    retry_requested: int
    rejected: int


@dataclass(frozen=True)
class HumanFeedbackSummary:
    total_approvals: int
    resolved_approvals: int
    approvals_with_feedback: int
    approvals_with_edits: int
    approval_rate: float
    retry_request_rate: float
    rejection_rate: float
    common_reviewer_issues: list[ReviewerIssueSummary]
    common_human_edits: list[HumanEditSummary]
    approval_trend: list[HumanApprovalTrendPoint]


def summarize_human_feedback(approvals: list[HumanApproval]) -> HumanFeedbackSummary:
    resolved = [
        approval
        for approval in approvals
        if approval.status
        in {
            ApprovalStatus.approved,
            ApprovalStatus.retry_requested,
            ApprovalStatus.rejected,
        }
    ]
    return HumanFeedbackSummary(
        total_approvals=len(approvals),
        resolved_approvals=len(resolved),
        approvals_with_feedback=sum(
            1 for approval in approvals if bool((approval.human_feedback or "").strip())
        ),
        approvals_with_edits=sum(
            1 for approval in approvals if bool(approval.edited_analysis_json)
        ),
        approval_rate=_status_rate(resolved, ApprovalStatus.approved),
        retry_request_rate=_status_rate(resolved, ApprovalStatus.retry_requested),
        rejection_rate=_status_rate(resolved, ApprovalStatus.rejected),
        common_reviewer_issues=_summarize_reviewer_issues(approvals),
        common_human_edits=_summarize_human_edits(approvals),
        approval_trend=_summarize_approval_trend(resolved),
    )


def get_edited_fields(edited_analysis_json: dict[str, Any] | None) -> list[str]:
    if not edited_analysis_json:
        return []
    return sorted(_flatten_fields(edited_analysis_json))


def _status_rate(approvals: list[HumanApproval], status: ApprovalStatus) -> float:
    if not approvals:
        return 0.0
    return sum(1 for approval in approvals if approval.status == status) / len(approvals)


def _summarize_reviewer_issues(
    approvals: list[HumanApproval],
) -> list[ReviewerIssueSummary]:
    issue_counts: Counter[tuple[str, str | None]] = Counter()
    for approval in approvals:
        for issue in approval.issues_json or []:
            if not isinstance(issue, dict):
                continue
            label = _issue_label(issue)
            severity = issue.get("severity")
            issue_counts[(label, severity if isinstance(severity, str) else None)] += 1
    return [
        ReviewerIssueSummary(label=label, severity=severity, count=count)
        for (label, severity), count in issue_counts.most_common(5)
    ]


def _summarize_human_edits(approvals: list[HumanApproval]) -> list[HumanEditSummary]:
    field_counts: Counter[str] = Counter()
    examples_by_field: dict[str, list[str]] = defaultdict(list)
    for approval in approvals:
        for field in get_edited_fields(approval.edited_analysis_json):
            field_counts[field] += 1
            example = _field_example(approval.edited_analysis_json or {}, field)
            if example and example not in examples_by_field[field]:
                examples_by_field[field].append(example)
    return [
        HumanEditSummary(
            field=field,
            count=count,
            examples=examples_by_field[field][:3],
        )
        for field, count in field_counts.most_common(5)
    ]


def _summarize_approval_trend(
    approvals: list[HumanApproval],
) -> list[HumanApprovalTrendPoint]:
    buckets: dict[str, Counter[ApprovalStatus]] = defaultdict(Counter)
    for approval in approvals:
        timestamp = approval.resolved_at or approval.created_at
        if timestamp is None:
            continue
        buckets[timestamp.date().isoformat()][approval.status] += 1
    return [
        HumanApprovalTrendPoint(
            date=date,
            total=sum(counts.values()),
            approved=counts[ApprovalStatus.approved],
            retry_requested=counts[ApprovalStatus.retry_requested],
            rejected=counts[ApprovalStatus.rejected],
        )
        for date, counts in sorted(buckets.items())
    ][-14:]


def _issue_label(issue: dict[str, Any]) -> str:
    for key in ("problem", "claim"):
        value = issue.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Unspecified reviewer issue"


def _flatten_fields(value: Any, prefix: str = "") -> set[str]:
    if not isinstance(value, dict):
        return {prefix} if prefix else set()
    fields: set[str] = set()
    for key, nested in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(nested, dict):
            fields.update(_flatten_fields(nested, path))
        else:
            fields.add(path)
    return fields


def _field_example(value: dict[str, Any], field: str) -> str | None:
    current: Any = value
    for part in field.split("."):
        if not isinstance(current, dict):
            return _short_example(current)
        current = current.get(part)
    return _short_example(current)


def _short_example(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        return _short_example(value[0])
    if isinstance(value, dict):
        return _short_example(next(iter(value.values()), None))
    text = str(value).strip()
    if not text:
        return None
    return text[:120]
