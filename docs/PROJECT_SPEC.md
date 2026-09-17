# Workflow Platform — Project Specification

## Product contract

AgentOps builds, runs, inspects and evaluates business automations through typed,
versioned graphs. It combines LLM generation with deterministic computation,
external tools and human decisions. The original three business workflows remain
first-class templates and historical views. This specification reflects the
implemented platform; the [consolidated plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md)
owns R01–R14 scope and the [phase ledger](phase-progress.md) owns delivery status.

The portfolio claim is a traceable, recoverable workflow system with measured
local reliability. Comparative live-model quality improvement is a hypothesis to
measure, not an established result. [Evidence index](PLATFORM_EVIDENCE.md).

## Users and permissions

| Role | Permitted work |
| --- | --- |
| Viewer | Read/export organization data |
| Operator | Read, draft, upload, start and control permitted workflows |
| Reviewer | Read and decide/edit/retry/reject approvals |
| Admin | All above; publish, manage members/prompts/settings/tools/triggers; resolve effects and override high-severity findings |

Verified issuer/subject identity and active memberships determine roles. Caller
role/actor/organization fields cannot grant authority. Service principals require
an allowed role and explicit action scopes; they cannot create browser sessions.
Approval/control transactions recheck current permission. Organization scope
covers nested resources, aggregates, exports, prompts/settings, tools, triggers
and traces. Local prototype identity behavior is restricted to development/test.
[Permission implementation](../apps/api/src/services/permissions.py) ·
[Identity contract](IDENTITY.md).

## Definitions and execution primitives

An editable definition has revisioned drafts and immutable published versions.
A run pins one version, its input and its accepted runtime settings. Publication
validates schemas, references, reachability, routing, joins and tool policies.
The builder also requires runnable validation; direct API publication can retain
a recognized graph with an unavailable code handler. Every start independently
checks runtime capability before accepting work.
Archived versions stay readable to their existing runs. No arbitrary graph cycles,
uploaded executable code or dynamic imports are supported.

| Primitive | Contract |
| --- | --- |
| `llm` | Pinned prompt/model/configuration, structured output, bounded repair and optional declared tools |
| `code` | Server-registered deterministic handler and version |
| `tool` | Tenant-owned pinned HTTP, PostgreSQL or GitHub contract |
| `condition` | Ordered constrained boolean cases and explicit default route |
| `approval` | Durable exact-payload review, edit/replacement, rejection or bounded revision request |
| `transform` | Typed bindings and constrained expressions |
| `parallel` | Explicit fork branches and one all-selected join |
| `delay` | Persisted duration or absolute wake time, releasing worker capacity |

The [graph format](WORKFLOW_GRAPH.md) is canonical for bounds and schemas;
[executor registration](../apps/api/src/services/execution_registry.py) is canonical
for runnable capabilities. Non-LLM steps do not invent agent names, model usage
or token costs.

## Durable lifecycle

1. Manual, webhook and scheduled admission use the same versioned start contract.
   Commit the start receipt, execution, initial job and audit/events before 202.
2. Workers claim due jobs with leases/tokens and prepare attempts in short
   transactions. Perform I/O outside locks, then recheck ownership and revision.
3. Commit outputs, events, terminal timestamps and downstream scheduling together.
   Retain logical node/branch/iteration identity and each numbered attempt.
4. Persist waits and retry due times; recover expired ownership within its bounds.
   A stale owner cannot commit after replacement.
5. Terminal runs remain terminal. Explicit linked recovery retains source history,
   checkpoint/effect provenance and spent budgets, with fresh required approvals.

The state authority covers generic and legacy live transitions. Execution states
are pending/running/waiting/retrying/completed/failed/cancelled. Step, attempt and
job state sets are distinct. See [records](EXECUTION_RECORDS.md),
[queue](DURABLE_QUEUE.md), [retry/deadline policy](RETRIES_AND_DEADLINES.md) and
[recovery](WORKFLOW_RECOVERY.md).

### Retry, cancellation and idempotency limits

Infrastructure retries use error classes, attempt bounds, persisted backoff/jitter
and attempt/run deadlines. Quality revisions repeat only an explicitly bounded
review region and retain feedback independently of infrastructure attempt numbers.
Generic SDK retries are disabled; schema repairs share the attempt deadline.

A start key is organization-scoped and bound to a canonical request fingerprint.
Identical retries return the original run; changed requests conflict. Receipts
have no expiry/reuse API while history is retained. Cancellation stops new work
and fences results; supported I/O is cooperatively aborted. It cannot reverse an
already accepted remote effect or forcibly stop arbitrary synchronous Python.

External writes need stable logical effect keys and provider-specific idempotency
or reconciliation. Ambiguous outcomes stay unknown instead of being blindly
retried. An administrator's resolution requires evidence and cannot itself resend
an action. No universal exactly-once effect guarantee is made.
[Effect contract](TOOL_CONTRACTS.md).

## Tools and triggers

- [HTTP REST](HTTP_TOOL.md): operator-configured destinations/methods, bounded
  request/response sizes, vetted addresses, protected credentials and explicit
  provider idempotency guarantees. Defaults deny network destinations.
