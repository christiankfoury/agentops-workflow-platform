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
from src.schemas.incident import IncidentRootCauseOutput, IncidentTimelineOutput
from src.services.agent_settings import (
    AgentRuntimeConfig,
    AgentSettingsError,
    get_agent_runtime_config,
)
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

INCIDENT_REVIEWER_AGENT_NAME = "Reviewer Agent"


class IncidentReviewerRunError(Exception):
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


def run_incident_reviewer(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    run = _lock_run(db, run)
    uploaded_input = _validate_run_and_get_input(db, run)
    timeline_step = _get_completed_step(db, run.id, AgentType.timeline)
    root_step = _get_completed_step(db, run.id, AgentType.root_cause)
    timeline_output = _validate_timeline_output(timeline_step)
    root_output = _validate_root_output(root_step)
    _ensure_no_reviewer_for_root_cause(db, run.id, root_step.id)
    runtime_config = _get_reviewer_runtime_config(db)
    prompt = runtime_config.prompt
    step_order = _next_step_order(db, run.id)
    agent_input = {
        "workflow_run_id": str(run.id),
        "input_id": str(uploaded_input.id),
        "source_title": uploaded_input.title,
        "source_text": uploaded_input.raw_text,
        "timeline_step_id": str(timeline_step.id),
        "root_cause_step_id": str(root_step.id),
        "timeline": timeline_output.model_dump(),
        "root_cause": root_output.model_dump(),
    }
    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=INCIDENT_REVIEWER_AGENT_NAME,
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
                    "Review the incident timeline and root-cause analysis against "
                    "the source log. Check timeline accuracy, root-cause support, "
                    "whether inferred claims are clearly labeled, and whether "
                    "follow-up actions are reasonable.\n\n"
                    f"Source title: {uploaded_input.title}\n\n"
                    f"Source notes: {uploaded_input.notes or 'None'}\n\n"
                    f"Source incident log:\n{uploaded_input.raw_text}\n\n"
                    f"Timeline JSON:\n{timeline_output.model_dump()}\n\n"
                    f"Root cause JSON:\n{root_output.model_dump()}"
                ),
            }
        ]
        response = llm_client.generate_structured(
            messages=messages,
            system=prompt.template,
            schema=SALES_REVIEW_SCHEMA,
            **runtime_config.generation_kwargs(),
        )
        output, response = validate_or_repair_structured_response(
            response=response,
            output_model=SalesReviewOutput,
            llm_client=llm_client,
            messages=messages,
            system=prompt.template,
            schema=SALES_REVIEW_SCHEMA,
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
            "Workflow failed during incident reviewer execution.",
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
            "Reviewer flagged the incident analysis.",
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
        raise IncidentReviewerRunError("Workflow run not found")
    return locked_run


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.reviewer_running:
        raise IncidentReviewerRunError("Reviewer can only run after root cause completion")
    if run.workflow_type != WorkflowType.incident_log:
        raise IncidentReviewerRunError("Reviewer only supports incident log workflows")
    if run.run_mode != RunMode.multi_agent:
        raise IncidentReviewerRunError("Reviewer only runs for multi-agent workflows")
    if run.input_id is None:
        raise IncidentReviewerRunError("Workflow run must have an uploaded input")
    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise IncidentReviewerRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.incident_log:
        raise IncidentReviewerRunError("Uploaded input must be an incident log")
    return uploaded_input


def _get_completed_step(db: Session, run_id: uuid.UUID, agent_type: AgentType) -> AgentStep:
    steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == agent_type.value,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    if not steps:
        raise IncidentReviewerRunError(f"Completed {agent_type.value} step not found")
    return max(steps, key=lambda step: step.step_order)


def _validate_timeline_output(step: AgentStep) -> IncidentTimelineOutput:
    if step.output_json is None:
        raise IncidentReviewerRunError("Completed timeline step has no output")
    try:
        return IncidentTimelineOutput.model_validate(step.output_json)
    except ValidationError as e:
        raise IncidentReviewerRunError("Completed timeline output is invalid") from e


def _validate_root_output(step: AgentStep) -> IncidentRootCauseOutput:
    if step.output_json is None:
        raise IncidentReviewerRunError("Completed root cause step has no output")
    try:
        return IncidentRootCauseOutput.model_validate(step.output_json)
    except ValidationError as e:
        raise IncidentReviewerRunError("Completed root cause output is invalid") from e


def _ensure_no_reviewer_for_root_cause(
    db: Session,
    run_id: uuid.UUID,
    root_step_id: uuid.UUID,
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
            raise IncidentReviewerRunError("Reviewer already running for workflow run")
        if step.status == AgentStepStatus.completed and (
            step.input_json or {}
        ).get("root_cause_step_id") == str(root_step_id):
            raise IncidentReviewerRunError("Reviewer already completed for root cause step")


def _get_reviewer_runtime_config(db: Session) -> AgentRuntimeConfig:
    try:
        return get_agent_runtime_config(db, AgentType.reviewer)
    except AgentSettingsError as e:
        raise IncidentReviewerRunError("Active Reviewer prompt not found") from e


def _next_step_order(db: Session, run_id: uuid.UUID) -> int:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run_id).all()
    return max((step.step_order for step in steps), default=0) + 1


def _mark_step_failed(step: AgentStep, error_message: str, started: float, db: Session) -> None:
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
