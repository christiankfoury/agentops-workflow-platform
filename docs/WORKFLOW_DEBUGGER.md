# Workflow run debugger

Open **Graph runs**, or use **Open run debugger** after a manual start. Business
run pages also link to **Open run trace**. All readers enforce the current
organization and read permission; changing organization requires reopening the
trace. The debugger performs no workflow mutation.

## Graph and logical history

The graph comes from the run's immutable version, including when that version is
archived or a later draft is published. Node badges show the latest logical
iteration. Edge colors and the textual connection list describe the current
checkpoint: selected, skipped or pending. They do not reconstruct an earlier
iteration's edge map. The branch/quality checkpoint is available beneath the graph.

Choose a node to inspect its latest step. **Steps** lists every retained logical
step with its UUID, node, branch and iteration. Select an earlier row to inspect
its own input/output and pinned node/runtime configuration. **Attempts for …**
opens attempt history for that exact step UUID. Attempt details include returned
model/prompt metadata, token counts, estimated cost, latency and incomplete usage.
Unknown cost remains unavailable rather than being displayed as zero.

**Events**, **Tools**, and **Approvals** have independent record histories and
detail readers. Tool rows retain step, attempt and call identity, effect status,
latency and errors; details show the redacted request/result/reconciliation.
Approval rows retain revision, expiry, actor and replacement identity; details show
the review and submitted payload. Wait reasons, wake times and retry deadlines are
shown on logical steps. Cancellation/failure information remains readable.

## Bounded access and partial failures

Lists return metadata only, in pages of 25 (API maximum 50). Payloads are fetched
only when explicitly inspected. Run payloads have their own load button. Detail
previews are limited to 64,000 characters, 8,000 visited values and 24 nesting
levels; a visible notice identifies truncation. The compact checkpoint preview is
limited to 2,000 characters. These previews are not full exports.

Readers mask known credential field names and HTTP URL user information. Tool
claim/reservation tokens and credential digests are excluded entirely. Debugger
requests never fetch secret values or private LLM conversation checkpoints.
Redaction cannot recognize arbitrary secrets embedded in prose: workflow authors
must keep credentials in configured references rather than workflow payloads.

A failed section load retains the existing view and provides a retry. Initial
step-history failure leaves the graph/run state usable. Controls suppress duplicate
requests while loading. **Reload section** refreshes that history; reload the page
to refresh graph/run state. Automatic polling and recovery controls are separate
delivery phases.

## Historical compatibility and usage

An older run with only AgentStep history retains its original labels and stored
totals, with no invented graph or attempt identities. A business run backed by the
generic engine links to its canonical execution trace. Generic attempts, usage
events, AgentStep projections and CostEvent projections are never added together.
The generic debugger shows selected-attempt usage; historical run totals and their
step breakdowns are clearly identified as the same source accounting.

## API readers

- `GET /execution-traces` lists generic run metadata.
- `GET /execution-traces/{id}` returns pinned topology and current graph state.
- `GET /execution-traces/{id}/payloads` returns bounded run payload previews.
- `GET /execution-traces/{id}/records/{kind}` pages steps, attempts, events,
  tools or approvals. Attempts require `step_id`; other collections may filter it.
- `GET /execution-traces/{id}/records/{kind}/{record_id}` authorizes the record
  against the run before loading details. Attempt details also require `step_id`.
- `GET /execution-traces/legacy/{id}` resolves historical or canonical source.
- `GET /execution-traces/legacy/{id}/steps[/{record_id}]` reads historical steps.

Pagination uses `offset`, `limit` and `next_offset`; records have stable timestamp
and UUID ordering (attempts use attempt number). These additive readers require no
schema migration and preserve existing workflow and trace API contracts.
