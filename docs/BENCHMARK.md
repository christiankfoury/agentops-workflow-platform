# Deterministic throughput benchmark

Phase 98 measures the durable engine with real PostgreSQL transactions and real
workers. It uses fixed-seed condition branches, parallel joins, and exact-payload
approval gates before an idempotent loopback HTTP sink. No LLM, paid provider,
real business data, or remote effect is used.

The completed 10,000-workflow run is documented in
[the measured results](BENCHMARK_RESULTS.md), with raw archives and environment
evidence. It is a local observation, not a production capacity guarantee.

## Run

Use an authorized disposable PostgreSQL database with schema-creation rights.
Set `WORKFLOW_TEST_DATABASE_URL` in the shell; the CLI deliberately does not fall
back to the application database. From the repository root:

```powershell
uv sync --directory apps/api --locked --dev
uv run --directory apps/api python -m src.benchmark --count 12 --capacities 1 4 --batch-size 6 --output ../../benchmark-small
uv run --directory apps/api python -m src.benchmark --count 10000 --capacities 1 4 16 --batch-size 100 --seed 20260916 --output ../../docs/evidence/phase98-full
uv run --directory apps/api python -m src.benchmarks.verify ../../docs/evidence/phase98-full
```

The output directory must not exist. Each stage creates a uniquely named
`benchmark98_<uuid>` schema, applies all migrations, creates a synthetic user and
admin membership, and publishes three graph versions. It never drops schemas or
alters application tables. Retained schema names are printed and recorded.
Run the CLI as its own process: its fixture settings are process-local and must
not be imported into a running API server.

The default 10,000 requests are split 3,334 / 3,333 / 3,333 across increasing worker
capacities. One producer accepts bounded batches; one worker with the listed
thread capacity executes them. Every tenth input repeats its exact start request.
A fixture controller decides persisted approvals through the normal permission
and payload-hash checks. The sink binds only to loopback, accepts bounded POST
bodies, retains one effect per idempotency key and rejects conflicting payloads.

## Evidence and interpretation

`summary.json` records the base Git commit, LF-normalized SHA-256 fingerprints of
the measured API Python sources/migrations/lockfile, platform, PostgreSQL version,
seed, workload counts, concurrency, duration, input bounds and resources. Source
fingerprints identify uncommitted benchmark code measured before its phase commit.
The phase delivery record identifies the final implementation commit.

Each stage writes hashed, counted gzip JSONL archives of accepted IDs, start
receipts, runs, jobs, steps, attempts, effect ledger entries, sink calls/effects,
and persisted claim-wait samples. `REPORT.md` summarizes the measured results.
The offline verifier checks archive integrity and independently repeats identity,
state, expected job/attempt, branch/join output and sink reconciliation. Missing
runs/jobs/effects, extra effect identities, changed versions/inputs, unknown
outcomes or incomplete drain fail validation. Expected failures are **zero**;
failure evidence is retained and the CLI exits nonzero.

Throughput includes service acceptance, duplicate requests, fixture decisions and
worker drain. Migration/setup and evidence serialization are excluded. Latencies
use nearest-rank p50/p95/p99/max: initial run queue, execution after first start,
end-to-end, and each persisted job claim. Completed count is the throughput
numerator; failed/cancelled/nonterminal states remain visible. Retry counters
separate additional step attempts, lease recoveries, and tool retries.

CPU time and lifetime peak RSS cover the Python process (producer, worker threads,
approver and sink). Schema bytes include PostgreSQL indexes; PostgreSQL CPU and
memory are separate from Python measurements. Capture host/container limits with
the full result. Fresh schemas limit history-growth bias, but shared-host load,
caches and sequential stage order still affect comparisons. A single run is an
observation, not a statistically established scaling curve.

The workload exercises service-level current membership checks. It does not
measure HTTP/OIDC ingress, browser traffic, human decision latency, paid models,
arbitrary external services, or 10,000 simultaneous calls. Controlled sink
reconciliation does not establish exactly-once behavior for third-party APIs.

## Automated validation

```powershell
uv run --directory apps/api pytest tests/test_benchmark.py
uv run --directory apps/api ruff check src tests
```

The CI sample runs 12 workflows at capacities 1 and 4 against freshly migrated
schemas, verifies all four sink effects, checks duplicate starts, then corrupts
evidence to prove missing records, duplicate effects and altered archives fail.
Only that test's reported uniquely owned schemas are removed by its cleanup.
The full 10,000-run result is required separately; the small test is not a
substitute for it.
