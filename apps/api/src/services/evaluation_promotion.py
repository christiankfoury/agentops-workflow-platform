from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.evaluation_metrics import calculate_sales_evaluation_scores
from src.services.evaluation_runner import (
    LLMClientLike,
    _create_workflow_run,
    _run_multi_agent_case,
    run_sales_evaluation_case,
)


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
    if run.run_mode == RunMode.baseline:
        return _promote_baseline_run(db, run, uploaded_input, llm_client)
    return _promote_multi_agent_run(db, run, uploaded_input, llm_client)


def _promote_multi_agent_run(
    db: Session,
    run: WorkflowRun,
    uploaded_input: UploadedInput,
    llm_client: LLMClientLike,
) -> EvaluationPromotionResult:
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
    multi_agent_result = _get_or_create_existing_run_result(db, evaluation_case, run)
    baseline_result = _get_or_run_counterpart_result(
        db,
        evaluation_case,
        RunMode.baseline,
        llm_client,
    )
    return _promotion_result(evaluation_case, baseline_result, multi_agent_result)


def _promote_baseline_run(
    db: Session,
    run: WorkflowRun,
    uploaded_input: UploadedInput,
    llm_client: LLMClientLike,
) -> EvaluationPromotionResult:
    title = f"[Promoted] {uploaded_input.title}"
    evaluation_case = _get_existing_evaluation_case(
        db,
        run.workflow_type,
        title=title,
        input_text=uploaded_input.raw_text,
    )

    multi_agent_result = (
        _latest_completed_result(db, evaluation_case.id, RunMode.multi_agent)
        if evaluation_case is not None
        else None
    )
    multi_agent_run = (
        db.query(WorkflowRun).filter(WorkflowRun.id == multi_agent_result.workflow_run_id).first()
        if multi_agent_result is not None and multi_agent_result.workflow_run_id is not None
        else None
    )
    if multi_agent_result is None or multi_agent_run is None:
        multi_agent_run = _run_new_multi_agent_counterpart(
            db,
            run.workflow_type,
            title=title,
            source_input=uploaded_input,
            llm_client=llm_client,
        )
        structured_step = _get_latest_completed_structured_step(db, multi_agent_run)
        expected_items = _derive_expected_items(
            multi_agent_run.workflow_type,
            structured_step.output_json or {},
        )
        evaluation_case = _get_or_create_evaluation_case(
            db,
            run.workflow_type,
            title=title,
            input_text=uploaded_input.raw_text,
            expected_items=expected_items,
            notes=uploaded_input.notes,
        )
        multi_agent_result = _get_or_create_existing_run_result(
            db,
            evaluation_case,
            multi_agent_run,
        )

    if evaluation_case is None:
        raise EvaluationPromotionError("Promoted evaluation case could not be created")

    baseline_result = _get_or_create_existing_run_result(db, evaluation_case, run)
    return _promotion_result(evaluation_case, baseline_result, multi_agent_result)


def _validate_source_run(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.completed:
        raise EvaluationPromotionError("Only completed workflow runs can be compared")
    if run.run_mode not in {RunMode.baseline, RunMode.multi_agent}:
        raise EvaluationPromotionError("Only baseline or multi-agent workflow runs can be compared")
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


def _get_existing_evaluation_case(
    db: Session,
    workflow_type: WorkflowType,
    *,
    title: str,
    input_text: str,
) -> EvaluationCase | None:
    return (
        db.query(EvaluationCase)
        .filter(
            EvaluationCase.workflow_type == workflow_type,
            EvaluationCase.title == title,
            EvaluationCase.input_text == input_text,
        )
        .first()
    )


def _get_or_create_evaluation_case(
    db: Session,
    workflow_type: WorkflowType,
    *,
    title: str,
    input_text: str,
    expected_items: dict[str, Any],
    notes: str | None,
) -> EvaluationCase:
    existing = _get_existing_evaluation_case(
        db,
        workflow_type,
        title=title,
        input_text=input_text,
    )
    if existing is not None:
        _update_expected_items(db, existing, expected_items)
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
            "Promoted from a completed workflow run."
            if not notes
            else f"Promoted from a completed workflow run. Source notes: {notes}"
        ),
    )
    db.add(evaluation_case)
    db.commit()
    db.refresh(evaluation_case)
    return evaluation_case


def _update_expected_items(
    db: Session,
    evaluation_case: EvaluationCase,
    expected_items: dict[str, Any],
) -> None:
    evaluation_case.expected_facts_json = expected_items["facts"]
    evaluation_case.expected_risks_json = expected_items["risks"]
    evaluation_case.expected_recommendations_json = expected_items["recommendations"]
    evaluation_case.expected_themes_json = expected_items.get("themes")
    evaluation_case.expected_timeline_json = expected_items.get("timeline")
    db.commit()
    db.refresh(evaluation_case)


