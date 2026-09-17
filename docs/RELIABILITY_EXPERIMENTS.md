# Crash and concurrency reliability experiments

Phase 99 tests fault recovery against real PostgreSQL, independent worker
processes and a controlled loopback HTTP sink. These experiments complement
the [10,000-workflow throughput run](BENCHMARK_RESULTS.md); they do not establish
arbitrary third-party exactly-once execution or hosted production reliability.

## Reproduce

Use the locked API development dependencies, Docker with `postgres:16-alpine`
available, and an explicitly authorized disposable PostgreSQL database. The
ordinary cases create and remove unique test schemas in that database. The
outage case creates a **separate** container with a random name, ownership label,
loopback port, 512 MiB memory limit and two-CPU limit. It validates its name and
label before stopping, restarting or removing that same container and volume.

From the repository root in PowerShell:

```powershell
$env:WORKFLOW_TEST_DATABASE_URL = '<disposable PostgreSQL connection URL>'
uv run --directory apps/api pytest tests/test_reliability_experiments.py -q
uv run --directory apps/api python -m tests.reliability_experiment run --repeat 3 --output ../../docs/evidence/phase99-full
uv run --directory apps/api python -m tests.reliability_experiment verify ../../docs/evidence/phase99-full
```

The output directory must not already exist. Choose a new name for another run.
The full runner fails if a scenario fails, skips, produces no evidence, loses an
accepted identity or disagrees with independent reconciliation. Failed/partial
records and pytest logs are retained. The offline verifier needs no database,
Docker daemon or credentials; it verifies archive hashes and recomputes counts.

## Scenarios and boundaries

| Scenario | Injection and expected outcome |
| --- | --- |
| Worker death, before execution | Kill the owned subprocess after claim; expire its lease, rotate ownership and complete the accepted run. |
| Worker death, during execution | Kill after attempt persistence inside a held deterministic handler; retain the abandoned attempt and recover within the pinned budget. |
| Worker death, after checkpoint | Kill after a committed checkpoint; retain completion and execute the remaining queued work. |
| Dead-letter and explicit recovery | Exhaust the original attempt budget after process death; retain the failed source and create a separately admitted recovery child. |
| Expired parallel claim and duplicate delivery | Two reclaimers compete for one expired branch; reject the stale owner and a repeated completed claim; join once. |
| Timeout after effect, idempotent provider | The sink records a write, then delays its first response beyond the 0.2-second contract timeout; replay the stable key and reconcile one effect. |
| Timeout after effect, no provider guarantee | Preserve a failed run and `unknown` effect; block recovery and send no second request. |
| Explicit unknown-outcome reconciliation | Verify the disposable sink receipt, record operator evidence, create a linked child and require fresh approval; do not dispatch again. |
| Receipt-commit interruption | Inject `SystemExit` after the HTTP effect but before ledger completion; recover the expired claim and reconcile by stable key. This is an injected boundary, separately labeled from actual process kills. |
| Approval/cancel race, three instances | Race independent decision and cancellation sessions; cancellation remains terminal and downstream work does not run. |
| Scheduler replicas | Race three schedulers at one explicit due instant and replay that instant; admit one fire, run and job. |
| Overlapping graceful replacement | Start a second independent worker while the first owns a held checkpoint; request the first worker's stop event, release/drain it, and complete eight accepted runs without lease recovery. |
| PostgreSQL service outage | Stop the owned database container with an accepted claimed job; reject an unavailable admission and worker operation, restart the database, fence the expired owner and complete the accepted run. |

All 15 cases use fixed synthetic graph/input data. Race winners depend on the
operating-system scheduler; the permitted terminal invariants are fixed. There
are no LLM calls or effects outside the local test sink.

## Evidence and accounting

Each case admits expected workflow IDs explicitly before its fault. Snapshots
retain starts, runs, jobs, steps, attempts, execution events, approval history,
recovery links, scheduler fires and effect reconciliation metadata. The final
record also contains sink calls/effect identities and expected terminal states.

The verifier checks:

- Every explicitly accepted ID exists in terminal history and has a start or
  recovery receipt; expected failures and cancellations remain in totals.
- Every persisted queued-job admission event matches exactly one terminal job;
  every job seen in earlier snapshots remains present, with no orphan owner.
- Attempts retain valid step owners and terminal states.
- Intended effect owners, request bodies, confirmed receipts and observed sink
  bodies agree. For an idempotent sink, observed keys exactly match ledger keys.
- Non-idempotent outcomes have the explicitly expected unresolved count. A sink
  observation alone does not silently change an `unknown` ledger outcome.
- Repetitions contain the same scenario set and no reused accepted IDs.

`recovery_seconds` measures each documented fault/race boundary through terminal
recovery, before final evidence serialization. It includes controller activity,
some intermediate snapshots, lease expiry and, for the outage, stop/start and
readiness time. It is an experiment observation, not an SLA. Raw frame timestamps
allow inspection of intermediate windows. Duplicate-prevention metrics count
actual rejected repeated deliveries, competing claims/fires or sink requests.

## Environment and limits

The summary records the base commit and LF-normalized runtime, migration, lock
and test-source hashes. Each gzip JSON case has a SHA-256 in the manifest; pytest
logs and JUnit results accompany each repetition. Database version and the
outage container image identity are retained in case snapshots.

These cases use current SQLAlchemy metadata in isolated disposable schemas;
fresh migration compatibility is validated separately by normal CI. Service
calls use the explicitly configured local development identity fixture. This
suite measures lifecycle/recovery behavior, not OIDC ingress or tenant-security
coverage; existing identity and permission regressions remain in CI.

Graceful replacement uses stdin to set the same worker stop event that the CLI
signal handler sets. It runs on Windows and Linux, but does not itself test
operating-system SIGTERM or a container/Kubernetes rollout. Those deployment
checks belong to Phases 100–102. The database case validates fail-closed behavior
and explicit worker restart after dependency recovery; it does not claim the
worker loop stays alive during database loss. A deployment supervisor is needed.

The non-idempotent sink uses a request-local observation identity, so its verified
single write is evidence for this controlled fixture only. Production operators
must obtain real provider evidence before recording a reconciliation decision.

See [the measured results and failure analysis](RELIABILITY_RESULTS.md) for the
three completed repetitions and their raw evidence.
