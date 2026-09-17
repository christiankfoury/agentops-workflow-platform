# Kubernetes operations results

## Result and scope

The complete local operations suite passed on **2026-09-17, 08:30:38–08:36:58
UTC**. All **21 accepted workflows completed**, with **21 distinct external
effects from 23 requests**, zero lost accepted runs and zero duplicate effects.
These are authenticated, deployed checks against the owned single-node kind
cluster and a controlled persistent HTTP sink. They are not hosted availability
or arbitrary-provider exactly-once guarantees.

Reproduce with the [operations runbook](KUBERNETES_OPERATIONS.md), following
[deployment](KUBERNETES.md) and its [acceptance results](KUBERNETES_RESULTS.md).
The [manifest](evidence/phase102-final/summary.json),
[raw observations](evidence/phase102-final/operations-evidence.json.gz),
[independent review](evidence/phase102-final/independent-review.json),
[worker metrics](evidence/phase102-final/worker-metrics.txt) and
[validation logs](evidence/phase102-final/validation-logs.json.gz) retain the IDs,
source hashes, commands/output, histories, resource snapshots and reconciliation.

## Environment and release identity

- Base commit: `ca281b73363d3c7b8dc6624aa0731c2beba8d21a`, plus the 25 normalized
  source hashes in the manifest. These identify the tested working tree before
  its implementation commit; they do not imply an unbuilt future commit image.
- Cluster: `agentops-phase101`, kind v0.33.0, Kubernetes v1.37.0,
  containerd 2.3.4; PostgreSQL 16.15. Exact node/image metadata is in the archive.
- API/worker baseline `agentops-api:kubernetes` image ID:
  `sha256:1306439e72f32309a5e9fb087764cab5ca375384a8726ed7451e0e5b179d2f52`.
- Release `agentops-api:phase102-release` image ID:
  `sha256:c340a6e58971474374517efdb49f6ff2cc6fabe91e074b7684e629cf325cbbfe`.
- Sink `agentops-operations-sink:phase102` image ID:
  `sha256:9a7cfb8b17efde4b87850ceb5a16c51a8e0a584add1dc60888c0bfef57366607`.

The release changes **packaging metadata only**. Application code and schema
`f097_worker_presence` are unchanged. Rollback verifies the compatible image
procedure, not a schema downgrade or a functional application upgrade. Web,
gateway, identity fixture and ingress retain their Phase 101 versions.

## Observed experiments

| Experiment | Evidence and outcome |
| --- | --- |
| Baseline | One approved HTTP write completed; duplicate start returned the same run ID. |
| Rolling API/worker update | Six active workflows reconciled; both Deployment snapshots show the release image. All 19 sampled API/web HTTP pairs were 200/200. Sampling is not continuous availability measurement. |
| Worker scaling | Three live registered workers and three Pod snapshots; nine workflows completed, then replicas returned to one. No throughput claim is derived from this batch. |
| Active Pod loss | Owner removed after the external receipt committed; natural lease recovery completed the run and reused the same effect key. |
| Stale owner | Paused owner outlived its lease; replacement completed recovery. Resumed owner logged `late result discarded`; the full completed-history hash stayed unchanged. |
| Database readiness | Two accepted approval waits retained. With PostgreSQL stopped, API and web each returned health 200 / readiness 503 inside their Pods. Both workflows completed after recovery. Worker process exceptions/restarts during the outage are retained in Pod state. |
| Backup/restore | Quiescent custom-format backup restored into a new database; all 11 selected history/definition/tool tables matched exact row content and schema revision. |
| Sink persistence | Replaced sink Pod had a different UID and identical persisted receipt/call history on its retained PVC. |
| Compatible rollback | API/worker returned to the baseline image, were ready, and completed one further approved write. |

Every suite run's version, approved payload, completed jobs, effect result and sink
receipt were reconciled. The two recovery cases generated one extra request each;
the sink's durable idempotency contract collapsed each to its original effect.

## Backup and retained history

Backup SHA-256:
`06a25f48f47830ed612bd7fa5a277622b3eaf9eb2712015cd71dbbec08d3c470`,
**376,051 bytes**. The ignored binary archive remains at
`.local/kubernetes/phase102_a95839289259.dump`; the fresh restored database is
`restore_phase102_a95839289259`. Neither the original database nor its PVC was
overwritten. An independent read rechecked all 11 restored table hashes.

The snapshot includes 59 runs, 59 approvals, 118 steps, 123 attempts, 177 jobs and
58 effect records. The final rollback adds one run/approval/effect, two steps and
attempts, and three jobs. Final live totals include prior attempts and Phase 101:
**60 completed runs, 180 completed jobs, 120 completed attempts and five failed
abandoned attempts**. Metrics report five lease recoveries, no stale/dead-letter
jobs, no waiting steps and one running worker.

## Failed harness attempts retained

Two earlier attempts failed their harness gates and remain marked `passed: false`:

1. [First attempt](evidence/phase102/summary.json): the assertion omitted the
   valid successful `reconciled` effect status. Corrected the assertion to require
   a successful reconciliation and matching result, output and receipt.
   [Post-failure check](evidence/phase102/post-failure-reconciliation.json):
   17 accepted/completed runs, 17 effects, 18 requests, no unresolved work.
2. [Second attempt](evidence/phase102-recheck/summary.json): all operations cases
   completed, but the final pass outlived the synthetic five-minute identity
   session. Added normal fixture sign-in renewal between batches/reconciliations,
   preserving production expiry rules.
   [Post-failure check](evidence/phase102-recheck/post-failure-reconciliation.json):
   21 accepted/completed runs, 21 effects, 23 requests, no unresolved work.

The final independent review rebuilt both earlier history hashes from the final
database export and matched them exactly. Across all three attempts, **59 tool
workflows completed with 59 effects from 64 requests**. Failed harness outcomes
were preserved rather than relabeled as passed. Two focused sink tests passed;
Ruff passed across API code/tests and deployment scripts. GitHub CI and pushed
review details are recorded in the [phase ledger](phase-progress.md).

## Limits

The fixture provides durable idempotency and synthetic OIDC/TLS; no paid provider
was called. No hosted target, multi-node failure, managed-database failover,
internet security assessment, cluster-role/Secret recovery or destructive schema
rollback was performed. The binary backup contains the database, not external
provider data or the sink PVC. The separate sink persistence check covers that
fixture's receipts. Resources and all datasets remain available for inspection.
