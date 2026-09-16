# Published business templates

## Sales rollout (Phase 83)

Apply `alembic upgrade head` and deploy the updated API and durable workers
together. As an organization administrator, call
`POST /workflow-definitions/templates/sales/install`. This installs two published,
tenant-owned definitions. Repeated installation preserves existing published
versions and administrator edits. Missing default prompts are installed as inactive
template prompts; existing selected analyst/reviewer/writer prompts are reused.
Installation does not execute a provider request.

New sales requests to `POST /workflow-runs` require an uploaded sales input and
enqueue durable work. The response retains the legacy run ID and adds
`execution_id`. Missing installation returns a clear 409; there is no silent
fallback. The normal worker drains the jobs, releases its slot during approval,
and resumes after an authorized decision.

- Multi-agent: analyst → reviewer → mandatory human approval → writer.
- Quality: repeat analyst/reviewer at most twice when review recommends a retry,
  the score is below the pinned human threshold, or a high/critical issue exists.
  Exhaustion still requires human approval; manual retries share the published
  revision bound. Infrastructure attempts use their separate bounded retry policy.
- Baseline: one LLM step with the existing sales baseline system prompt.
- Existing analysis and review schemas are reused. The graph stores their closed
  type subset; semantic reviewer validation enforces score/severity constraints.
  Writer/baseline return a structured `final_output` string; a registered validator
  trims it and rejects blank output through bounded repair.
- Model, prompt and settings snapshots remain fixed for accepted runs. The graph
  owns revision and infrastructure attempt limits; changing a legacy SDK retry
  setting does not change those graph limits.

## Customer feedback rollout (Phase 84)

As an organization administrator, call
`POST /workflow-definitions/templates/customer-feedback/install`. New feedback
starts require an uploaded feedback input and use the durable runtime. CSV upload
normalization is unchanged; the graph receives the stored normalized text and notes.
Selected classifier, insight, reviewer and writer prompts are pinned on publication.
Task guidance and supporting-example structures are preserved in the graph.

- Multi-agent: classifier → insight → reviewer → mandatory human approval → writer.
- Baseline: one LLM step with the existing feedback baseline system prompt.
- Revisions repeat classifier, insight and reviewer together, up to two times.
  Every insight consumes its own iteration's classification. Reviewer feedback,
  human feedback and edited payloads remain in revision context. Exhausted revisions
  still require human review. The former feedback path always stopped for a human;
  the published template adds the bounded automatic quality loop required by the plan.
- Registered semantic validators reuse the existing classification, insight and
  review models. They retain count, category, severity and example constraints
  beyond the graph's type subset. Invalid generated output uses bounded repair;
  invalid human edits return 422 without superseding the pending approval.
- The writer consumes the approved insight payload, including human edits.
  Feedback uses the same compatibility projections and control protections as sales.

Set `FEEDBACK_TEMPLATE_ENABLED=false` to select legacy starts for future feedback
runs. Already accepted durable runs retain their owner and continue on workers.
No database migration is required for Phase 84. Fixture validation compares legacy
and durable outputs, approval decisions and observed usage; it does not claim
live-provider equality.

## Incident and evaluation rollout (Phase 85)

Apply `alembic upgrade head`, deploy the API and workers together, then call
`POST /workflow-definitions/templates/incident/install` as an administrator.
New incident starts use the published timeline → root cause → reviewer → mandatory
approval → writer graph, or the one-step baseline. Revisions repeat timeline,
root cause and review together, at most twice. Writers consume the approved root
cause, including human edits, and the current timeline. Existing timestamp parsing,
ambiguous lines, and confirmed/inferred/unknown distinctions remain intact.
Registered semantic models validate generated outputs and human edits.

Set `INCIDENT_TEMPLATE_ENABLED=false` to back out future incident starts. Accepted
durable executions keep their owner, pinned graph and worker control. All eight
legacy `run-*` agent endpoints are marked deprecated in OpenAPI; they remain
available for unlinked historical runs and return 409 for durable-owned runs.

Evaluations now enqueue these published templates and score their committed
compatibility projections. See [evaluation](EVALUATION.md) for pending results,
automatic approval authorization and worker requirements. Demo seeding installs
templates for new runs while preserving synthetic historical fixtures without
invented execution versions. Reseeding never overwrites durable-owned run history.

## Compatibility and control ownership

The existing immutable `legacy_run_id` link has a unique constraint: a business
run has at most one durable owner. Old agent endpoints reject linked runs with
409, including after backout or completion. Cancellation delegates to durable
cancellation. There is no business-type branch in the generic interpreter.

The durable transaction updates legacy run, agent-step, approval, event and cost
read projections atomically. Stable step/event/attempt IDs make repeated projection
updates idempotent. One cost row represents one returned attempt's aggregate usage,
including schema repair and failed attempts. These rows are the compatibility
representation of the same usage, not additional provider calls. Unknown pricing
remains null in run/step totals and produces no fabricated cost row. Abrupt worker
death can still leave remote usage unknown, as described in [LLM execution](LLM_EXECUTION.md).

Approval actions require the displayed `expected_payload_hash`. Editing returns
the replacement approval ID; the Web form redirects there. Superseded, invalidated,
expired and cancelled approvals retain those statuses. A stale ID cannot approve
the replacement. Writer input uses the approved payload and preserves human feedback.

Historical runs have no invented version or execution link. Their existing APIs,
steps, comparisons and evaluations remain readable. New projections retain the
same evaluation foreign keys, deterministic scoring and comparison links. Queued
counterpart and corrected runs return their progress links until results complete.
The backout runner can create unlinked runs only; it cannot take control of an
already linked run.

## Backout

Set `SALES_TEMPLATE_ENABLED=false` on the API to create future sales runs through
the retained legacy start path. Keep workers running for already accepted durable
runs; their owner and versions never switch. Keep the additive schema and approval
enum values. Migration downgrade refuses while linked executions exist. There is
no historical backfill or data deletion. To change future template behavior,
edit/publish the installed definition through the normal authorized version APIs.

## Validation boundary

Phase 83 tests use disposable PostgreSQL and provider fixtures. They cover the
approval/edit/reject/retry/cancel paths, one-step baseline, blank report repair,
returned usage, repeated projection updates, same-input evaluation links, API
duplicate-control prevention and the legacy backout path. They do not establish
live-provider output equality or a hosted rollout. Delivery evidence is recorded
in [phase progress](phase-progress.md).
