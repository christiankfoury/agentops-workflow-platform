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
same evaluation foreign keys, deterministic scoring and comparison links. Migrating
the shared evaluation/demo orchestration to generic execution completes in Phase 85;
its current legacy counterpart runner is not a second execution path for an already
linked run.

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
