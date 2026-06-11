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
from src.schemas.incident import IncidentTimelineOutput
from src.services.cost_tracking import record_agent_cost, update_workflow_cost_totals
from src.services.llm_client import StructuredResponse
from src.services.structured_output_guardrails import validate_or_repair_structured_response
from src.services.workflow_events import (
    log_agent_completed,
    log_agent_failed,
    log_agent_started,
    log_workflow_event,
)

INCIDENT_TIMELINE_AGENT_NAME = "Timeline Agent"

INCIDENT_TIMELINE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "time": {"type": "string", "minLength": 1},
                    "event": {"type": "string", "minLength": 1},
                    "source_evidence": {"type": "string", "minLength": 1},
                },
                "required": ["time", "event", "source_evidence"],
                "additionalProperties": False,
            },
        },
        "ambiguous_events": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
    },
    "required": ["timeline", "ambiguous_events"],
    "additionalProperties": False,
}


class TimelineRunError(Exception):
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


def run_incident_timeline(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    uploaded_input = _validate_run_and_get_input(db, run)
    prompt = _get_active_timeline_prompt(db)
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
        agent_name=INCIDENT_TIMELINE_AGENT_NAME,
        agent_type=AgentType.timeline.value,
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
                    "Extract a precise chronological timeline from this incident log. "
                    "Preserve each timestamp, event description, and exact source "
                    "evidence. Put unclear or missing-timestamp items in "
                    "ambiguous_events.\n\n"
                    f"Title: {uploaded_input.title}\n\n"
                    f"Notes: {uploaded_input.notes or 'None'}\n\n"
                    f"Incident log:\n{uploaded_input.raw_text}"
                ),
            }
        ]
        response = llm_client.generate_structured(
            messages=messages,
            system=prompt.template,
            schema=INCIDENT_TIMELINE_SCHEMA,
        )
        output, response = validate_or_repair_structured_response(
            response=response,
            output_model=IncidentTimelineOutput,
            llm_client=llm_client,
            messages=messages,
            system=prompt.template,
            schema=INCIDENT_TIMELINE_SCHEMA,
        )
    except (Exception, ValidationError) as e:
        _mark_step_failed(step, str(e), started, db)
        log_agent_failed(db, run, step, str(e))
        _set_run_status(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Workflow failed during incident timeline execution.",
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
        raise TimelineRunError("Timeline agent can only run from created workflows")
    if run.workflow_type != WorkflowType.incident_log:
        raise TimelineRunError("Timeline agent only supports incident log workflows")
    if run.run_mode != RunMode.multi_agent:
        raise TimelineRunError("Timeline agent only runs for multi-agent workflows")
    if run.input_id is None:
        raise TimelineRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise TimelineRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.incident_log:
        raise TimelineRunError("Uploaded input must be an incident log")
    return uploaded_input


def _get_active_timeline_prompt(db: Session) -> PromptVersion:
    prompt = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == AgentType.timeline,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .order_by(PromptVersion.version.desc(), PromptVersion.created_at.desc())
        .first()
    )
    if prompt is None:
        raise TimelineRunError("Active Timeline prompt not found")
    return prompt


def _next_step_order(db: Session, run_id: uuid.UUID) -> int:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run_id).all()
    return max((step.step_order for step in steps), default=0) + 1
