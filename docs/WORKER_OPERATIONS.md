# Worker operations and live updates

Phase 97 adds `/operations`, a metadata-only view of the current organization's
durable work. Open a job's run to inspect its pinned graph, attempts, errors,
approvals, costs and [recovery controls](WORKFLOW_RECOVERY.md).

## Read APIs and access

All routes require current `read` permission and use the verified organization.
There is no HTTP organization override or global-admin flag.

| Route | Result |
| --- | --- |
| `GET /operations` | Consistent database snapshot of counts and queue measurements |
| `GET /operations/jobs?kind=stale&offset=0&limit=25` | Metadata history, maximum 50 rows per page |
| `GET /operations/metrics` | Prometheus text for this organization only |
| `GET /operations/pulse?kind=execution&identity=UUID` | Opaque change token, terminal flag and polling interval |

Job filters: `all`, `queued`, `running`, `retrying`, `failed`, `completed`,
`cancelled`, `dead_letter`, `stale`. Pulse kinds: `execution`, `run`, `approval`,
`executions`, `runs`, `approvals`, `operations`. Singular resources outside the
organization return 404. Responses omit inputs, outputs, claim tokens, worker
hostnames, private conversations and credential material.

## What the numbers mean

- **Jobs** are durable scheduling receipts, not node attempts or workflows.
  A claim can register a wait or finalize a workflow without another node attempt.
- **Retrying** is queued work with a previous lease recovery or a matching
  retrying logical step. It is a subset of queued jobs, not an additional total.
- **Dead-letter** is failed work with `retry_exhausted` or `recovery_exhausted`.
  Other permanent failures remain in the failed filter. Recovery never clears
  these historical records or resets their budgets.
- **Stale leases** are running jobs whose database lease deadline has passed.
  The recovery authority, not this dashboard or the presence registry, decides
  whether a claim can be recovered.
- **Claims** count persisted queued-to-running job events. **Lease recoveries**
  count persisted `lease_expired` requeue events; exhausted recoveries instead
  remain failed/dead-letter. **Abandoned attempts** count retained
  `worker_abandoned` attempts, including exhausted cases.
- **Attempts** are counts of persisted attempt statuses. Reused recovery outputs
  create no fake attempts or duplicated provider cost. **Linked recoveries**
  count explicit immutable recovery receipts.
- **Queue wait** measures claim time minus the job's due time, clamped to zero.
  Samples begin with Phase 97 claim events. Historical claims without this field
  are excluded from wait statistics, but remain in total claims. Retry backoff
  before due time is excluded. Mean is sum divided by samples; zero samples means
  unavailable, not evidence of zero latency.
- **Oldest ready** is the age of the earliest currently due queued job. Future
  backoff, approval waits and delayed steps are excluded.
- **Throughput** is completed workflows in the trailing 900 seconds divided by
  900. It is an observed window, not a benchmark or capacity claim.

Snapshots read at PostgreSQL repeatable-read isolation. Histories and later
snapshots can differ as workers continue. Existing cost/event dashboards retain
their accounting; operational totals do not add generic and legacy projections.

## Worker availability and infrastructure export

Updated workers write presence immediately and every 10 seconds, expiring after
40 seconds. Graceful exit records `stopped`; shutdown may report `draining`.
A late heartbeat cannot resurrect a stopped identity. Records expired for more
than a day are pruned; durable jobs/events are retained. Telemetry write failure
does not grant or revoke job ownership. Job heartbeat and fencing remain the
authority for safe execution.

Tenant worker counts include only unexpired workers associated with that tenant's
retained jobs. No identities, shared capacity or other tenants' workloads are
returned. A fresh tenant or an older worker can have no observed presence. Zero
observed workers does not establish a fleet outage.

Infrastructure operators with database access can export aggregate fleet metrics:

```powershell
uv run --directory apps/api python -m src.operations_metrics
```

The CLI is a separate database administration boundary, not a tenant-admin HTTP
permission. Run it only inside trusted infrastructure. It emits fixed metric
names and allowlisted status labels; no tenant/run/job IDs, node names, hostnames,
payloads or secret-derived labels. No unauthenticated global HTTP endpoint is
installed. Deployment wiring is covered by the container/Kubernetes phases.

Metrics are database-backed observations; retained totals can change after a
database restore. Treat status/window/age measurements as gauges. Scrape at a
bounded interval (15 seconds or longer) and retain the scrape timestamp.

## Live update behavior

Run lists/details, graph debugger, approvals and operations use small metadata
pulses. Active details poll at 5 seconds; waits and aggregate views at 15 seconds.
Only changed tokens refresh the page. The operations token advances every 15
seconds because queue ages and lease expiry change without a workflow event.

One pulse is in flight per page. Failed reads back off through 10, 20, 40 and
60 seconds. Offline/hidden tabs pause reads; reconnect resumes them. Resolved
details stop automatic polling. Current permission and organization are checked
for each pulse; access loss stops automatic reads. `Refresh now` is available
for an explicit retry, including terminal history.

Recovery/cancellation mutations request an immediate refresh, queued behind an
in-flight pulse. Client form state survives page refresh. When the debugger's
run revision changes, visible history reloads and stale expanded payloads clear;
select a record again to inspect the updated detail. No recurring payload download
is performed for closed records. Historical and canonical usage remain separate.

## Incident diagnosis

1. Check **oldest ready**, queued count and stale leases. Future-due jobs may be
   intentionally waiting; inspect the due time before intervening.
2. With stale leases, inspect the affected run and its attempt history. Compare
   abandoned attempts, recovery counts and the pinned retry budget. Use expired
   claim recovery only when current eligibility permits it.
3. If ready work grows with no tenant-observed workers, an infrastructure operator
   should check fleet presence and worker process/database logs. Tenant absence
   alone is insufficient evidence to restart the shared fleet.
4. Inspect waiting steps and approvals before treating an inactive queue as an
   outage. Approval and delay waits release workers by design.
5. For dead-letter or permanent failure, inspect the pinned contract and error in
   the run debugger. Terminal recovery creates a linked run. Unknown remote
   effects require evidence and reconciliation; never infer success from an idle
   queue or issue the action again just to clear an alert.
6. Compare attempt usage in the debugger with cost dashboards. Claims/recoveries
   are operational counts and must not be multiplied by estimated model prices.

## Rollout

Apply `f097_worker_presence` before starting updated API/workers. The migration
adds only an ephemeral presence table and expiry index. Existing workers remain
usable but have no registry evidence; historical queue waits remain unavailable.
Rollback updated API/workers before dropping that table. No durable history or
business schema is removed by the Phase 97 downgrade.
