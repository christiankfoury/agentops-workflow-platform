# Workflow recovery controls

Open a generic run debugger and choose **Load control eligibility**. The control
panel fetches current state, permissions, queued/running jobs and unresolved
effects. Mutations recheck authorization and persisted state. A failed control
request leaves the existing trace and entered reason available. Reload eligibility
before retrying an uncertain response; reload the page for updated trace history.

## Cancellation and active jobs

An operator or administrator can cancel a nonterminal execution with a reason.
Cancellation retains completed outputs, fences late results and stops runnable
jobs through the existing cancellation authority. It cannot undo an external
action that already happened. Inspect uncertain effects before recovery.

**Recover expired job** invokes the same lease recovery used by workers. A live
claim cannot be taken over. The existing recovery count, node attempt budget,
backoff and overall deadline remain authoritative. Exhaustion finalizes failure;
it does not grant another attempt. Queued retries retain their scheduled due time.
The control panel shows up to 50 active jobs; detailed job history remains available
through the execution jobs API. Operations views are delivered in Phase 97.

## Terminal recovery

**Create linked recovery** requires both `workflow.control` and `workflow.start`.
Only failed or cancelled runs qualify. A source has at most one recovery child:
double clicks, response retries and concurrent operators return the same child.
If that child later fails, recover the child to extend the recorded lineage.
Lineages are bounded to 100 executions. Completed runs cannot be recovered.

The child pins the original immutable version, input and runtime settings, with
a new overall time window and the current authorized operator as its starter.
Archived versions or unavailable pinned tool policies block a new recovery.
The request accepts only a reason; changed input requires a separate new start.

Completed/skipped checkpoints before approval-dependent work are reused, including
their branch and quality iteration. Their new logical steps point to the original
step through `recovered_from_id`; no provider attempt or usage charge is fabricated.
Quality counters remain bounded. Approval decisions are never copied: each gate
and dependent computation is reconsidered, including when the old approval expired.
An approval edit that changes an existing logical tool action cannot silently turn
recovery into a different effect. Start a new run with fresh approval for that change.

Tools preserve the original logical effect key through step provenance. Confirmed
success is read from its retained ledger row. An LLM write's fresh approval UUID
does not create a duplicate logical action for the same tool contract/arguments.
Private LLM continuations retain messages, call identities, provider rounds, spent
cost and unknown reservations. Only their explicit recovery time window renews;
exhausted round/cost/effect budgets cannot be reset by recovery. Usage in the new
trace includes only its new attempts. Follow **Original recovery source** to inspect
earlier attempts and the original effect records.

## Uncertain effects and dead letters

An unknown outcome, including an abandoned dispatched write, blocks terminal
recovery even if an adapter normally supports automatic reconciliation. An
administrator must verify the remote state and record the outcome through the
effect-resolution control. The form requires evidence and, for success, a JSON
result matching the pinned tool output contract. Recording reconciliation never
sends the remote action again. Concurrent resolutions cannot overwrite an outcome.

A confirmed successful resolution permits eligible recovery using the original
effect. A confirmed failure is retained as final; use a new start and fresh approval
for another action. An exhausted effect policy likewise blocks recovery rather than
creating a fresh key. Failed executions/jobs remain the durable dead-letter history;
their recovery link is the explicit disposition. The UI states the blocking reason.

## API and rollout

- `GET /workflow-executions/{id}/controls`: current eligibility and reasons.
- `POST /workflow-executions/{id}/cancel`: existing cancellation API.
- `POST /workflow-executions/{id}/recover`, body `{ "reason": "…" }`: linked run.
- `POST /workflow-executions/{id}/jobs/{job_id}/retry`: expired-claim recovery.
- `POST /tools/executions/{effect_id}/resolve`: existing administrator resolution.

Audit actions include `workflow.cancel`, `workflow.recover`, `workflow.retry_claim`
and `tool.resolve`. The new receipt records source, child, actor, reason and time;
database/ORM guards retain it and logical-step provenance. Original terminal runs,
steps, attempts and their statuses remain unchanged.

Apply `alembic upgrade head` before updated API/workers. Migration
`f096_execution_recovery` adds the tenant-scoped receipt table and nullable step
provenance with tenant foreign keys. Existing data needs no invented backfill.
An empty migration can be reversed; once receipts exist, downgrade is refused to
retain history. Roll application code back without deleting the additive schema.
Legacy AgentStep-only runs keep their historical reader; these controls apply to
generic executions, including the canonical execution behind a business run.