- [PostgreSQL](POSTGRESQL_TOOL.md): configured parameterized query aliases over
  restricted read-only connections; no arbitrary query/connection input.
- [GitHub](GITHUB_TOOL.md): configured repository issue reads and approved creation;
  persisted correlation supports bounded ambiguous-write reconciliation.
- [LLM tool calling](LLM_TOOL_CALLING.md): declared tools only, retained call and
  continuation identities, exact approval for writes, bounded calls/rounds/cost/time.
- [Webhooks](WEBHOOK_TRIGGERS.md): signature, freshness, event identity, payload
  bounds and configured tenant/definition/service-principal binding.
- [Cron](SCHEDULED_TRIGGERS.md): five fields, IANA timezone, no overlap, coalesced
  missed ticks and replica-safe admission. Version selection is pinned per fire.

Contract/fixture validation is implemented. Real account acceptance is separately
authorized and is not inferred from a fake GitHub server or local HTTP sink.

## Business workflow requirements retained

| Workflow | Specialist chain | Review/output contract |
| --- | --- | --- |
| Sales report | Analyst extracts findings, risks, recommendations and evidence | Reviewer checks support; mandatory approval; writer produces executive summary |
| Customer feedback | Classifier groups comments; insight extracts themes and examples | Reviewer checks source support; approval/edit; writer produces product report |
| Incident log | Timeline preserves events; root cause separates confirmed/inferred/unknown | Reviewer checks causal claims; approval/edit; writer produces post-incident report |

A router can classify input type with confidence and explicit fallback. Each
workflow also has a one-step baseline. Published multi-agent templates use bounded
quality revisions and mandatory approval; the writer consumes the approved edited
payload. Existing typed schemas enforce business constraints beyond graph types.
Pasted text and `.txt`, `.md`, `.csv` ingestion are supported. Source facts remain
separate from evaluation answer keys and reviewer guidance.
[Agents](AGENTS.md) · [Published templates](BUSINESS_TEMPLATES.md).

Historical runs retain AgentStep, approval, cost and evaluation views. Durable
runs have one canonical execution owner plus atomic compatibility projections;
legacy per-agent controls cannot also execute them. Backout flags change future
starts only. No historical graph/attempt data is fabricated and no retained
execution history is silently discarded by migration downgrade.

## Product surfaces

The [builder](WORKFLOW_BUILDER.md) supports typed node forms, JSON schema/binding
editors, saved revision conflicts, validation, publication, history/diffs and
idempotent manual starts. Trigger forms expose configuration and delivery history.
The [debugger](WORKFLOW_DEBUGGER.md) shows immutable topology, selected edges,
inputs/outputs, attempts, usage, tools, approvals, errors and wait reasons.
Controls expose cancellation, expired-claim recovery and linked terminal recovery.

Business run creation/details/final output, structured approval edits, prompt
versions/settings, evaluation/comparison, costs, agent performance, failures and
improvement views remain. Evaluation exports are JSON/CSV/Markdown. Live views use
bounded authorized polling with backoff and offline/hidden-tab behavior.
[Operations](WORKER_OPERATIONS.md) and [observability](OBSERVABILITY.md) define the
queue, worker, wait, throughput and usage measurements.

## Evaluation and cost requirements

The base corpus has ten sales, ten feedback and ten incident cases; demo seeding
adds two sales showcases. Deterministic scoring compares generated final output
with stored facts, risks, recommendations, themes and timeline expectations.
Keyword/numeric heuristics are not a semantic truth oracle or an additional LLM
judge. Baseline and multi-agent comparisons expose quality, cost, latency, retries
and approval policy. Automatic evaluation approvals are explicitly labeled and
must not be mistaken for individual human review.

Model/prompt identity, returned tokens, latency and configured price estimates are
retained. Unknown cost/usage is not fabricated; abandoned calls may have unobserved
provider spend. Generic attempts and business cost projections are the same
accounting, not additive charges. Seeded demonstration numbers are illustrative.
No measured live-provider uplift percentage is available in this delivery.
[Evaluation methodology](EVALUATION.md) · [LLM accounting](LLM_EXECUTION.md).

## Deployment, acceptance and exclusions

Production web/API/worker images, secret references, readiness, migration Jobs,
resource limits, local persistent PostgreSQL and a hosted external-database
profile are implemented. Local authenticated container/Kubernetes acceptance,
rollout, scaling, worker loss, stale ownership, readiness failure, backup/restore
and compatible rollback are recorded. Hosted access and real-provider acceptance
remain unperformed. [Deployment](DEPLOYMENT.md) · [Security](../SECURITY.md).

Completion requires scoped implementation, meaningful validation, pushed commits,
completed CI and review for every phase, with the R01–R14 evidence mapping and
limitations retained. Runtime benchmarks do not prove semantic model quality;
fixture security tests do not certify a public deployment. Notifications,
evaluation caching, advanced judging, billing, arbitrary uploaded code and extra
integrations remain outside the sequence. [Deferred scope](deferred-phases.md).
