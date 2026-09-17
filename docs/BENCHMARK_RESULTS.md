# Phase 98 measured benchmark results

## Outcome

The full command ran from **2026-09-17 02:05:02 to 03:10:45 UTC** on a shared
local development host. All **10,000 accepted workflows completed**, with
**33,333 completed jobs**, **26,666 completed attempts**, and **3,333 intended
sink effects** observed exactly once by the controlled sink.

There were **zero failed, cancelled or nonterminal runs**, missing jobs, extra
effect identities, unknown effects, worker exceptions or controller errors.
The 1,000 deliberate duplicate start requests returned their original run IDs.
Step retries, lease recoveries, tool retries and duplicate sink requests were all
zero. These are normal-operation observations; fault experiments are Phase 99.

The [offline verifier](../apps/api/src/benchmarks/verify.py) independently checked
every archived accepted ID, start receipt, job, attempt and sink identity. All
220 LF-normalized source fingerprints matched the measured checkout, and the
archived inputs matched each stage's seed and offset.

## Throughput and latency

Capacity is the number of concurrent executor slots in **one worker loop**.
The producer, worker threads, synthetic approver and loopback sink share one
Python process. Each stage uses a fresh migrated schema and batches of 100.

| Capacity | Completed | Measured seconds | Workflows/s | Run queue p95 s | Execution p95 s | End-to-end p95 s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 3334 | 2467.59 | 1.351 | 22.021 | 59.922 | 73.695 |
| 4 | 3333 | 786.14 | 4.240 | 6.330 | 19.129 | 20.898 |
| 16 | 3333 | 588.25 | 5.666 | 1.949 | 13.694 | 14.398 |

Duration includes acceptance, duplicate requests, fixture approval decisions and
worker drain. Setup/migrations and archive serialization are outside these stage
timers. Full command wall time was approximately 65 minutes 43 seconds.
Percentiles use nearest rank; p50/p99/max and all individual claim-wait samples
are retained in the [machine-readable evidence](evidence/phase98-full/summary.json).

Higher concurrency improved throughput on this host, with a smaller gain from
4 to 16 than from 1 to 4. This single sequential experiment does not isolate the
cause or establish a production scaling curve. Shared-host activity, caches,
one producer, immediate synthetic decisions and small inputs constrain the result.

## Resources and environment

| Capacity | Python CPU seconds | Python lifetime peak RSS MiB | Retained schema MiB |
| --- | --- | --- | --- |
| 1 | 912.78 | 118.63 | 53.65 |
| 4 | 710.94 | 151.52 | 53.78 |
| 16 | 665.14 | 156.12 | 54.52 |

RSS is a process-lifetime high-water mark, including earlier stages; it is not a
per-stage memory allocation limit. Schema bytes include indexes. PostgreSQL CPU
and memory are separate from Python observations.

The host reported an AMD Ryzen 7 3700X, 16 logical CPUs and 17,084,694,528 bytes of
physical memory. Python was 3.12.7 on Windows 11. PostgreSQL 16.14 ran in Docker
27.2.0 with an 8,277,651,456-byte VM memory allocation and no additional database
container CPU/memory cap. Existing local preview services remained running.
Database fsync, synchronous commit and full-page writes were enabled.

See the [environment and image identity](evidence/phase98-environment.json) and
[124 periodic database resource samples](evidence/phase98-resources.jsonl).
Those samples cover the full command, including setup, and retain Docker's
reported CPU, memory and cumulative I/O values.

## Workload, provenance and limits

The workload contains 3,334 condition workflows, 3,333 parallel joins and 3,333
approved HTTP actions. Maximum serialized workflow input was **130 bytes**.
Each isolated schema uses one synthetic organization and a persisted administrator
membership. Approval and execution use normal service-level permission checks.

The measured base commit was
`d2b46667fd1476008697e55d698c0da38bbdd32e`. The runtime and new benchmark sources
are individually fingerprinted in the summary; the phase implementation commit
is recorded in [phase progress](phase-progress.md). This identifies code measured
before its phase commit without claiming that the base commit already contained
the new harness.

No paid models, arbitrary remote effects, HTTP/OIDC workflow ingress, browser
load or human response time were measured. No hosted deployment or third-party
exactly-once guarantee follows from this controlled sink result.

## Reproduce and inspect

Follow [BENCHMARK.md](BENCHMARK.md). The [generated report](evidence/phase98-full/REPORT.md)
and [summary manifest](evidence/phase98-full/summary.json) accompany 30 hashed gzip
JSONL archives. The three schemas are retained for direct inspection; their names
are in the manifest. The small 12-run CI sample and corruption tests passed
locally; delivery CI and phase review are recorded separately in the tracker.
