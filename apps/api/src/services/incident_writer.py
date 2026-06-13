from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.human_approval import ApprovalStatus, HumanApproval
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
from src.services.llm_client import TextResponse
from src.services.workflow_events import (
    log_agent_completed,
    log_agent_failed,
    log_agent_started,
    log_workflow_event,
)
from src.services.workflow_state import transition
from src.services.writer_inputs import IncidentWriterInput

INCIDENT_WRITER_AGENT_NAME = "Writer Agent"


class IncidentWriterRunError(Exception):
    pass


class LLMClientLike(Protocol):
    def generate_text(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> TextResponse:
        pass


def run_incident_writer(db: Session, run: WorkflowRun, llm_client: LLMClientLike) -> AgentStep:
    run = _lock_run(db, run)
    uploaded_input = _validate_run_and_get_input(db, run)
    timeline_step = _get_completed_step(db, run.id, AgentType.timeline)
    root_step = _get_completed_step(db, run.id, AgentType.root_cause)
    approval = _get_latest_approved_human_approval(db, run.id)
    reviewer_step = _get_latest_completed_reviewer_step(db, run.id)
    _ensure_writer_allowed(approval, reviewer_step)
    timeline_output = _validate_timeline_output(timeline_step)
    root_output = _get_writer_root_cause(root_step, approval)
    _ensure_no_writer_started(db, run.id)
    runtime_config = _get_writer_runtime_config(db)
    prompt = runtime_config.prompt
    step_order = _next_step_order(db, run.id)
    agent_input = IncidentWriterInput(
        workflow_run_id=str(run.id),
        input_id=str(uploaded_input.id),
        source_title=uploaded_input.title,
        source_text=uploaded_input.raw_text,
        timeline_step_id=str(timeline_step.id),
        root_cause_step_id=str(root_step.id),
        reviewer_step_id=str(reviewer_step.id) if reviewer_step is not None else None,
        timeline=timeline_output,
        root_cause=root_output,
        root_cause_source="human_edited"
        if approval is not None and approval.edited_analysis_json is not None
        else "root_cause",
        human_approval_id=str(approval.id) if approval is not None else None,
        human_feedback=approval.human_feedback if approval is not None else None,
    ).model_dump(mode="json", exclude_none=True)

    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=INCIDENT_WRITER_AGENT_NAME,
        agent_type=AgentType.writer.value,
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
        response = llm_client.generate_text(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Create a polished post-incident report using only the approved "
                        "timeline, root-cause analysis, and source incident log below. "
                        "Clearly separate confirmed facts from inferred conclusions. "
                        "Use this executive-ready structure: Executive Summary, "
                        "Severity and Customer Impact, Timeline, Root Cause, What Fixed It, "
                        "Follow-Up Actions, and Unknowns / Evidence Limitations. Include "
                        "owner-style roles from the approved follow-up actions when present. "
                        "Avoid overstating causality: say the rollback and timing strongly "
                        "support the deployment as the likely cause unless the source proves "
                        "direct causation.\n\n"
                        f"Source title: {uploaded_input.title}\n\n"
                        f"Source notes: {uploaded_input.notes or 'None'}\n\n"
                        f"Source incident log:\n{uploaded_input.raw_text}\n\n"
                        f"Timeline JSON:\n{timeline_output.model_dump()}\n\n"
                        f"Approved root cause JSON:\n{root_output.model_dump()}\n\n"
                        f"Human feedback: {approval.human_feedback if approval else 'None'}"
                    ),
                }
            ],
            system=prompt.template,
            **runtime_config.generation_kwargs(),
        )
    except Exception as e:
        return _fail_writer(db, run, step, started, str(e))

    final_output = response.content.strip()
    if not final_output:
        return _fail_writer(db, run, step, started, "Writer returned empty final output")

    step.status = AgentStepStatus.completed
    step.output_json = {"final_output": final_output}
    step.model = response.model
    step.tokens_input = response.usage.input_tokens
    step.tokens_output = response.usage.output_tokens
    step.total_tokens = response.usage.total_tokens
    step.latency_ms = int((time.perf_counter() - started) * 1000)
    step.completed_at = datetime.now(UTC)
    run.final_output = final_output
    db.commit()
    db.refresh(step)
    record_agent_cost(db, step)
    update_workflow_cost_totals(db, run)
    log_agent_completed(db, run, step)
    transition(run, WorkflowStatus.completed, db)
    log_workflow_event(
        db,
        run,
        WorkflowEventType.workflow_completed,
        "Workflow completed.",
        agent_step=step,
        metadata={
            "quality_score": run.quality_score,
            "total_cost": run.total_cost,
            "total_tokens": run.total_tokens,
            "retry_count": run.retry_count,
        },
    )
    return step


