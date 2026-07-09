import uuid
from typing import Any

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.models.workflow_run import WorkflowRun
from src.observability.platform_telemetry import emit_agent_step_telemetry


def log_workflow_event(
    db: Session,
    run: WorkflowRun,
    event_type: WorkflowEventType,
    message: str,
    *,
    agent_step: AgentStep | None = None,
    metadata: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> WorkflowEvent:
    event = WorkflowEvent(
        workflow_run_id=run.id,
        agent_step_id=agent_step.id if agent_step is not None else None,
        event_type=event_type,
        message=message,
        metadata_json=_json_safe(metadata),
        error_message=error_message,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def log_agent_started(db: Session, run: WorkflowRun, step: AgentStep) -> WorkflowEvent:
    return log_workflow_event(
        db,
        run,
        WorkflowEventType.agent_started,
        f"{step.agent_name} started.",
        agent_step=step,
        metadata={
            "agent_name": step.agent_name,
            "agent_type": step.agent_type,
            "step_order": step.step_order,
            "retry_count": step.retry_count,
        },
    )


def log_agent_completed(db: Session, run: WorkflowRun, step: AgentStep) -> WorkflowEvent:
    return log_workflow_event(
        db,
        run,
        WorkflowEventType.agent_completed,
        f"{step.agent_name} completed.",
        agent_step=step,
        metadata={
            "agent_name": step.agent_name,
            "agent_type": step.agent_type,
            "step_order": step.step_order,
            "latency_ms": step.latency_ms,
            "total_tokens": step.total_tokens,
            "cost": step.cost,
            "retry_count": step.retry_count,
        },
    )


def log_agent_failed(
    db: Session,
    run: WorkflowRun,
    step: AgentStep,
    error_message: str,
) -> WorkflowEvent:
    emit_agent_step_telemetry(
        step,
        run=run,
        error_category=_error_category(error_message),
    )
    return log_workflow_event(
        db,
        run,
        WorkflowEventType.agent_failed,
        f"{step.agent_name} failed.",
        agent_step=step,
        metadata={
            "agent_name": step.agent_name,
            "agent_type": step.agent_type,
            "step_order": step.step_order,
            "latency_ms": step.latency_ms,
            "retry_count": step.retry_count,
        },
        error_message=error_message,
    )


def _error_category(error_message: str) -> str:
    lowered = error_message.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return "provider_timeout"
    if "rate limit" in lowered or "429" in lowered:
        return "rate_limited"
    if "validation" in lowered or "schema" in lowered:
        return "validation_error"
    if "llm" in lowered or "provider" in lowered or "openai" in lowered:
        return "provider_error"
    return "unknown"


def _json_safe(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None
    return {key: _json_safe_value(value) for key, value in metadata.items()}


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe_value(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    return value
