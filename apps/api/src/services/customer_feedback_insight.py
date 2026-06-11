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
from src.schemas.customer_feedback import (
    CustomerFeedbackClassificationOutput,
    ProductInsightOutput,
)
from src.services.cost_tracking import record_agent_cost, update_workflow_cost_totals
from src.services.llm_client import StructuredResponse
from src.services.workflow_events import (
    log_agent_completed,
    log_agent_failed,
    log_agent_started,
    log_workflow_event,
)

CUSTOMER_FEEDBACK_INSIGHT_AGENT_NAME = "Customer Feedback Insight Agent"


def _feedback_example_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "text": {"type": "string", "minLength": 1},
            "source": {"type": ["string", "null"]},
        },
        "required": ["text", "source"],
        "additionalProperties": False,
    }


CUSTOMER_FEEDBACK_INSIGHT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "top_insights": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "customer_pain_points": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "feature_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "request": {"type": "string", "minLength": 1},
                    "count": {"type": "integer", "minimum": 0},
                    "supporting_examples": {
                        "type": "array",
                        "items": _feedback_example_schema(),
                    },
                },
                "required": ["request", "count", "supporting_examples"],
                "additionalProperties": False,
            },
        },
        "risks": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "recommendation": {"type": "string", "minLength": 1},
                    "rationale": {"type": "string", "minLength": 1},
                    "supporting_examples": {
                        "type": "array",
                        "items": _feedback_example_schema(),
                    },
                },
                "required": ["recommendation", "rationale", "supporting_examples"],
                "additionalProperties": False,
            },
        },
        "supporting_examples": {
            "type": "array",
            "items": _feedback_example_schema(),
        },
    },
    "required": [
        "top_insights",
        "customer_pain_points",
        "feature_requests",
        "risks",
        "recommendations",
        "supporting_examples",
    ],
    "additionalProperties": False,
}


class InsightRunError(Exception):
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


def run_customer_feedback_insight(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    uploaded_input = _validate_run_and_get_input(db, run)
    classifier_output = _get_latest_classifier_output(db, run.id)
    prompt = _get_active_insight_prompt(db)
    step_order = _next_step_order(db, run.id)
    _set_run_status(run, WorkflowStatus.analyst_running, db)
    agent_input = {
        "workflow_run_id": str(run.id),
        "input_id": str(uploaded_input.id),
        "title": uploaded_input.title,
        "raw_text": uploaded_input.raw_text,
        "notes": uploaded_input.notes,
        "classification": classifier_output.model_dump(),
    }
    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=CUSTOMER_FEEDBACK_INSIGHT_AGENT_NAME,
        agent_type=AgentType.insight.value,
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
        response = llm_client.generate_structured(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Turn this classified customer feedback into product insights. "
                        "Use only the source feedback and classifier output as support.\n\n"
                        f"Title: {uploaded_input.title}\n\n"
                        f"Notes: {uploaded_input.notes or 'None'}\n\n"
                        f"Customer feedback:\n{uploaded_input.raw_text}\n\n"
                        f"Classifier output JSON:\n{classifier_output.model_dump()}"
                    ),
                }
            ],
            system=prompt.template,
            schema=CUSTOMER_FEEDBACK_INSIGHT_SCHEMA,
        )
        output = ProductInsightOutput.model_validate(response.data)
    except (Exception, ValidationError) as e:
        _mark_step_failed(step, str(e), started, db)
        log_agent_failed(db, run, step, str(e))
        _set_run_status(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Workflow failed during customer feedback insight execution.",
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
    if run.status != WorkflowStatus.running:
        raise InsightRunError("Insight agent can only run from running workflows")
    if run.workflow_type != WorkflowType.customer_feedback:
        raise InsightRunError("Insight agent only supports customer feedback workflows")
    if run.run_mode != RunMode.multi_agent:
        raise InsightRunError("Insight agent only runs for multi-agent workflows")
    if run.input_id is None:
        raise InsightRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise InsightRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.customer_feedback:
        raise InsightRunError("Uploaded input must be customer feedback")
    return uploaded_input


def _get_latest_classifier_output(
    db: Session, run_id: uuid.UUID
) -> CustomerFeedbackClassificationOutput:
    classifier_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == AgentType.classifier.value,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    if not classifier_steps:
        raise InsightRunError("Completed classifier output not found")
    classifier_step = max(classifier_steps, key=lambda step: step.step_order)
    if classifier_step.output_json is None:
        raise InsightRunError("Completed classifier step has no output")
    try:
        return CustomerFeedbackClassificationOutput.model_validate(classifier_step.output_json)
    except ValidationError as e:
        raise InsightRunError("Completed classifier output is invalid") from e


def _get_active_insight_prompt(db: Session) -> PromptVersion:
    prompt = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == AgentType.insight,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .order_by(PromptVersion.version.desc(), PromptVersion.created_at.desc())
        .first()
    )
    if prompt is None:
        raise InsightRunError("Active Insight prompt not found")
    return prompt


def _next_step_order(db: Session, run_id: uuid.UUID) -> int:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run_id).all()
    return max((step.step_order for step in steps), default=0) + 1
