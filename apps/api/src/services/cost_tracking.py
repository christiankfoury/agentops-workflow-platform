from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.cost_event import CostEvent
from src.models.workflow_run import WorkflowRun
from src.observability.platform_telemetry import emit_agent_step_telemetry

TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


DEFAULT_PRICING = ModelPricing(input_per_million=0.40, output_per_million=1.60)
MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-4.1-mini": DEFAULT_PRICING,
    "gpt-4.1": ModelPricing(input_per_million=2.00, output_per_million=8.00),
    "gpt-4o-mini": ModelPricing(input_per_million=0.15, output_per_million=0.60),
    "gpt-4o": ModelPricing(input_per_million=2.50, output_per_million=10.00),
}


def estimate_token_cost(
    model: str | None,
    tokens_input: int | None,
    tokens_output: int | None,
) -> tuple[float, float, float]:
    input_tokens = tokens_input or 0
    output_tokens = tokens_output or 0
    pricing = MODEL_PRICING.get(model or "", DEFAULT_PRICING)
    cost_input = (input_tokens / TOKENS_PER_MILLION) * pricing.input_per_million
    cost_output = (output_tokens / TOKENS_PER_MILLION) * pricing.output_per_million
    total_cost = cost_input + cost_output
    return cost_input, cost_output, total_cost


def record_agent_cost(db: Session, step: AgentStep) -> CostEvent | None:
    if step.status != AgentStepStatus.completed:
        return None
    if step.model is None or step.tokens_input is None or step.tokens_output is None:
        return None
    if _cost_event_exists(db, step):
        return None

    cost_input, cost_output, total_cost = estimate_token_cost(
        step.model,
        step.tokens_input,
        step.tokens_output,
    )
    step.cost = total_cost
    event = CostEvent(
        workflow_run_id=step.workflow_run_id,
        agent_step_id=step.id,
        model=step.model,
        tokens_input=step.tokens_input,
        tokens_output=step.tokens_output,
        total_tokens=step.total_tokens or step.tokens_input + step.tokens_output,
        cost_input=cost_input,
        cost_output=cost_output,
        total_cost=total_cost,
    )
    db.add(event)
    db.commit()
    db.refresh(step)
    run = db.query(WorkflowRun).filter(WorkflowRun.id == step.workflow_run_id).first()
    emit_agent_step_telemetry(step, run=run, estimated_cost_usd=total_cost)
    return event


def update_workflow_cost_totals(db: Session, run: WorkflowRun) -> WorkflowRun:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run.id).all()
    completed_steps = [step for step in steps if step.status == AgentStepStatus.completed]
    total_tokens = sum(step.total_tokens or 0 for step in completed_steps)
    total_latency = sum(step.latency_ms or 0 for step in completed_steps)
    total_cost = sum(step.cost or 0 for step in completed_steps)

    run.total_tokens = total_tokens or None
    run.latency_ms = total_latency or None
    run.total_cost = total_cost or None
    db.commit()
    db.refresh(run)
    return run


def _cost_event_exists(db: Session, step: AgentStep) -> bool:
    existing = (
        db.query(CostEvent)
        .filter(
            CostEvent.workflow_run_id == step.workflow_run_id,
            CostEvent.agent_step_id == step.id,
        )
        .first()
    )
    return existing is not None
