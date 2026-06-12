from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.uploaded_input import UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.evaluation_runner import LLMClientLike, run_sales_evaluation_case


class EvaluationPromotionError(Exception):
    pass


@dataclass(frozen=True)
class EvaluationPromotionResult:
    evaluation_case_id: uuid.UUID
    baseline_result_id: uuid.UUID
    multi_agent_result_id: uuid.UUID
    baseline_run_id: uuid.UUID
    multi_agent_run_id: uuid.UUID
    comparison_url: str


STRUCTURED_AGENT_BY_WORKFLOW: dict[WorkflowType, str] = {
    WorkflowType.sales_report: "analyst",
    WorkflowType.customer_feedback: "insight",
    WorkflowType.incident_log: "root_cause",
}


def promote_workflow_run_to_evaluation_comparison(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> EvaluationPromotionResult:
    uploaded_input = _validate_source_run(db, run)
    structured_step = _get_latest_completed_structured_step(db, run)
    expected_items = _derive_expected_items(run.workflow_type, structured_step.output_json or {})
    evaluation_case = _get_or_create_evaluation_case(
        db,
        run.workflow_type,
        title=f"[Promoted] {uploaded_input.title}",
        input_text=uploaded_input.raw_text,
        expected_items=expected_items,
        notes=uploaded_input.notes,
    )

    baseline_result = _run_promoted_evaluation(db, evaluation_case, RunMode.baseline, llm_client)
    multi_agent_result = _run_promoted_evaluation(
        db,
        evaluation_case,
        RunMode.multi_agent,
        llm_client,
    )

    if baseline_result.workflow_run_id is None or multi_agent_result.workflow_run_id is None:
        raise EvaluationPromotionError("Promoted evaluation did not create both workflow runs")

    return EvaluationPromotionResult(
        evaluation_case_id=evaluation_case.id,
        baseline_result_id=baseline_result.id,
        multi_agent_result_id=multi_agent_result.id,
        baseline_run_id=baseline_result.workflow_run_id,
        multi_agent_run_id=multi_agent_result.workflow_run_id,
        comparison_url=f"/workflow-comparison?search={quote(evaluation_case.title)}",
    )


def _validate_source_run(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.completed:
        raise EvaluationPromotionError("Only completed workflow runs can be promoted")
    if run.run_mode != RunMode.multi_agent:
        raise EvaluationPromotionError("Only multi-agent workflow runs can be promoted")
    if run.input_id is None:
        raise EvaluationPromotionError("Workflow run must have a linked uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise EvaluationPromotionError("Linked uploaded input was not found")
    return uploaded_input


def _get_latest_completed_structured_step(db: Session, run: WorkflowRun) -> AgentStep:
    agent_type = STRUCTURED_AGENT_BY_WORKFLOW[run.workflow_type]
    step = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run.id,
            AgentStep.agent_type == agent_type,
            AgentStep.status == AgentStepStatus.completed,
        )
        .order_by(AgentStep.step_order.desc(), AgentStep.created_at.desc())
        .first()
    )
    if step is None or not step.output_json:
        raise EvaluationPromotionError(
            f"Workflow run must have a completed {agent_type} step with structured output"
        )
    return step


def _get_or_create_evaluation_case(
    db: Session,
    workflow_type: WorkflowType,
    *,
    title: str,
    input_text: str,
    expected_items: dict[str, Any],
    notes: str | None,
) -> EvaluationCase:
    existing = (
        db.query(EvaluationCase)
        .filter(
            EvaluationCase.workflow_type == workflow_type,
            EvaluationCase.title == title,
            EvaluationCase.input_text == input_text,
        )
        .first()
    )
    if existing is not None:
        return existing

    evaluation_case = EvaluationCase(
        workflow_type=workflow_type,
        title=title,
        input_text=input_text,
        expected_facts_json=expected_items["facts"],
        expected_risks_json=expected_items["risks"],
        expected_recommendations_json=expected_items["recommendations"],
        expected_themes_json=expected_items.get("themes"),
        expected_timeline_json=expected_items.get("timeline"),
        expected_output_notes=(
            "Promoted from a completed manual workflow run."
            if not notes
            else f"Promoted from a completed manual workflow run. Source notes: {notes}"
        ),
    )
    db.add(evaluation_case)
    db.commit()
    db.refresh(evaluation_case)
    return evaluation_case


def _run_promoted_evaluation(
    db: Session,
    evaluation_case: EvaluationCase,
    run_mode: RunMode,
    llm_client: LLMClientLike,
) -> EvaluationResult:
    result = run_sales_evaluation_case(db, evaluation_case, run_mode, llm_client)
    if result.status != EvaluationRunStatus.completed:
        detail = result.error_message or "Promoted evaluation run failed"
        raise EvaluationPromotionError(f"{run_mode.value} evaluation failed: {detail}")
    return result


def _derive_expected_items(workflow_type: WorkflowType, output: dict[str, Any]) -> dict[str, Any]:
    if workflow_type == WorkflowType.customer_feedback:
        items = _derive_customer_feedback_expected_items(output)
    elif workflow_type == WorkflowType.incident_log:
        items = _derive_incident_expected_items(output)
    else:
        items = _derive_sales_expected_items(output)

    if not items["facts"]:
        raise EvaluationPromotionError("Structured output did not contain expected facts")
    if not items["recommendations"]:
        raise EvaluationPromotionError("Structured output did not contain expected recommendations")
    return items


def _derive_sales_expected_items(output: dict[str, Any]) -> dict[str, Any]:
    return {
        "facts": _strings_from(output.get("key_findings"))
        + _strings_from(output.get("supporting_evidence")),
        "risks": _strings_from(output.get("risks")),
        "recommendations": _strings_from(output.get("recommendations")),
        "themes": None,
        "timeline": None,
    }


def _derive_customer_feedback_expected_items(output: dict[str, Any]) -> dict[str, Any]:
    return {
        "facts": _strings_from(output.get("top_insights"))
        + _strings_from(output.get("supporting_examples")),
        "risks": _strings_from(output.get("risks"))
        + _strings_from(output.get("customer_pain_points")),
        "recommendations": _strings_from(output.get("recommendations"))
        + _strings_from(output.get("feature_requests")),
        "themes": _strings_from(output.get("themes")) or None,
        "timeline": None,
    }


def _derive_incident_expected_items(output: dict[str, Any]) -> dict[str, Any]:
    suspected_root_cause = _strings_from(output.get("suspected_root_cause"))
    return {
        "facts": _strings_from(output.get("confirmed_facts")) + suspected_root_cause,
        "risks": _strings_from(output.get("likely_causes")),
        "recommendations": _strings_from(output.get("follow_up_actions")),
        "themes": None,
        "timeline": _timeline_items(output.get("timeline")),
    }


def _strings_from(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(_strings_from(item))
        return _dedupe(items)
    if isinstance(value, dict):
        for key in (
            "claim",
            "recommendation",
            "action",
            "request",
            "description",
            "name",
            "summary",
            "text",
            "event",
        ):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return [item.strip()]
    return []


def _timeline_items(value: Any) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return None
    timeline: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        time = str(item.get("time", "")).strip()
        event = str(item.get("event", "")).strip()
        if time or event:
            timeline.append({"time": time, "event": event})
    return timeline or None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = item.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped
