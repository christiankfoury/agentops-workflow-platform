# Deterministic throughput benchmark

Started: 2026-09-17T02:05:02.561630+00:00. Base commit: `d2b46667fd1476008697e55d698c0da38bbdd32e`.
Exact measured Python/migration/lock sources are fingerprinted in `summary.json`.

| Capacity | Accepted | Completed | Failed | Seconds | Completed/s | Reconciled |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 3334 | 3334 | 0 | 2467.59 | 1.351 | True |
| 4 | 3333 | 3333 | 0 | 786.14 | 4.240 | True |
| 16 | 3333 | 3333 | 0 | 588.25 | 5.666 | True |

## Scope and limits

Fixed-seed condition, parallel-join and approved loopback HTTP workflows. Fresh migrated schema per stage; bounded batches, one producer and one real worker process with the listed thread capacity. No paid models or remote effects.

Service-level membership/permission checks and durable approval decisions are exercised. HTTP/OIDC ingress and human response time are excluded. Throughput includes acceptance, duplicate requests, fixture approvals and drain; migration/setup and evidence serialization are excluded. These are local observations, not production targets or 10,000 simultaneous calls.

Latency percentiles use nearest rank. Execution latency includes waits after first start; end-to-end also includes initial queue time. Job queue samples come from persisted claim events. RSS is the Python process lifetime high-water mark; CPU includes its controller, workers and sink, not PostgreSQL. Database relation bytes include indexes. Shared-host/cache effects and stage order remain limits.

All expected failures are zero; unsuccessful or incomplete runs remain in raw evidence and fail reconciliation. Gzipped JSONL archives retain accepted IDs, runs, jobs, steps, attempts, effects, sink observations and queue samples; each archive hash/count is in the summary. No arbitrary third-party exactly-once guarantee is implied.
