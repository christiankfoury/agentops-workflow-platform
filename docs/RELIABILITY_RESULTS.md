# Phase 99 measured reliability results

## Outcome

Three repetitions of all 15 scenarios passed from **2026-09-17 03:51:05 to
03:59:27 UTC**. The command exited 0; none of the 45 cases failed or skipped.
Pytest durations were **164.92, 163.92 and 166.87 seconds**. Full command wall
time was approximately eight minutes 21 seconds, including fixture setup and
evidence serialization.

Independent reconciliation found:

| Observation | Total across three repetitions |
| --- | ---: |
| Accepted workflow identities | 72 |
| Completed workflows | 54 |
| Expected failed source workflows | 9 |
| Expected cancelled workflows | 9 |
| Terminal jobs matched to queued admission events | 279 |
| Retained attempts | 234 |
| Intended / observed sink effects | 12 / 12 |
| Sink requests | 18 |
| Duplicate sink requests suppressed by stable keys | 6 |
| Lost jobs / lost effects / duplicate effects | 0 / 0 / 0 |
| Deliberately unresolved remote outcomes | 3 |

The failed sources cover exhausted worker recovery, non-idempotent unknown
writes, and failed sources retained after operator-reconciled child recovery.
The cancellations are approval/cancel races. These expected outcomes remain in
the denominator; the experiment does not claim a production success rate.

The three unresolved writes each occurred once in the disposable sink, but their
workflow ledger correctly remains `unknown`. They were not retried or relabeled
as successful. Three separate reconciliation cases recorded operator evidence,
required fresh child approval, and completed without another remote request.

## Observed recovery intervals

These are minimum–maximum seconds across three observations, except the approval
race, which has nine observations. The timer boundaries and included controller
work are defined in [the method](RELIABILITY_EXPERIMENTS.md#evidence-and-accounting).

| Scenario | Observations | Recovery interval, seconds |
| --- | ---: | ---: |
| Process killed before execution | 3 | 3.875–4.000 |
| Process killed during execution | 3 | 4.562–4.781 |
| Process killed after checkpoint | 3 | 2.843–2.906 |
| Dead-letter followed by explicit child recovery | 3 | 4.015–4.094 |
| Expired parallel claim, repeated delivery and one join | 3 | 2.688–2.953 |
| Timeout after write, idempotent reconciliation | 3 | 2.672–2.781 |
| Timeout after write, unknown outcome retained | 3 | 2.843–3.047 |
| Unknown outcome explicitly reconciled, fresh approval | 3 | 3.766–3.891 |
| Interruption before effect receipt commit | 3 | 4.546–4.625 |
| Approval/cancel race | 9 | 2.125–2.219 |
| Scheduler replica race | 3 | 2.531–2.594 |
| Overlapping graceful worker replacement | 3 | 13.797–15.375 |
| PostgreSQL service stop, restart and recovery | 3 | 10.969–11.343 |

These small local samples are not latency objectives or percentile estimates.
Worker startup, short fixture leases, snapshot reads and the shared host affect
the measurements. The unknown-outcome timer measures safe terminal accounting,
not resolution of that remote uncertainty.

## Failure analysis

No application runtime defect was found in these tested scenarios. Fencing
discarded stale ownership and repeated completed claims; parallel work joined
once. Concurrent scheduler requests admitted one fire. Every accepted job
remained accounted for after recovery, cancellation or explicit failure.

The timeout evidence distinguishes provider guarantees: idempotent cases made
two requests, retained one effect and ended with adapter reconciliation.
Non-idempotent cases made one request and retained `tool_timeout`/`unknown`
until a separately recorded operator decision. Receipt-commit interruption also
reused its original effect key after ownership recovery.

The database outage made new admission and worker operations fail closed.
After PostgreSQL restart, an explicit worker restart recovered the expired
claimed job. This requires a deployment supervisor; the experiment does not
claim the worker loop remained alive through database loss.

Initial harness development found a nonexistent ORM relationship lookup and a
metadata keyword collision before the outage boundary. A later attempt reached
database restart but failed host readiness with an unspecified Docker host port.
The corrected fixture retains an explicit loopback port across restart. The
isolated outage then passed, followed by all three full repetitions. No
application state transition, schema or retry policy was changed to obtain the
result. Initial attempt logs are identified in [phase progress](phase-progress.md).

The first implementation CI subsequently found a platform-dependent fixture
assumption: Linux restarted PostgreSQL before the half-second lease expired,
so renewal was correctly still allowed. The fixture now waits for the persisted
database lease deadline before checking stale-owner rejection. This changes no
runtime lease rule. A separate [fix-validation run](evidence/phase99-fix/summary.json)
passed **all 15 scenarios in 182.08 seconds**, with 24 accepted runs, 93 terminal
jobs, 78 attempts, all four intended effects, no loss/duplication and one
deliberately unresolved outcome. The original three-repetition measurements above
remain intact; this additional run is not mixed into those timing ranges.

## Evidence and provenance

The [summary manifest](evidence/phase99-full/summary.json) identifies all **45
hashed gzip case archives**, their scenario names and measurements. Each
repetition also contains pytest output and JUnit results. Archives retain the
accepted IDs, fault-boundary snapshots, admission events, terminal history,
approval/recovery records, effect ledger and sink observations.

The measured base commit is **`ee13c8cc0c0ff7201b76623bfdfaa2829edcd2e7`**.
All **220 runtime/migration/lock source hashes and 96 test-source hashes** matched
the measured checkout after the run. The new harness was measured before its
phase commit; the implementation SHA and CI evidence are recorded in phase
progress. Independent offline verification recomputed all totals and checked
the timeout/reconciliation outcomes from the raw records.

The fix rerun used base commit `8d4582845201cb27f01bbffcfbd48a3ea3d7cef0` plus
the fingerprinted lease-wait correction. Its 316 source hashes matched after
measurement. A later descriptive metadata correction replaces a Phase 98
single-process scope label inherited from the shared helper. Both manifests
retain that correction's previous label and reason; their measured source hashes
and raw archives are unchanged. Future runner output uses the correct scope.

The host ran Python 3.12.7 on Windows 11 with 16 logical CPUs. Ordinary cases
used PostgreSQL 16.14 in the existing disposable validation service; each outage
case created a separate PostgreSQL container limited to 512 MiB and two CPUs.
Image identities and database versions are in the raw frames. All owned outage
containers were removed after their tests; the existing preview database and
retained Phase 98 schemas were not outage targets.

Follow [the reproducible commands and limits](RELIABILITY_EXPERIMENTS.md). The
suite uses fixed synthetic data, development identity fixtures and no paid
models. It does not measure OIDC ingress, human response time, operating-system
SIGTERM, container rollouts, hosted infrastructure or arbitrary remote providers.
Those boundaries are not implied by these passing local fault experiments.