def _get_or_run_counterpart_result(
    db: Session,
    evaluation_case: EvaluationCase,
    run_mode: RunMode,
    llm_client: LLMClientLike,
) -> EvaluationResult:
    existing = _latest_completed_result(db, evaluation_case.id, run_mode)
    if existing is not None:
        return existing

    result = run_sales_evaluation_case(db, evaluation_case, run_mode, llm_client)
    if result.status != EvaluationRunStatus.completed:
        detail = result.error_message or "Promoted evaluation run failed"
        raise EvaluationPromotionError(f"{run_mode.value} evaluation failed: {detail}")
    return result


def _run_new_multi_agent_counterpart(
    db: Session,
    workflow_type: WorkflowType,
    *,
    title: str,
    source_input: UploadedInput,
    llm_client: LLMClientLike,
) -> WorkflowRun:
    uploaded_input = UploadedInput(
        title=f"Evaluation: {title}",
        input_type=InputType(workflow_type.value),
        raw_text=source_input.raw_text,
        notes="Created by promoted comparison runner.",
    )
    db.add(uploaded_input)
    db.commit()
    db.refresh(uploaded_input)

    run = _create_workflow_run(
        db,
        EvaluationCase(
            workflow_type=workflow_type,
            title=title,
            input_text=source_input.raw_text,
            expected_facts_json=[],
            expected_risks_json=[],
            expected_recommendations_json=[],
        ),
        uploaded_input,
        RunMode.multi_agent,
    )
    _run_multi_agent_case(db, run, llm_client)
    if run.status != WorkflowStatus.completed:
        raise EvaluationPromotionError(
            f"multi_agent evaluation failed: Workflow ended with status {run.status.value}"
        )
    return run


def _get_or_create_existing_run_result(
    db: Session,
    evaluation_case: EvaluationCase,
    run: WorkflowRun,
) -> EvaluationResult:
    existing = (
        db.query(EvaluationResult)
        .filter(
            EvaluationResult.evaluation_case_id == evaluation_case.id,
            EvaluationResult.workflow_run_id == run.id,
            EvaluationResult.run_mode == run.run_mode,
            EvaluationResult.status == EvaluationRunStatus.completed,
        )
        .first()
    )
    if existing is not None:
        return existing

    result = EvaluationResult(
        evaluation_case_id=evaluation_case.id,
        workflow_run_id=run.id,
        run_mode=run.run_mode,
        status=EvaluationRunStatus.completed,
    )
    _score_existing_run_result(db, result, evaluation_case, run)
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def _score_existing_run_result(
    db: Session,
    result: EvaluationResult,
    evaluation_case: EvaluationCase,
    run: WorkflowRun,
) -> None:
    scores = calculate_sales_evaluation_scores(evaluation_case, run.final_output)
    result.factual_accuracy = scores.factual_accuracy
    result.unsupported_claim_rate = scores.unsupported_claim_rate
    result.completeness_score = scores.completeness_score
    result.judge_notes = scores.deterministic_notes
    result.retry_count = run.retry_count
    result.cost = run.total_cost
    result.latency_ms = run.latency_ms
    result.prompt_version_summary_json = _prompt_version_summary(db, run)


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


def _prompt_version_summary(db: Session, run: WorkflowRun) -> dict[str, str | None]:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run.id).all()
    summary: dict[str, str | None] = {}
    for step in sorted(steps, key=lambda item: item.step_order):
        summary[step.agent_type] = (
            str(step.prompt_version_id) if step.prompt_version_id is not None else None
        )
    return summary


def _promotion_result(
    evaluation_case: EvaluationCase,
    baseline_result: EvaluationResult,
    multi_agent_result: EvaluationResult,
) -> EvaluationPromotionResult:
    if baseline_result.workflow_run_id is None or multi_agent_result.workflow_run_id is None:
        raise EvaluationPromotionError("Promoted comparison did not link both workflow runs")

    return EvaluationPromotionResult(
        evaluation_case_id=evaluation_case.id,
        baseline_result_id=baseline_result.id,
        multi_agent_result_id=multi_agent_result.id,
        baseline_run_id=baseline_result.workflow_run_id,
        multi_agent_run_id=multi_agent_result.workflow_run_id,
        comparison_url=f"/workflow-comparison?search={quote(evaluation_case.title)}",
    )


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
