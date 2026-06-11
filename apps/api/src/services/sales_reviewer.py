from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.cost_tracking import record_agent_cost, update_workflow_cost_totals
from src.services.human_approvals import create_pending_human_approval
from src.services.llm_client import StructuredResponse
from src.services.sales_analyst import SalesAnalysisOutput
from src.services.workflow_events import (
    log_agent_completed,
    log_agent_failed,
    log_agent_started,
    log_workflow_event,
)

SALES_REVIEWER_AGENT_NAME = "Reviewer Agent"
QUALITY_APPROVAL_THRESHOLD = 0.85
HUMAN_REVIEW_THRESHOLD = 0.70
MAX_AUTO_RETRIES = 2

SALES_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "quality_score": {"type": "number", "minimum": 0, "maximum": 1},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "problem": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["claim", "problem", "severity"],
                "additionalProperties": False,
            },
        },
        "retry_recommended": {"type": "boolean"},
    },
    "required": ["approved", "quality_score", "issues", "retry_recommended"],
    "additionalProperties": False,
}


class ReviewerRunError(Exception):
    pass


class ReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    problem: str
    severity: Literal["low", "medium", "high"]


class SalesReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    quality_score: float = Field(ge=0, le=1)
    issues: list[ReviewIssue]
    retry_recommended: bool


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


def run_sales_reviewer(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    run = _lock_run(db, run)
    uploaded_input = _validate_run_and_get_input(db, run)
    analyst_step = _get_completed_analyst_step(db, run.id)
    analyst_output = _validate_analyst_output(analyst_step)
    _ensure_no_reviewer_for_analyst(db, run.id, analyst_step.id)
    prompt = _get_active_reviewer_prompt(db)
    step_order = _next_step_order(db, run.id)
    agent_input = {
        "workflow_run_id": str(run.id),
        "input_id": str(uploaded_input.id),
        "source_title": uploaded_input.title,
        "source_text": uploaded_input.raw_text,
        "analyst_step_id": str(analyst_step.id),
        "analyst_output": analyst_output.model_dump(),
    }
    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=SALES_REVIEWER_AGENT_NAME,
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
        response = llm_client.generate_structured(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Review the Sales Analyst Agent output against the source sales report. "
                        "Return structured JSON with approval, quality score, issues, and retry "
                        "recommendation.\n\n"
                        f"Source title: {uploaded_input.title}\n\n"
                        f"Source notes: {uploaded_input.notes or 'None'}\n\n"
                        f"Source sales report:\n{uploaded_input.raw_text}\n\n"
                        f"Analyst output JSON:\n{analyst_output.model_dump()}"
                    ),
                }
            ],
            system=prompt.template,
            schema=SALES_REVIEW_SCHEMA,
        )
        output = SalesReviewOutput.model_validate(response.data)
    except (Exception, ValidationError) as e:
        _mark_step_failed(step, str(e), started, db)
        log_agent_failed(db, run, step, str(e))
        _set_run_status(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Workflow failed during reviewer execution.",
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
            "Reviewer flagged the analyst output.",
            agent_step=step,
            metadata={
                "approved": output.approved,
                "quality_score": output.quality_score,
                "issues": [issue.model_dump() for issue in output.issues],
                "retry_recommended": output.retry_recommended,
            },
        )
    next_status = _next_status_after_review(run, output)
    if next_status == WorkflowStatus.retrying:
        log_workflow_event(
            db,
            run,
            WorkflowEventType.retry_triggered,
            "Automatic retry triggered from reviewer result.",
            agent_step=step,
            metadata={
                "quality_score": output.quality_score,
                "retry_count": run.retry_count or 0,
                "max_auto_retries": MAX_AUTO_RETRIES,
            },
        )
    _set_run_status(run, next_status, db)
    if next_status == WorkflowStatus.waiting_for_human:
        create_pending_human_approval(db, run)
    return step


def _lock_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    query = db.query(WorkflowRun).filter(WorkflowRun.id == run.id)
    if hasattr(query, "with_for_update"):
        query = query.with_for_update()
    locked_run = query.first()
    if locked_run is None:
        raise ReviewerRunError("Workflow run not found")
    return locked_run


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.reviewer_running:
        raise ReviewerRunError("Reviewer can only run after analyst completion")
    if run.workflow_type != WorkflowType.sales_report:
        raise ReviewerRunError("Reviewer only supports sales report workflows")
    if run.run_mode != RunMode.multi_agent:
        raise ReviewerRunError("Reviewer only runs for multi-agent workflows")
    if run.input_id is None:
        raise ReviewerRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise ReviewerRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.sales_report:
        raise ReviewerRunError("Uploaded input must be a sales report")
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
        raise ReviewerRunError("Completed analyst step not found")
    analyst_step = max(analyst_steps, key=lambda step: step.step_order)
    return analyst_step


def _validate_analyst_output(analyst_step: AgentStep) -> SalesAnalysisOutput:
    if analyst_step.output_json is None:
        raise ReviewerRunError("Completed analyst step has no output")
    try:
        return SalesAnalysisOutput.model_validate(analyst_step.output_json)
    except ValidationError as e:
        raise ReviewerRunError(f"Completed analyst step output is invalid: {e}") from e


def _ensure_no_reviewer_for_analyst(
    db: Session,
    run_id: uuid.UUID,
    analyst_step_id: uuid.UUID,
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
            raise ReviewerRunError("Reviewer already running for workflow run")
        if step.status == AgentStepStatus.completed and (
            step.input_json or {}
        ).get("analyst_step_id") == str(analyst_step_id):
            raise ReviewerRunError("Reviewer already completed for analyst step")


def _get_active_reviewer_prompt(db: Session) -> PromptVersion:
    prompt = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == AgentType.reviewer,
            PromptVersion.name == SALES_REVIEWER_AGENT_NAME,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .first()
    )
    if prompt is None:
        raise ReviewerRunError("Active Reviewer prompt not found")
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
    completed_steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run.id,
            AgentStep.status == AgentStepStatus.completed,
        )
        .all()
    )
    reviewer_steps = [
        step
        for step in completed_steps
        if step.agent_type == AgentType.reviewer.value and step.output_json is not None
    ]

    if reviewer_steps:
        latest_review = max(reviewer_steps, key=lambda step: step.step_order)
        quality_score = latest_review.output_json.get("quality_score")
        run.quality_score = float(quality_score) if quality_score is not None else None
    db.commit()
    db.refresh(run)


def _next_status_after_review(run: WorkflowRun, output: SalesReviewOutput) -> WorkflowStatus:
    has_high_severity_issue = any(issue.severity == "high" for issue in output.issues)
    needs_retry = (
        output.quality_score < HUMAN_REVIEW_THRESHOLD
        or has_high_severity_issue
        or output.retry_recommended
    )
    if needs_retry and (run.retry_count or 0) < MAX_AUTO_RETRIES:
        return WorkflowStatus.retrying

    if output.quality_score >= QUALITY_APPROVAL_THRESHOLD and output.approved:
        return WorkflowStatus.waiting_for_human

    return WorkflowStatus.waiting_for_human


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
