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
from src.schemas.customer_feedback import ProductInsightOutput
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
from src.services.writer_inputs import CustomerFeedbackWriterInput

CUSTOMER_FEEDBACK_WRITER_AGENT_NAME = "Writer Agent"


class CustomerFeedbackWriterRunError(Exception):
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


def run_customer_feedback_writer(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    run = _lock_run(db, run)
    uploaded_input = _validate_run_and_get_input(db, run)
    insight_step = _get_completed_insight_step(db, run.id)
    approval = _get_latest_approved_human_approval(db, run.id)
    reviewer_step = _get_latest_completed_reviewer_step(db, run.id)
    _ensure_writer_allowed(approval, reviewer_step)
    insight_output = _get_writer_insights(insight_step, approval)
    _ensure_no_writer_started(db, run.id)
    runtime_config = _get_writer_runtime_config(db)
    prompt = runtime_config.prompt
    step_order = _next_step_order(db, run.id)
    agent_input = CustomerFeedbackWriterInput(
        workflow_run_id=str(run.id),
        input_id=str(uploaded_input.id),
        source_title=uploaded_input.title,
        source_text=uploaded_input.raw_text,
        insight_step_id=str(insight_step.id),
        reviewer_step_id=str(reviewer_step.id) if reviewer_step is not None else None,
        insights=insight_output,
        insights_source="human_edited"
        if approval is not None and approval.edited_analysis_json is not None
        else "insight",
        human_approval_id=str(approval.id) if approval is not None else None,
        human_feedback=approval.human_feedback if approval is not None else None,
    ).model_dump(mode="json", exclude_none=True)

    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=CUSTOMER_FEEDBACK_WRITER_AGENT_NAME,
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
                        "Create a polished product insights report using only the approved "
                        "customer feedback insights and source feedback below.\n\n"
                        f"Source title: {uploaded_input.title}\n\n"
                        f"Source notes: {uploaded_input.notes or 'None'}\n\n"
                        f"Source customer feedback:\n{uploaded_input.raw_text}\n\n"
                        f"Approved product insights JSON:\n{insight_output.model_dump()}\n\n"
                        f"Human feedback: {approval.human_feedback if approval else 'None'}"
                    ),
                }
            ],
            system=prompt.template,
            **runtime_config.generation_kwargs(),
        )
    except Exception as e:
        _mark_step_failed(step, str(e), started, db)
        log_agent_failed(db, run, step, str(e))
        transition(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Workflow failed during customer feedback writer execution.",
            agent_step=step,
            error_message=str(e),
        )
        return step

    final_output = response.content.strip()
    if not final_output:
        error = "Writer returned empty final output"
        _mark_step_failed(step, error, started, db)
        log_agent_failed(db, run, step, error)
        transition(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Workflow failed during customer feedback writer execution.",
            agent_step=step,
            error_message=error,
        )
        return step

    latency_ms = int((time.perf_counter() - started) * 1000)
    step.status = AgentStepStatus.completed
    step.output_json = {"final_output": final_output}
    step.model = response.model
    step.tokens_input = response.usage.input_tokens
    step.tokens_output = response.usage.output_tokens
    step.total_tokens = response.usage.total_tokens
    step.latency_ms = latency_ms
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


def _lock_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    query = db.query(WorkflowRun).filter(WorkflowRun.id == run.id)
    if hasattr(query, "with_for_update"):
        query = query.with_for_update()
    locked_run = query.first()
    if locked_run is None:
        raise CustomerFeedbackWriterRunError("Workflow run not found")
    return locked_run


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.writer_running:
        raise CustomerFeedbackWriterRunError("Writer can only run after approval")
    if run.workflow_type != WorkflowType.customer_feedback:
        raise CustomerFeedbackWriterRunError("Writer only supports customer feedback workflows")
    if run.run_mode != RunMode.multi_agent:
        raise CustomerFeedbackWriterRunError("Writer only runs for multi-agent workflows")
    if run.input_id is None:
        raise CustomerFeedbackWriterRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise CustomerFeedbackWriterRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.customer_feedback:
        raise CustomerFeedbackWriterRunError("Uploaded input must be customer feedback")
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
        raise CustomerFeedbackWriterRunError("Completed insight step not found")
    return max(insight_steps, key=lambda step: step.step_order)


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
    raise CustomerFeedbackWriterRunError(
        "Writer requires approved human approval or reviewer approval"
    )


def _get_writer_insights(
    insight_step: AgentStep,
    approval: HumanApproval | None,
) -> ProductInsightOutput:
    insights = (
        approval.edited_analysis_json
        if approval is not None and approval.edited_analysis_json is not None
        else insight_step.output_json
    )
    if insights is None:
        raise CustomerFeedbackWriterRunError("Approved insights not found")
    try:
        return ProductInsightOutput.model_validate(insights)
    except ValidationError as e:
        raise CustomerFeedbackWriterRunError("Approved insights are invalid") from e


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
        raise CustomerFeedbackWriterRunError("Writer already running for workflow run")
    if any(step.status == AgentStepStatus.completed for step in writer_steps):
        raise CustomerFeedbackWriterRunError("Writer already completed for workflow run")


def _get_writer_runtime_config(db: Session) -> AgentRuntimeConfig:
    try:
        return get_agent_runtime_config(db, AgentType.writer)
    except AgentSettingsError as e:
        raise CustomerFeedbackWriterRunError("Active Writer prompt not found") from e


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
