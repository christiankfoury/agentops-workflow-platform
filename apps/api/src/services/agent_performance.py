from collections import defaultdict

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.schemas.agent_performance import AgentPerformanceSummaryRead

SCHEMA_VALIDATION_MARKERS = (
    "schema validation",
    "structured output failed validation",
    "validation error",
    "invalid json",
)


def summarize_agent_performance(
    steps: list[AgentStep],
    events: list[WorkflowEvent],
) -> list[AgentPerformanceSummaryRead]:
    schema_failure_step_ids = _schema_failure_step_ids(events)
    grouped_steps: dict[str, list[AgentStep]] = defaultdict(list)
    for step in steps:
        grouped_steps[step.agent_type].append(step)

    summaries = [
        _summarize_agent_steps(agent_type, agent_steps, schema_failure_step_ids)
        for agent_type, agent_steps in grouped_steps.items()
    ]
    return sorted(summaries, key=lambda summary: summary.agent_type)


def _summarize_agent_steps(
    agent_type: str,
    steps: list[AgentStep],
    schema_failure_step_ids: set[object],
) -> AgentPerformanceSummaryRead:
    step_count = len(steps)
    completed_count = sum(1 for step in steps if step.status == AgentStepStatus.completed)
    failed_count = sum(1 for step in steps if step.status == AgentStepStatus.failed)
    retry_count = sum(1 for step in steps if step.retry_count > 0)
    schema_validation_failure_count = sum(
        1
        for step in steps
        if step.id in schema_failure_step_ids or _contains_schema_failure_marker(step.error_message)
    )
    latency_values = [step.latency_ms for step in steps if step.latency_ms is not None]
    cost_values = [step.cost for step in steps if step.cost is not None]
    reviewer_scores = [
        float(step.output_json["quality_score"])
        for step in steps
        if step.agent_type == "reviewer"
        and isinstance(step.output_json, dict)
        and isinstance(step.output_json.get("quality_score"), int | float)
    ]

    return AgentPerformanceSummaryRead(
        agent_type=agent_type,
        agent_name=_display_agent_name(agent_type, steps),
        step_count=step_count,
        completed_count=completed_count,
        failed_count=failed_count,
        retry_count=retry_count,
        schema_validation_failure_count=schema_validation_failure_count,
        average_latency_ms=_average(latency_values),
        average_cost=_average(cost_values),
        failure_rate=_rate(failed_count, step_count),
        retry_rate=_rate(retry_count, step_count),
        average_reviewer_score=_average(reviewer_scores) if reviewer_scores else None,
        schema_validation_failure_rate=_rate(schema_validation_failure_count, step_count),
    )


def _schema_failure_step_ids(events: list[WorkflowEvent]) -> set[object]:
    return {
        event.agent_step_id
        for event in events
        if event.agent_step_id is not None
        and event.event_type in {WorkflowEventType.agent_failed, WorkflowEventType.workflow_failed}
        and (
            _contains_schema_failure_marker(event.error_message)
            or _contains_schema_failure_marker(event.message)
        )
    }


def _contains_schema_failure_marker(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.lower()
    return any(marker in normalized for marker in SCHEMA_VALIDATION_MARKERS)


def _display_agent_name(agent_type: str, steps: list[AgentStep]) -> str:
    names = [step.agent_name for step in steps if step.agent_name]
    if names:
        return max(set(names), key=names.count)
    return agent_type.replace("_", " ").title()


def _average(values: list[int | float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return count / total
