from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.cost_tracking import record_agent_cost, update_workflow_cost_totals
from src.services.llm_client import TextResponse
from src.services.workflow_events import (
    log_agent_completed,
    log_agent_failed,
    log_agent_started,
    log_workflow_event,
)
from src.services.workflow_state import transition

SALES_BASELINE_AGENT_NAME = "Baseline Agent"
SALES_BASELINE_AGENT_TYPE = "baseline"
SALES_BASELINE_SYSTEM_PROMPT = (
    "Generate a concise executive summary for leadership directly from the supplied "
    "sales report. This is a single-agent baseline: do not mention reviewer checks, "
    "retry logic, or human approval. Use only facts supported by the source input."
)
CUSTOMER_FEEDBACK_BASELINE_SYSTEM_PROMPT = (
    "Generate a concise product insights report directly from the supplied customer "
    "feedback. This is a single-agent baseline: do not mention reviewer checks, retry "
    "logic, or human approval. Use only themes, requests, risks, and examples supported "
    "by the source feedback."
)
INCIDENT_BASELINE_SYSTEM_PROMPT = (
    "Generate a concise post-incident report directly from the supplied incident log. "
    "This is a single-agent baseline: do not mention reviewer checks, retry logic, or "
    "human approval. Use only timeline events, impact, root-cause claims, and follow-up "
    "actions supported by the source incident log."
)


class BaselineRunError(Exception):
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


def run_sales_baseline(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    uploaded_input = _validate_run_and_get_input(db, run)
    _ensure_no_baseline_started(db, run.id)
    transition(run, WorkflowStatus.running, db)
    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=SALES_BASELINE_AGENT_NAME,
        agent_type=SALES_BASELINE_AGENT_TYPE,
        step_order=_next_step_order(db, run.id),
        status=AgentStepStatus.running,
        input_json={
            "workflow_run_id": str(run.id),
            "input_id": str(uploaded_input.id),
            "title": uploaded_input.title,
            "raw_text": uploaded_input.raw_text,
            "notes": uploaded_input.notes,
            "run_mode": RunMode.baseline.value,
        },
        retry_count=0,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    log_agent_started(db, run, step)

    started = time.perf_counter()
    try:
        prompt = _baseline_prompt(uploaded_input)
        response = llm_client.generate_text(
            messages=[
                {
                    "role": "user",
                    "content": prompt["content"],
                }
            ],
            system=prompt["system"],
        )
    except Exception as e:
        _mark_step_failed(step, str(e), started, db)
        log_agent_failed(db, run, step, str(e))
        transition(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Baseline workflow failed.",
            agent_step=step,
            error_message=str(e),
        )
        return step

    final_output = response.content.strip()
    if not final_output:
        error_message = "Baseline returned empty final output"
        _mark_step_failed(step, error_message, started, db)
        log_agent_failed(db, run, step, error_message)
        transition(run, WorkflowStatus.failed, db)
        log_workflow_event(
            db,
            run,
            WorkflowEventType.workflow_failed,
            "Baseline workflow failed.",
            agent_step=step,
            error_message=error_message,
        )
        return step

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
        "Baseline workflow completed.",
        agent_step=step,
        metadata={
            "run_mode": RunMode.baseline.value,
            "total_cost": run.total_cost,
            "total_tokens": run.total_tokens,
            "latency_ms": run.latency_ms,
        },
    )
    return step


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.created:
        raise BaselineRunError("Baseline can only run from created workflows")
    if run.workflow_type not in {
        WorkflowType.sales_report,
        WorkflowType.customer_feedback,
        WorkflowType.incident_log,
    }:
        raise BaselineRunError(
            "Baseline only supports sales report, customer feedback, and incident log workflows"
        )
    if run.run_mode != RunMode.baseline:
        raise BaselineRunError("Baseline only runs for baseline workflows")
    if run.input_id is None:
        raise BaselineRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise BaselineRunError("Uploaded input not found")
    expected_input_type = InputType(run.workflow_type.value)
    if uploaded_input.input_type != expected_input_type:
        raise BaselineRunError("Uploaded input type must match workflow type")
    return uploaded_input


def _baseline_prompt(uploaded_input: UploadedInput) -> dict[str, str]:
    if uploaded_input.input_type == InputType.customer_feedback:
        return {
            "system": CUSTOMER_FEEDBACK_BASELINE_SYSTEM_PROMPT,
            "content": (
                "Create a product insights report directly from this customer feedback.\n\n"
                f"Title: {uploaded_input.title}\n\n"
                f"Notes: {uploaded_input.notes or 'None'}\n\n"
                f"Customer feedback:\n{uploaded_input.raw_text}"
            ),
        }
    if uploaded_input.input_type == InputType.incident_log:
        return {
            "system": INCIDENT_BASELINE_SYSTEM_PROMPT,
            "content": (
                "Create a post-incident report directly from this incident log.\n\n"
                f"Title: {uploaded_input.title}\n\n"
                f"Notes: {uploaded_input.notes or 'None'}\n\n"
                f"Incident log:\n{uploaded_input.raw_text}"
            ),
        }
    return {
        "system": SALES_BASELINE_SYSTEM_PROMPT,
        "content": (
            "Create an executive summary directly from this sales report.\n\n"
            f"Title: {uploaded_input.title}\n\n"
            f"Notes: {uploaded_input.notes or 'None'}\n\n"
            f"Sales report:\n{uploaded_input.raw_text}"
        ),
    }


def _ensure_no_baseline_started(db: Session, run_id: object) -> None:
    steps = (
        db.query(AgentStep)
        .filter(
            AgentStep.workflow_run_id == run_id,
            AgentStep.agent_type == SALES_BASELINE_AGENT_TYPE,
        )
        .all()
    )
    if any(step.status == AgentStepStatus.running for step in steps):
        raise BaselineRunError("Baseline already running for workflow run")
    if any(step.status == AgentStepStatus.completed for step in steps):
        raise BaselineRunError("Baseline already completed for workflow run")


def _next_step_order(db: Session, run_id: object) -> int:
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
