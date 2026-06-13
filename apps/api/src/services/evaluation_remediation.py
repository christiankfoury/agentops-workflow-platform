from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.workflow_run import RunMode
from src.services.evaluation_runner import LLMClientLike, run_sales_evaluation_case


class EvaluationRemediationError(Exception):
    pass


@dataclass(frozen=True)
class CorrectedEvaluationComparisonResult:
    evaluation_case_id: uuid.UUID
    baseline_result_id: uuid.UUID
    corrected_result_id: uuid.UUID
    baseline_run_id: uuid.UUID
    source_multi_agent_run_id: uuid.UUID
    corrected_multi_agent_run_id: uuid.UUID
    comparison_url: str


def create_corrected_evaluation_comparison_run(
    db: Session,
    evaluation_case_id: uuid.UUID,
    llm_client: LLMClientLike,
) -> CorrectedEvaluationComparisonResult:
    evaluation_case = _get_evaluation_case(db, evaluation_case_id)
    baseline_result = _latest_completed_result(db, evaluation_case_id, RunMode.baseline)
    source_multi_agent_result = _latest_completed_result(
        db,
        evaluation_case_id,
        RunMode.multi_agent,
    )
    if baseline_result is None or baseline_result.workflow_run_id is None:
        raise EvaluationRemediationError("Comparison must have a completed baseline result")
    if source_multi_agent_result is None or source_multi_agent_result.workflow_run_id is None:
        raise EvaluationRemediationError("Comparison must have a completed multi-agent result")

    reviewer_issues = _latest_reviewer_issues(db, source_multi_agent_result.workflow_run_id)
    if not reviewer_issues:
        raise EvaluationRemediationError("Comparison has no reviewer issues to correct")

    corrected_result = run_sales_evaluation_case(
        db,
        evaluation_case,
        RunMode.multi_agent,
        llm_client,
        correction_guidance=_corrected_run_notes(reviewer_issues),
    )

    if corrected_result.status != EvaluationRunStatus.completed:
        detail = corrected_result.error_message or "Corrected multi-agent evaluation failed"
        raise EvaluationRemediationError(f"Corrected multi-agent evaluation failed: {detail}")
    if corrected_result.workflow_run_id is None:
        raise EvaluationRemediationError("Corrected evaluation did not link a workflow run")

    return CorrectedEvaluationComparisonResult(
        evaluation_case_id=evaluation_case.id,
        baseline_result_id=baseline_result.id,
        corrected_result_id=corrected_result.id,
        baseline_run_id=baseline_result.workflow_run_id,
        source_multi_agent_run_id=source_multi_agent_result.workflow_run_id,
        corrected_multi_agent_run_id=corrected_result.workflow_run_id,
        comparison_url=f"/workflow-comparison?search={quote(evaluation_case.title)}",
    )


def _get_evaluation_case(db: Session, evaluation_case_id: uuid.UUID) -> EvaluationCase:
    evaluation_case = (
        db.query(EvaluationCase).filter(EvaluationCase.id == evaluation_case_id).first()
    )
    if evaluation_case is None:
        raise EvaluationRemediationError("Evaluation case not found")
    return evaluation_case


def _latest_completed_result(
    db: Session,
    evaluation_case_id: uuid.UUID,
    run_mode: RunMode,
) -> EvaluationResult | None:
    return (
        db.query(EvaluationResult)
        .filter(
            EvaluationResult.evaluation_case_id == evaluation_case_id,
            EvaluationResult.run_mode == run_mode,
            EvaluationResult.status == EvaluationRunStatus.completed,
        )
        .order_by(EvaluationResult.created_at.desc())
        .first()
    )


def _latest_reviewer_issues(db: Session, workflow_run_id: uuid.UUID) -> list[dict[str, Any]]:
    steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == workflow_run_id,
            AgentStep.agent_type == "reviewer",
            AgentStep.status == AgentStepStatus.completed,
        )
        .order_by(AgentStep.completed_at.desc(), AgentStep.created_at.desc())
        .all()
    )
    for step in steps:
        if not isinstance(step.output_json, dict):
            continue
        issues = step.output_json.get("issues")
        if isinstance(issues, list):
            return [issue for issue in issues if isinstance(issue, dict)]
    return []


def _corrected_run_notes(reviewer_issues: list[dict[str, Any]]) -> str:
    issue_lines = "\n".join(
        f"- {_format_issue(issue)}" for issue in reviewer_issues
    )
    return (
        "Corrected comparison run guidance. The reviewer issues below are not "
        "source facts; use them only to avoid repeating the same unsupported or "
        "misclassified claims. Address them while using only facts supported by "
        "the source input.\n"
        f"{issue_lines}"
    )


def _format_issue(issue: dict[str, Any]) -> str:
    severity = str(issue.get("severity") or "unspecified")
    claim = str(issue.get("claim") or "Reviewer issue")
    problem = str(issue.get("problem") or "").strip()
    if problem:
        return f"[{severity}] {claim}: {problem}"
    return f"[{severity}] {claim}"
