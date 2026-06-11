from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.agent_settings import (
    AgentRuntimeConfig,
    AgentSettingsError,
    get_agent_runtime_config,
)
from src.services.cost_tracking import record_agent_cost, update_workflow_cost_totals
from src.services.llm_client import StructuredResponse
from src.services.structured_output_guardrails import validate_or_repair_structured_response
from src.services.workflow_events import (
    log_agent_completed,
    log_agent_failed,
    log_agent_started,
    log_workflow_event,
)

SALES_ANALYST_AGENT_NAME = "Sales Analyst Agent"

SALES_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "key_findings": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "opportunities": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "supporting_evidence": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "key_findings",
        "risks",
        "opportunities",
        "recommendations",
        "supporting_evidence",
    ],
    "additionalProperties": False,
}


class AnalystRunError(Exception):
    pass


class SalesAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_findings: list[str]
    risks: list[str]
    opportunities: list[str]
    recommendations: list[str]
    supporting_evidence: list[str]


class LLMClientLike(Protocol):
    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        pass


def run_sales_analyst(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    uploaded_input = _validate_run_and_get_input(db, run)
    retry_context = _get_retry_context(db, run) if run.status == WorkflowStatus.retrying else None
    if run.status == WorkflowStatus.retrying:
        run.retry_count = (run.retry_count or 0) + 1
        db.commit()
        db.refresh(run)
    runtime_config = _get_sales_analyst_runtime_config(db)
    prompt = runtime_config.prompt
    step_order = _next_step_order(db, run.id)
    if retry_context is None:
        _set_run_status(run, WorkflowStatus.running, db)
    _set_run_status(run, WorkflowStatus.analyst_running, db)
    agent_input = {
        "workflow_run_id": str(run.id),
        "input_id": str(uploaded_input.id),
        "title": uploaded_input.title,
        "raw_text": uploaded_input.raw_text,
        "notes": uploaded_input.notes,
        "retry_count": run.retry_count or 0,
    }
    if retry_context is not None:
        agent_input["retry_reason"] = retry_context["retry_reason"]
        agent_input["reviewer_feedback"] = retry_context["reviewer_feedback"]
        if retry_context.get("human_feedback") is not None:
            agent_input["human_feedback"] = retry_context["human_feedback"]
        if retry_context.get("edited_analysis_json") is not None:
            agent_input["edited_analysis_json"] = retry_context["edited_analysis_json"]
    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=SALES_ANALYST_AGENT_NAME,
        agent_type=AgentType.analyst.value,
        step_order=step_order,
        status=AgentStepStatus.running,
        input_json=agent_input,
        prompt_version_id=prompt.id,
        retry_count=run.retry_count or 0,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    log_agent_started(db, run, step)

    started = time.perf_counter()
    try:
        user_content = (
            "Analyze this sales report and return structured JSON.\n\n"
            f"Title: {uploaded_input.title}\n\n"
            f"Notes: {uploaded_input.notes or 'None'}\n\n"
            f"Sales report:\n{uploaded_input.raw_text}"
        )
        if retry_context is not None:
            user_content += (
                "\n\nThis is a retry. Address the reviewer feedback below while "
                "still using only facts supported by the source input.\n\n"
                f"Retry reason: {retry_context['retry_reason']}\n\n"
                f"Reviewer feedback: {retry_context['reviewer_feedback']}"
            )
            if retry_context.get("human_feedback") is not None:
                user_content += f"\n\nHuman feedback: {retry_context['human_feedback']}"
            if retry_context.get("edited_analysis_json") is not None:
                user_content += (
                    "\n\nHuman-edited analysis JSON: "
                    f"{retry_context['edited_analysis_json']}"
                )
        messages = [{"role": "user", "content": user_content}]
        response = llm_client.generate_structured(
            messages=messages,
            system=prompt.template,
            schema=SALES_ANALYSIS_SCHEMA,
            **runtime_config.generation_kwargs(),
        )
        output, response = validate_or_repair_structured_response(
            response=response,
            output_model=SalesAnalysisOutput,
            llm_client=llm_client,
            messages=messages,
            system=prompt.template,
            schema=SALES_ANALYSIS_SCHEMA,
            request_kwargs=runtime_config.generation_kwargs(),
        )
    except (Exception, ValidationError) as e:
        _mark_step_failed(step, str(e), started, db)
        log_agent_failed(db, run, step, str(e))
        _set_run_status(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Workflow failed during analyst execution.",
            agent_step=step,
            error_message=str(e),
        )
        return step

    latency_ms = int((time.perf_counter() - started) * 1000)
    step.status = AgentStepStatus.completed
    step.output_json = output.model_dump()
    step.model = response.model
    step.tokens_input = response.usage.input_tokens
    step.tokens_output = response.usage.output_tokens
    step.total_tokens = response.usage.total_tokens
    step.latency_ms = latency_ms
    step.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(step)
    record_agent_cost(db, step)
    update_workflow_cost_totals(db, run)
    log_agent_completed(db, run, step)
    _set_run_status(run, WorkflowStatus.reviewer_running, db)
    return step


def _mark_step_failed(
    step: AgentStep,
    error_message: str,
    started: float,
    db: Session,
) -> None:
    step.status = AgentStepStatus.failed
    step.error_message = error_message
    step.latency_ms = int((time.perf_counter() - started) * 1000)
    step.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(step)


def _set_run_status(run: WorkflowRun, status: WorkflowStatus, db: Session) -> None:
    run.status = status
    if status in {
        WorkflowStatus.completed,
        WorkflowStatus.failed,
        WorkflowStatus.cancelled,
    }:
        run.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status not in {WorkflowStatus.created, WorkflowStatus.retrying}:
        raise AnalystRunError("Sales analyst can only run from created or retrying workflows")
    if run.workflow_type != WorkflowType.sales_report:
        raise AnalystRunError("Sales analyst only supports sales report workflows")
    if run.run_mode != RunMode.multi_agent:
        raise AnalystRunError("Sales analyst only runs for multi-agent workflows")
    if run.input_id is None:
        raise AnalystRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise AnalystRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.sales_report:
        raise AnalystRunError("Uploaded input must be a sales report")
    return uploaded_input


def _get_retry_context(db: Session, run: WorkflowRun) -> dict[str, Any]:
    reviewer_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run.id,
            AgentStep.agent_type == AgentType.reviewer.value,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    if not reviewer_steps:
        raise AnalystRunError("Completed reviewer feedback not found for retry")
    reviewer_step = max(reviewer_steps, key=lambda step: step.step_order)
    if reviewer_step.output_json is None:
        raise AnalystRunError("Completed reviewer step has no output")

    quality_score = reviewer_step.output_json.get("quality_score")
    issues = reviewer_step.output_json.get("issues", [])
    retry_recommended = reviewer_step.output_json.get("retry_recommended")
    reasons: list[str] = []
    if retry_recommended:
        reasons.append("Reviewer recommended retry")
    if isinstance(quality_score, int | float) and quality_score < 0.70:
        reasons.append("Quality score is below 0.70")
    if any(issue.get("severity") == "high" for issue in issues if isinstance(issue, dict)):
        reasons.append("High severity reviewer issue")

    latest_human_retry = _get_latest_human_retry(db, run.id)
    context = {
        "retry_reason": "; ".join(reasons) or "Reviewer requested revised analysis",
        "reviewer_feedback": reviewer_step.output_json,
    }
    if latest_human_retry is not None:
        if latest_human_retry.human_feedback is not None:
            context["human_feedback"] = latest_human_retry.human_feedback
        if latest_human_retry.edited_analysis_json is not None:
            context["edited_analysis_json"] = latest_human_retry.edited_analysis_json
    return context


def _get_latest_human_retry(db: Session, run_id: uuid.UUID) -> HumanApproval | None:
    retry_approvals = (
        db.query(HumanApproval)
        .filter(
            HumanApproval.workflow_run_id == run_id,
            HumanApproval.status == ApprovalStatus.retry_requested,
        )
        .all()
    )
    if not retry_approvals:
        return None
    return max(retry_approvals, key=lambda approval: approval.resolved_at or approval.created_at)


def _get_sales_analyst_runtime_config(db: Session) -> AgentRuntimeConfig:
    try:
        return get_agent_runtime_config(db, AgentType.analyst)
    except AgentSettingsError as e:
        raise AnalystRunError("Active Sales Analyst prompt not found") from e


def _next_step_order(db: Session, run_id: uuid.UUID) -> int:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run_id).all()
    return max((step.step_order for step in steps), default=0) + 1
