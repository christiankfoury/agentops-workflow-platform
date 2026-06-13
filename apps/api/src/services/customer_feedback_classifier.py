from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.schemas.customer_feedback import CustomerFeedbackClassificationOutput
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

CUSTOMER_FEEDBACK_CLASSIFIER_AGENT_NAME = "Customer Feedback Classifier Agent"

CUSTOMER_FEEDBACK_CLASSIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": [
                            "pricing",
                            "bugs",
                            "feature_requests",
                            "performance",
                            "usability",
                            "support_experience",
                            "other",
                        ],
                    },
                    "count": {"type": "integer", "minimum": 0},
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative", "mixed"],
                    },
                    "examples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "minLength": 1},
                                "source": {"type": ["string", "null"]},
                            },
                            "required": ["text", "source"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name", "count", "sentiment", "examples"],
                "additionalProperties": False,
            },
        },
        "sentiment_patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative", "mixed"],
                    },
                    "count": {"type": "integer", "minimum": 0},
                    "summary": {"type": "string", "minLength": 1},
                },
                "required": ["sentiment", "count", "summary"],
                "additionalProperties": False,
            },
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
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "minLength": 1},
                                "source": {"type": ["string", "null"]},
                            },
                            "required": ["text", "source"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["request", "count", "supporting_examples"],
                "additionalProperties": False,
            },
        },
        "bug_reports": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string", "minLength": 1},
                    "count": {"type": "integer", "minimum": 0},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "supporting_examples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "minLength": 1},
                                "source": {"type": ["string", "null"]},
                            },
                            "required": ["text", "source"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["issue", "count", "severity", "supporting_examples"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["themes", "sentiment_patterns", "feature_requests", "bug_reports"],
    "additionalProperties": False,
}


class ClassifierRunError(Exception):
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


def run_customer_feedback_classifier(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    uploaded_input = _validate_run_and_get_input(db, run)
    runtime_config = _get_classifier_runtime_config(db)
    prompt = runtime_config.prompt
    step_order = _next_step_order(db, run.id)
    _set_run_status(run, WorkflowStatus.running, db)
    agent_input = {
        "workflow_run_id": str(run.id),
        "input_id": str(uploaded_input.id),
        "title": uploaded_input.title,
        "raw_text": uploaded_input.raw_text,
        "notes": uploaded_input.notes,
    }
    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=CUSTOMER_FEEDBACK_CLASSIFIER_AGENT_NAME,
        agent_type=AgentType.classifier.value,
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
                    "Classify this customer feedback and return structured JSON.\n\n"
                    "Use bugs only for product defects such as crashes, freezes, "
                    "broken flows, errors, or failed uploads. Classify noisy "
                    "notifications, confusing settings, or hard-to-configure behavior "
                    "as usability unless the feedback describes a concrete defect.\n\n"
                    f"Title: {uploaded_input.title}\n\n"
                    f"Notes: {uploaded_input.notes or 'None'}\n\n"
                    f"Customer feedback:\n{uploaded_input.raw_text}"
                ),
            }
        ]
        response = llm_client.generate_structured(
            messages=messages,
            system=prompt.template,
            schema=CUSTOMER_FEEDBACK_CLASSIFICATION_SCHEMA,
            **runtime_config.generation_kwargs(),
        )
        output, response = validate_or_repair_structured_response(
            response=response,
            output_model=CustomerFeedbackClassificationOutput,
            llm_client=llm_client,
            messages=messages,
            system=prompt.template,
            schema=CUSTOMER_FEEDBACK_CLASSIFICATION_SCHEMA,
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
            "Workflow failed during customer feedback classifier execution.",
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
    if run.status != WorkflowStatus.created:
        raise ClassifierRunError("Classifier can only run from created workflows")
    if run.workflow_type != WorkflowType.customer_feedback:
        raise ClassifierRunError("Classifier only supports customer feedback workflows")
    if run.run_mode != RunMode.multi_agent:
        raise ClassifierRunError("Classifier only runs for multi-agent workflows")
    if run.input_id is None:
        raise ClassifierRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise ClassifierRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.customer_feedback:
        raise ClassifierRunError("Uploaded input must be customer feedback")
    return uploaded_input


def _get_classifier_runtime_config(db: Session) -> AgentRuntimeConfig:
    try:
        return get_agent_runtime_config(db, AgentType.classifier)
    except AgentSettingsError as e:
        raise ClassifierRunError("Active Classifier prompt not found") from e


def _next_step_order(db: Session, run_id: uuid.UUID) -> int:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run_id).all()
    return max((step.step_order for step in steps), default=0) + 1
