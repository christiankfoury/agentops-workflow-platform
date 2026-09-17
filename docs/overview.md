# AgentOps Workflow Platform

AgentOps is a durable AI workflow platform for building, running, debugging and
evaluating business automations. Published graphs combine LLM calls, registered
code, tools, conditions, human approvals, transforms, parallel branches and delays.
PostgreSQL stores accepted work, immutable versions, attempts and decisions;
separate workers execute it. The [architecture](ARCHITECTURE.md) explains the
boundaries; the [evidence index](PLATFORM_EVIDENCE.md) maps R01–R14 to delivery.

## The problem it addresses

A generated answer is only part of an automation. The system also needs to know
which version ran, what a reviewer approved, whether a timed-out write actually
happened, and what can safely resume after a worker dies. AgentOps makes those
questions inspectable in retained execution history.

Authors edit drafts in the [builder](WORKFLOW_BUILDER.md). Administrators publish
validated immutable versions. Operators start/control runs, reviewers decide
approvals, and viewers inspect their organization's data. The
[debugger](WORKFLOW_DEBUGGER.md) shows the pinned graph, selected edges, steps,
attempts, tool effects and approvals. [Operations](WORKER_OPERATIONS.md) shows
queued work, stale leases, recovery, worker presence and observed throughput.

## Three business examples

| Example | Processing | Output |
| --- | --- | --- |
| Sales | Revenue/pipeline/churn text → analyst → reviewer → human approval → writer | Executive summary with findings, risks and evidence |
| Customer feedback | Comments or normalized CSV → classifier → insight → reviewer → human approval → writer | Product insights with themes and supporting examples |
| Incident | Timestamped events → timeline → root cause → reviewer → human approval → writer | Report separating confirmed facts, likely causes and unknowns |

These are published templates on the generic runtime, with retained historical
views and one-step baseline versions. Published business templates require approval
even after favorable review. Bounded quality revisions retain prior feedback;
the writer consumes the approved payload, including human edits. See
[business templates](BUSINESS_TEMPLATES.md) and [agents](AGENTS.md).
The [upload API](../apps/api/src/routers/uploaded_inputs.py) accepts pasted text
and `.txt`, `.md`, `.csv` files; PDF/DOCX ingestion is not implemented.

## What durability means

Acceptance commits the run, version, idempotency receipt and initial job before
HTTP 202. Worker leases and fencing reject late results from expired owners.
Approval, delay and backoff waits release worker slots. Cancellation retains
partial history; it cannot undo an action already accepted by a provider.

External effects use stable keys, a ledger and adapter-specific reconciliation.
Ambiguous writes without sufficient evidence stay `unknown`. This is at-least-once
execution with guarded effects, not a universal exactly-once guarantee. See
[queue ownership](DURABLE_QUEUE.md), [effect contracts](TOOL_CONTRACTS.md) and
[explicit recovery](WORKFLOW_RECOVERY.md).

## Evidence and limits

| Evidence | Recorded result | Boundary |
| --- | --- | --- |
| [Benchmark](BENCHMARK_RESULTS.md) | 10,000 completed workflows; 33,333 jobs; 3,333 sink effects; zero loss/duplication | Deterministic service-level workload on one shared host; no paid LLMs or HTTP/OIDC admission load |
| [Fault experiments](RELIABILITY_RESULTS.md) | 45 cases across three repetitions; all 72 accepted identities accounted for | Includes expected failures/cancellations and three intentionally unresolved remote outcomes |
| [Kubernetes operations](KUBERNETES_OPERATIONS_RESULTS.md) | 21/21 workflows completed with 21 effects from 23 requests | Owned single-node kind cluster; idempotent fixture; metadata-only compatible release |
| [Evaluation](EVALUATION.md) | Deterministic scoring; 30 base cases plus two demo showcases | Seeded quality/cost/latency examples do not establish live-provider improvement |

HTTP REST, restricted PostgreSQL reads and GitHub issue tools are implemented.
Declared LLM tool calls use the same governed executor. Manual starts, signed
webhooks and timezone-aware cron schedules share versioned admission. Verified
OIDC sessions, memberships and service scopes enforce organization access.

Hosted rollout, real provider/account acceptance, multi-node availability and a
production security assessment remain unperformed. Arbitrary uploaded code,
billing, general notifications, evaluation caching and additional integrations
are outside this delivery. See [deployment](DEPLOYMENT.md),
[security](../SECURITY.md), [deferred work](deferred-phases.md) and the
[phase ledger](phase-progress.md).
