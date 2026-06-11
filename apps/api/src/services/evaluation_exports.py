from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.workflow_run import RunMode, WorkflowType
from src.services.evaluation_metrics import summarize_evaluation_results

EXPORT_FIELDS = [
    "evaluation_result_id",
    "evaluation_case_id",
    "workflow_type",
    "title",
    "run_mode",
    "status",
    "factual_accuracy",
    "unsupported_claim_rate",
    "completeness_score",
    "human_approval_required",
    "human_approved",
    "retry_count",
    "cost",
    "latency_ms",
    "judge_notes",
    "error_message",
    "created_at",
]


def build_evaluation_json_export(
    cases: list[EvaluationCase],
    results: list[EvaluationResult],
) -> dict[str, Any]:
    rows = _export_rows(cases, results)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "result_count": len(rows),
        "results": rows,
        "summary": _summary_rows(cases, results),
    }


def build_evaluation_csv_export(
    cases: list[EvaluationCase],
    results: list[EvaluationResult],
) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    writer.writerows(_export_rows(cases, results))
    return output.getvalue()


def build_evaluation_markdown_export(
    cases: list[EvaluationCase],
    results: list[EvaluationResult],
) -> str:
    rows = _export_rows(cases, results)
    summary = _summary_rows(cases, results)
    failed = [row for row in rows if row["status"] == EvaluationRunStatus.failed.value]

    lines = [
        "# Evaluation Report",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Evaluation results: {len(rows)}",
        "",
        "## Summary",
        "",
        (
            "| Workflow | Mode | Runs | Factual Accuracy | Unsupported Claims | "
            "Completeness | Avg Cost | Avg Latency | Avg Retries |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        (
            "| {workflow_type} | {run_mode} | {run_count} | {factual_accuracy:.0%} | "
            "{unsupported_claim_rate:.0%} | {completeness_score:.0%} | "
            "${average_cost:.4f} | {average_latency_ms:.0f}ms | {average_retries:.2f} |"
        ).format(**item)
        for item in summary
    )
    lines.extend(["", "## Notable Failure Cases", ""])
    if failed:
        lines.extend(
            f"- {row['title']} ({row['run_mode']}): {row['error_message'] or 'No error message'}"
            for row in failed[:10]
        )
    else:
        lines.append("- No failed evaluation results recorded.")

    lines.extend(["", "## Result Details", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row['title']} - {row['run_mode']}",
                "",
                f"- Workflow: {row['workflow_type']}",
                f"- Status: {row['status']}",
                f"- Factual accuracy: {_format_optional_percent(row['factual_accuracy'])}",
                (
                    "- Unsupported claim rate: "
                    f"{_format_optional_percent(row['unsupported_claim_rate'])}"
                ),
                f"- Completeness: {_format_optional_percent(row['completeness_score'])}",
                f"- Cost: {_format_optional_cost(row['cost'])}",
                f"- Latency: {_format_optional_latency(row['latency_ms'])}",
                f"- Retries: {row['retry_count'] if row['retry_count'] is not None else 'n/a'}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _export_rows(
    cases: list[EvaluationCase],
    results: list[EvaluationResult],
) -> list[dict[str, Any]]:
    case_by_id = {case.id: case for case in cases}
    rows: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda item: item.created_at, reverse=True):
        case = case_by_id.get(result.evaluation_case_id)
        rows.append(
            {
                "evaluation_result_id": str(result.id),
                "evaluation_case_id": str(result.evaluation_case_id),
                "workflow_type": case.workflow_type.value if case is not None else None,
                "title": case.title if case is not None else "Unknown evaluation case",
                "run_mode": result.run_mode.value,
                "status": result.status.value,
                "factual_accuracy": result.factual_accuracy,
                "unsupported_claim_rate": result.unsupported_claim_rate,
                "completeness_score": result.completeness_score,
                "human_approval_required": result.human_approval_required,
                "human_approved": result.human_approved,
                "retry_count": result.retry_count,
                "cost": result.cost,
                "latency_ms": result.latency_ms,
                "judge_notes": result.judge_notes,
                "error_message": result.error_message,
                "created_at": result.created_at.isoformat(),
            }
        )
    return rows


def _summary_rows(
    cases: list[EvaluationCase],
    results: list[EvaluationResult],
) -> list[dict[str, Any]]:
    case_workflows = {case.id: case.workflow_type for case in cases}
    rows: list[dict[str, Any]] = []
    for workflow_type in (
        WorkflowType.sales_report,
        WorkflowType.customer_feedback,
        WorkflowType.incident_log,
    ):
        workflow_results = [
            result
            for result in results
            if case_workflows.get(result.evaluation_case_id) == workflow_type
        ]
        for run_mode in (RunMode.baseline, RunMode.multi_agent):
            metrics = summarize_evaluation_results(
                [result for result in workflow_results if result.run_mode == run_mode]
            )
            rows.append(
                {
                    "workflow_type": workflow_type.value,
                    "run_mode": run_mode.value,
                    "run_count": metrics.run_count,
                    "factual_accuracy": metrics.factual_accuracy,
                    "unsupported_claim_rate": metrics.unsupported_claim_rate,
                    "completeness_score": metrics.completeness_score,
                    "human_approval_rate": metrics.human_approval_rate,
                    "average_cost": metrics.average_cost,
                    "average_latency_ms": metrics.average_latency_ms,
                    "average_retries": metrics.average_retries,
                }
            )
    return rows


def _format_optional_percent(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.0%}"


def _format_optional_cost(value: Any) -> str:
    return "n/a" if value is None else f"${float(value):.4f}"


def _format_optional_latency(value: Any) -> str:
    return "n/a" if value is None else f"{int(value)}ms"