def _fail_writer(
    db: Session,
    run: WorkflowRun,
    step: AgentStep,
    started: float,
    error_message: str,
) -> AgentStep:
    step.status = AgentStepStatus.failed
    step.error_message = error_message
    step.latency_ms = int((time.perf_counter() - started) * 1000)
    step.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(step)
    log_agent_failed(db, run, step, error_message)
    transition(run, WorkflowStatus.failed, db)
    log_workflow_event(
        db,
        run,
        WorkflowEventType.workflow_failed,
        "Workflow failed during incident writer execution.",
        agent_step=step,
        error_message=error_message,
    )
    return step


def _lock_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    query = db.query(WorkflowRun).filter(WorkflowRun.id == run.id)
    if hasattr(query, "with_for_update"):
        query = query.with_for_update()
    locked_run = query.first()
    if locked_run is None:
        raise IncidentWriterRunError("Workflow run not found")
    return locked_run


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.writer_running:
        raise IncidentWriterRunError("Writer can only run after approval")
    if run.workflow_type != WorkflowType.incident_log:
        raise IncidentWriterRunError("Writer only supports incident log workflows")
    if run.run_mode != RunMode.multi_agent:
        raise IncidentWriterRunError("Writer only runs for multi-agent workflows")
    if run.input_id is None:
        raise IncidentWriterRunError("Workflow run must have an uploaded input")
    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise IncidentWriterRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.incident_log:
        raise IncidentWriterRunError("Uploaded input must be an incident log")
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
        raise IncidentWriterRunError(f"Completed {agent_type.value} step not found")
    return max(steps, key=lambda step: step.step_order)


def _get_latest_approved_human_approval(db: Session, run_id: uuid.UUID) -> HumanApproval | None:
    approvals = (
        db.query(HumanApproval)
        .filter(
            HumanApproval.workflow_run_id == run_id,
            HumanApproval.status == ApprovalStatus.approved,
        )
        .all()
    )
    if not approvals:
        return None
    return max(approvals, key=lambda approval: approval.resolved_at or approval.created_at)


def _get_latest_completed_reviewer_step(db: Session, run_id: uuid.UUID) -> AgentStep | None:
    reviewer_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == AgentType.reviewer.value,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    if not reviewer_steps:
        return None
    return max(reviewer_steps, key=lambda step: step.step_order)


def _ensure_writer_allowed(
    approval: HumanApproval | None,
    reviewer_step: AgentStep | None,
) -> None:
    if approval is not None:
        return
    if reviewer_step is not None and (reviewer_step.output_json or {}).get("approved") is True:
        return
    raise IncidentWriterRunError("Writer requires approved human approval or reviewer approval")


def _validate_timeline_output(step: AgentStep) -> IncidentTimelineOutput:
    if step.output_json is None:
        raise IncidentWriterRunError("Completed timeline step has no output")
    try:
        return IncidentTimelineOutput.model_validate(step.output_json)
    except ValidationError as e:
        raise IncidentWriterRunError("Completed timeline output is invalid") from e


def _get_writer_root_cause(
    step: AgentStep,
    approval: HumanApproval | None,
) -> IncidentRootCauseOutput:
    root_cause = (
        approval.edited_analysis_json
        if approval is not None and approval.edited_analysis_json is not None
        else step.output_json
    )
    if root_cause is None:
        raise IncidentWriterRunError("Approved root cause not found")
    try:
        return IncidentRootCauseOutput.model_validate(root_cause)
    except ValidationError as e:
        raise IncidentWriterRunError("Approved root cause is invalid") from e


def _ensure_no_writer_started(db: Session, run_id: uuid.UUID) -> None:
    writer_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == AgentType.writer.value,
        )
        .all()
    )
    if any(step.status == AgentStepStatus.running for step in writer_steps):
        raise IncidentWriterRunError("Writer already running for workflow run")
    if any(step.status == AgentStepStatus.completed for step in writer_steps):
        raise IncidentWriterRunError("Writer already completed for workflow run")


def _get_writer_runtime_config(db: Session) -> AgentRuntimeConfig:
    try:
        return get_agent_runtime_config(db, AgentType.writer)
    except AgentSettingsError as e:
        raise IncidentWriterRunError("Active Writer prompt not found") from e


def _next_step_order(db: Session, run_id: uuid.UUID) -> int:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run_id).all()
    return max((step.step_order for step in steps), default=0) + 1
