# Observability

PostgreSQL retains the canonical workflow trace. Generic history and legacy
business projections are different views of the same work; do not add them
together. [Architecture](ARCHITECTURE.md) · [Evidence index](PLATFORM_EVIDENCE.md).

## Execution trace

The [generic debugger](WORKFLOW_DEBUGGER.md) at `/execution-traces` exposes the
run's immutable graph and current edge checkpoint. Select retained logical steps
by node/branch/iteration, then numbered attempts for their inputs, outputs,
status, typed failures, timing and optional LLM usage. Separate paginated readers
show events, approvals and redacted tool request/result/reconciliation records.

State and lifecycle events commit in the same fenced transaction. A timeout,
cancellation or expired lease retains its attempt and reason; a replacement does
not overwrite it. Unknown effects and incomplete provider usage remain explicit.
A linked recovery points back to its source and reused checkpoints.
[Trace implementation](../apps/api/src/services/execution_traces.py) ·
[Recovery](WORKFLOW_RECOVERY.md).

Lists contain bounded metadata; payloads load on explicit inspection and can be
truncated. Claim/reservation tokens and credential digests are excluded. Known
credential names and URL user information are masked, but arbitrary secrets in
prose cannot be recognized reliably. Credentials belong in configured references,
not graph payloads.

## Business and cost projections

`workflow_runs`, `agent_steps`, `workflow_events`, `human_approvals`, `cost_events`
and evaluation results preserve the business dashboard contracts. Durable workers
update these atomically from canonical execution. Historical AgentStep-only runs
keep their original labels and totals without invented versions/attempts.
[Projection service](../apps/api/src/services/business_projection.py).

Per-attempt returned usage includes schema repairs and failed responses where
usage was observed. Configured model rates estimate cost; they are not reconciled
provider invoices. Unknown pricing stays unavailable and abrupt worker death can
leave remote usage unknown. Reused recovery outputs create no fabricated calls
or charges. [LLM accounting](LLM_EXECUTION.md).

## Operations and live views

[Worker operations](WORKER_OPERATIONS.md) defines `/operations`, tenant metrics,
job filters, persisted queue waits, claims, abandoned attempts and recoveries.
Throughput is completed workflows in a trailing 900-second window divided by 900;
it is not a capacity benchmark. Job, attempt and workflow counts have different
denominators. Retrying is a subset of queued work, not an extra total.

Presence heartbeats describe availability; the job lease/token remains ownership
authority. Tenant views expose only observed workers associated with that tenant's
jobs. Zero observed workers alone does not prove a fleet outage. Infrastructure
operators can export aggregate metrics with `python -m src.operations_metrics`;
Kubernetes runs that CLI in a CronJob. No public global-metrics endpoint or full
Prometheus/Grafana deployment is bundled.

Small authorized pulses refresh changed run, approval, debugger and operations
pages. Active details poll at five seconds, waits/aggregate views at 15 seconds;
errors back off, hidden/offline tabs pause, terminal details stop polling. Payloads
are not downloaded repeatedly for closed records. [Live-update behavior](WORKER_OPERATIONS.md#live-update-behavior).

## Diagnosis and evidence

1. Inspect queued/oldest-ready work and due times before treating a wait as a stall.
2. For stale claims, inspect lease recovery, abandoned attempts and remaining bounds.
3. For unknown writes, inspect receipt/reconciliation evidence before recovery.
4. For usage differences, separate returned attempt usage from unknown remote spend
   and avoid summing compatibility projections.
5. For quality comparisons, distinguish seeded records from generated/scored output
   and automatic approval from individual review.

[Benchmark](BENCHMARK_RESULTS.md), [fault experiments](RELIABILITY_RESULTS.md) and
[Kubernetes operations](KUBERNETES_OPERATIONS_RESULTS.md) retain raw histories and
metrics with their measurement boundaries. Optional external usage telemetry is
[documented separately](TELEMETRY.md); hosted tracing/OpenTelemetry is not bundled.
