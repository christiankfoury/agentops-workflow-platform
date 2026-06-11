from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.llm_client import StructuredResponse
from src.services.workflow_state import transition

SALES_ANALYST_AGENT_NAME = "Sales Analyst Agent"

SALES_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "key_findings": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "opportunities": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "supporting_evidence": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "key_findings",
        "risks",
        "opportunities",
        "recommendations",
        "supporting_evidence",
    ],
    "additionalProperties": False,
}


class AnalystRunError(Exception):
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


def run_sales_analyst(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> AgentStep:
    uploaded_input = _validate_run_and_get_input(db, run)
    prompt = _get_active_sales_analyst_prompt(db)
    step_order = _next_step_order(db, run.id)
    agent_input = {
        "workflow_run_id": str(run.id),
        "input_id": str(uploaded_input.id),
        "title": uploaded_input.title,
        "raw_text": uploaded_input.raw_text,
        "notes": uploaded_input.notes,
    }
    step = AgentStep(
        workflow_run_id=run.id,
        agent_name=SALES_ANALYST_AGENT_NAME,
        agent_type=AgentType.analyst.value,
        step_order=step_order,
        status=AgentStepStatus.running,
        input_json=agent_input,
        prompt_version_id=prompt.id,
        retry_count=0,
    )
    db.add(step)
    db.commit()
    db.refresh(step)

    try:
        transition(run, WorkflowStatus.running, db)
        transition(run, WorkflowStatus.analyst_running, db)
        started = time.perf_counter()
        response = llm_client.generate_structured(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Analyze this sales report and return structured JSON.\n\n"
                        f"Title: {uploaded_input.title}\n\n"
                        f"Notes: {uploaded_input.notes or 'None'}\n\n"
                        f"Sales report:\n{uploaded_input.raw_text}"
                    ),
                }
            ],
            system=prompt.template,
            schema=SALES_ANALYSIS_SCHEMA,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        step.status = AgentStepStatus.completed
        step.output_json = response.data
        step.model = response.model
        step.tokens_input = response.usage.input_tokens
        step.tokens_output = response.usage.output_tokens
        step.total_tokens = response.usage.total_tokens
        step.latency_ms = latency_ms
        step.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(step)
        transition(run, WorkflowStatus.reviewer_running, db)
        return step
    except Exception as e:
        step.status = AgentStepStatus.failed
        step.error_message = str(e)
        step.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(step)
        transition(run, WorkflowStatus.failed, db)
        return step


def _validate_run_and_get_input(db: Session, run: WorkflowRun) -> UploadedInput:
    if run.status != WorkflowStatus.created:
        raise AnalystRunError("Sales analyst can only run from created workflows")
    if run.workflow_type != WorkflowType.sales_report:
        raise AnalystRunError("Sales analyst only supports sales report workflows")
    if run.run_mode != RunMode.multi_agent:
        raise AnalystRunError("Sales analyst only runs for multi-agent workflows")
    if run.input_id is None:
        raise AnalystRunError("Workflow run must have an uploaded input")

    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == run.input_id).first()
    if uploaded_input is None:
        raise AnalystRunError("Uploaded input not found")
    if uploaded_input.input_type != InputType.sales_report:
        raise AnalystRunError("Uploaded input must be a sales report")
    return uploaded_input


def _get_active_sales_analyst_prompt(db: Session) -> PromptVersion:
    prompt = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == AgentType.analyst,
            PromptVersion.name == SALES_ANALYST_AGENT_NAME,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .first()
    )
    if prompt is None:
        raise AnalystRunError("Active Sales Analyst prompt not found")
    return prompt


def _next_step_order(db: Session, run_id: uuid.UUID) -> int:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run_id).all()
    return max((step.step_order for step in steps), default=0) + 1
