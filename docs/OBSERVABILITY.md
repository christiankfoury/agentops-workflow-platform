# Observability

AgentOps stores workflow observability in the database so every run can be
inspected after execution.

## Event Model

`workflow_events` records lifecycle events:

- `workflow_started`
- `workflow_completed`
- `workflow_failed`
- `workflow_cancelled`
- `agent_started`
- `agent_completed`
- `agent_failed`
- `reviewer_rejected_output`
- `retry_triggered`
- `human_approval_required`
- `human_edited_analysis`
- `human_approved`
- `human_rejected`
- `human_requested_retry`

Each event stores:

- Workflow run ID.
- Optional agent step ID.
- Event type.
- Message.
- Metadata JSON.
- Error message.
- Created timestamp.

## Agent Step Telemetry

`agent_steps` stores:

- Agent name and type.
- Step order.
- Status.
- Input and output JSON.
- Model.
- Prompt version.
- Input/output/total tokens.
- Cost.
- Latency.
- Retry count.
- Error message.
- Created/completed timestamps.

## Cost Telemetry

Cost is tracked at two levels:

- `agent_steps` stores per-agent cost and token usage.
- `cost_events` records normalized cost entries for dashboards.

Workflow totals are recalculated from completed steps where needed.

## Dashboards

Observability is surfaced through:

- Workflow detail timeline: `/workflow-runs/:id`
- Cost dashboard: `/costs`
- Agent performance: `/agent-performance`
- Failure explorer: `/failures`
- Improvement tracking: `/improvements`

## Failure Handling

Agent failures should:

1. Mark the current `agent_step` as failed.
2. Store the error message.
3. Transition the workflow to `failed` where appropriate.
4. Log `agent_failed` or `workflow_failed`.
5. Keep enough metadata for the failure explorer and agent performance dashboard.

Cancellation uses `services/workflow_recovery.py` to mark running steps failed and
log `workflow_cancelled`.

## Operational Notes

The current implementation uses database-backed observability. Future production
deployment could add external telemetry such as OpenTelemetry or hosted tracing,
but the database trace remains the source of truth for portfolio demos and tests.
