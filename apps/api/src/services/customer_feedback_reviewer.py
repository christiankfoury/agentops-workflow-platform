from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.schemas.customer_feedback import ProductInsightOutput
from src.services.cost_tracking import record_agent_cost, update_workflow_cost_totals
from src.services.human_approvals import create_pending_human_approval
from src.services.llm_client import StructuredResponse
from src.services.sales_reviewer import SALES_REVIEW_SCHEMA, SalesReviewOutput
from src.services.structured_output_guardrails import validate_or_repair_structured_response
from src.services.workflow_events import (
    log_agent_completed,
    log_agent_failed,
    log_agent_started,
    log_workflow_event,
)

CUSTOMER_FEEDBACK_REVIEWER_AGENT_NAME = "Reviewer Agent"


class CustomerFeedbackReviewerRunError(Exception):
    pass


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


def run_customer_feedback_reviewer(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    run = _lock_run(db, run)
    uploaded_input = _validate_run_and_get_input(db, run)
    insight_step = _get_completed_insight_step(db, run.id)
    insight_output = _validate_insight_output(insight_step)
    _ensure_no_reviewer_for_insight(db, run.id, insight_step.id)
    prompt = _get_active_reviewer_prompt(db)
    step_order = _next_step_order(db, run.id)
    agent_input = {
        "workflow_run_id": str(run.id),
        "input_id": str(uploaded_input.id),
        "source_title": uploaded_input.title,
        "source_text": uploaded_input.raw_text,
        "insight_step_id": str(insight_step.id),
        "insight_output": insight_output.model_dump(),
    }
    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=CUSTOMER_FEEDBACK_REVIEWER_AGENT_NAME,
        agent_type=AgentType.reviewer.value,
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
        messages = [
            {
                "role": "user",
                "content": (
                    "Review the Customer Feedback Insight Agent output against the "
                    "source feedback. Check whether insights, risks, feature requests, "
                    "and recommendations are supported by actual feedback examples. "
                    "Return structured JSON with approval, quality score, issues, and "
                    "retry recommendation.\n\n"
                    f"Source title: {uploaded_input.title}\n\n"
                    f"Source notes: {uploaded_input.notes or 'None'}\n\n"
                    f"Source customer feedback:\n{uploaded_input.raw_text}\n\n"
                    f"Insight output JSON:\n{insight_output.model_dump()}"
                ),
            }
        ]
        response = llm_client.generate_structured(
            messages=messages,
            system=prompt.template,
            schema=SALES_REVIEW_SCHEMA,
        )
        output, response = validate_or_repair_structured_response(
            response=response,
            output_model=SalesReviewOutput,
            llm_client=llm_client,
            messages=messages,
            system=prompt.template,
            schema=SALES_REVIEW_SCHEMA,
        )
    except (Exception, ValidationError) as e:
        _mark_step_failed(step, str(e), started, db)
        log_agent_failed(db, run, step, str(e))
        _set_run_status(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Workflow failed during customer feedback reviewer execution.",
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
    _update_run_metrics(run, db)
    log_agent_completed(db, run, step)
    if not output.approved or output.issues or output.retry_recommended:
        log_workflow_event(
            db,
            run,
            WorkflowEventType.reviewer_rejected_output,
            "Reviewer flagged the customer feedback insights.",
            agent_step=step,
            metadata={
                "approved": output.approved,
                "quality_score": output.quality_score,
                "issues": [issue.model_dump() for issue in output.issues],
                "retry_recommended": output.retry_recommended,
            },
        )
    _set_run_status(run, WorkflowStatus.waiting_for_human, db)
    create_pending_human_approval(db, run)
    return step


def _lock_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    query = db.query(WorkflowRun).filter(WorkflowRun.id == run.id)
    if hasattr(query, "with_for_update"):
        query = query.with_for_update()
    locked_run = query.first()
    if locked_run is None:
        raise CustomerFeedbackReviewerRunError("Workflow run not found")
    return locked_run


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.reviewer_running:
        raise CustomerFeedbackReviewerRunError("Reviewer can only run after insight completion")
    if run.workflow_type != WorkflowType.customer_feedback:
        raise CustomerFeedbackReviewerRunError(
            "Reviewer only supports customer feedback workflows"
        )
    if run.run_mode != RunMode.multi_agent:
        raise CustomerFeedbackReviewerRunError("Reviewer only runs for multi-agent workflows")
    if run.input_id is None:
        raise CustomerFeedbackReviewerRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise CustomerFeedbackReviewerRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.customer_feedback:
        raise CustomerFeedbackReviewerRunError("Uploaded input must be customer feedback")
    return uploaded_input


def _get_completed_insight_step(db: Session, run_id: uuid.UUID) -> AgentStep:
    insight_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == AgentType.insight.value,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    if not insight_steps:
        raise CustomerFeedbackReviewerRunError("Completed insight step not found")
    return max(insight_steps, key=lambda step: step.step_order)


def _validate_insight_output(insight_step: AgentStep) -> ProductInsightOutput:
    if insight_step.output_json is None:
        raise CustomerFeedbackReviewerRunError("Completed insight step has no output")
    try:
        return ProductInsightOutput.model_validate(insight_step.output_json)
    except ValidationError as e:
        raise CustomerFeedbackReviewerRunError("Completed insight output is invalid") from e


def _ensure_no_reviewer_for_insight(
    db: Session,
    run_id: uuid.UUID,
    insight_step_id: uuid.UUID,
) -> None:
    reviewer_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == AgentType.reviewer.value,
        )
        .all()
    )
    for step in reviewer_steps:
        if step.status == AgentStepStatus.running:
            raise CustomerFeedbackReviewerRunError("Reviewer already running for workflow run")
        if step.status == AgentStepStatus.completed and (
            step.input_json or {}
        ).get("insight_step_id") == str(insight_step_id):
            raise CustomerFeedbackReviewerRunError("Reviewer already completed for insight step")


def _get_active_reviewer_prompt(db: Session) -> PromptVersion:
    prompt = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == AgentType.reviewer,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .order_by(PromptVersion.version.desc(), PromptVersion.created_at.desc())
        .first()
    )
    if prompt is None:
        raise CustomerFeedbackReviewerRunError("Active Reviewer prompt not found")
    return prompt


def _next_step_order(db: Session, run_id: uuid.UUID) -> int:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run_id).all()
    return max((step.step_order for step in steps), default=0) + 1


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


def _update_run_metrics(run: WorkflowRun, db: Session) -> None:
    update_workflow_cost_totals(db, run)
    reviewer_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run.id,
            AgentStep.agent_type == AgentType.reviewer.value,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    if reviewer_steps:
        latest_review = max(reviewer_steps, key=lambda step: step.step_order)
        quality_score = (latest_review.output_json or {}).get("quality_score")
        run.quality_score = float(quality_score) if quality_score is not None else None
    db.commit()
    db.refresh(run)


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
