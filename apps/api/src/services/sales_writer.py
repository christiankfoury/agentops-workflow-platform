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
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.llm_client import TextResponse
from src.services.sales_analyst import SalesAnalysisOutput
from src.services.workflow_state import transition

SALES_WRITER_AGENT_NAME = "Writer Agent"


class WriterRunError(Exception):
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


def run_sales_writer(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    run = _lock_run(db, run)
    uploaded_input = _validate_run_and_get_input(db, run)
    analyst_step = _get_completed_analyst_step(db, run.id)
    approval = _get_latest_approved_human_approval(db, run.id)
    reviewer_step = _get_latest_completed_reviewer_step(db, run.id)
    _ensure_writer_allowed(approval, reviewer_step)
    analyst_output = _get_writer_analysis(analyst_step, approval)
    _ensure_no_writer_started(db, run.id)
    prompt = _get_active_writer_prompt(db)
    step_order = _next_step_order(db, run.id)
    agent_input = {
        "workflow_run_id": str(run.id),
        "input_id": str(uploaded_input.id),
        "source_title": uploaded_input.title,
        "source_text": uploaded_input.raw_text,
        "analyst_step_id": str(analyst_step.id),
        "reviewer_step_id": str(reviewer_step.id) if reviewer_step is not None else None,
        "analysis": analyst_output.model_dump(),
        "analysis_source": "human_edited"
        if approval is not None and approval.edited_analysis_json is not None
        else "analyst",
    }
    if approval is not None:
        agent_input["human_approval_id"] = str(approval.id)
        agent_input["human_feedback"] = approval.human_feedback

    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=SALES_WRITER_AGENT_NAME,
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

    started = time.perf_counter()
    try:
        response = llm_client.generate_text(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Create a polished executive summary for leadership using only "
                        "the approved sales analysis and source report below.\n\n"
                        f"Source title: {uploaded_input.title}\n\n"
                        f"Source notes: {uploaded_input.notes or 'None'}\n\n"
                        f"Source sales report:\n{uploaded_input.raw_text}\n\n"
                        f"Approved analysis JSON:\n{analyst_output.model_dump()}\n\n"
                        f"Human feedback: {approval.human_feedback if approval else 'None'}"
                    ),
                }
            ],
            system=prompt.template,
        )
    except Exception as e:
        _mark_step_failed(step, str(e), started, db)
        transition(run, WorkflowStatus.failed, db)
        return step

    final_output = response.content.strip()
    if not final_output:
        _mark_step_failed(step, "Writer returned empty final output", started, db)
        transition(run, WorkflowStatus.failed, db)
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
    _update_run_metrics(run, db)
    transition(run, WorkflowStatus.completed, db)
    return step


def _lock_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    query = db.query(WorkflowRun).filter(WorkflowRun.id == run.id)
    if hasattr(query, "with_for_update"):
        query = query.with_for_update()
    locked_run = query.first()
    if locked_run is None:
        raise WriterRunError("Workflow run not found")
    return locked_run


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.writer_running:
        raise WriterRunError("Writer can only run after approval")
    if run.workflow_type != WorkflowType.sales_report:
        raise WriterRunError("Writer only supports sales report workflows")
    if run.run_mode != RunMode.multi_agent:
        raise WriterRunError("Writer only runs for multi-agent workflows")
    if run.input_id is None:
        raise WriterRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise WriterRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.sales_report:
        raise WriterRunError("Uploaded input must be a sales report")
    return uploaded_input


def _get_completed_analyst_step(db: Session, run_id: uuid.UUID) -> AgentStep:
    analyst_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == AgentType.analyst.value,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    if not analyst_steps:
        raise WriterRunError("Completed analyst step not found")
    return max(analyst_steps, key=lambda step: step.step_order)


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
    raise WriterRunError("Writer requires approved human approval or reviewer approval")


def _get_writer_analysis(
    analyst_step: AgentStep,
    approval: HumanApproval | None,
) -> SalesAnalysisOutput:
    analysis = (
        approval.edited_analysis_json
        if approval is not None and approval.edited_analysis_json is not None
        else analyst_step.output_json
    )
    if analysis is None:
        raise WriterRunError("Approved analysis not found")
    try:
        return SalesAnalysisOutput.model_validate(analysis)
    except ValidationError as e:
        raise WriterRunError(f"Approved analysis is invalid: {e}") from e


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
        raise WriterRunError("Writer already running for workflow run")
    if any(step.status == AgentStepStatus.completed for step in writer_steps):
        raise WriterRunError("Writer already completed for workflow run")


def _get_active_writer_prompt(db: Session) -> PromptVersion:
    prompt = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == AgentType.writer,
            PromptVersion.name == SALES_WRITER_AGENT_NAME,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .first()
    )
    if prompt is None:
        raise WriterRunError("Active Writer prompt not found")
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
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run.id).all()
    completed_steps = [step for step in steps if step.status == AgentStepStatus.completed]
    total_tokens = sum(step.total_tokens or 0 for step in completed_steps)
    total_latency = sum(step.latency_ms or 0 for step in completed_steps)
    costs = [step.cost for step in completed_steps if step.cost is not None]

    run.total_tokens = total_tokens or None
    run.latency_ms = total_latency or None
    run.total_cost = sum(costs) if costs else None
    db.commit()
    db.refresh(run)
