# Durable checkpoint queue

Phases 75–76 introduce PostgreSQL jobs, the local worker and lease recovery. Generic start requests
return HTTP 202 with ID/version/status after committing the execution, immutable
start receipt, initial job and audit/events together. Identical retries return
the accepted execution and do not enqueue another job. Executors never run in
the request handler.

## Queue transactions

Each `durable_jobs` row identifies an execution checkpoint by a unique sequence.
One queued/running job per execution is allowed at this stage. A checkpoint runs
one ready node or finalizes graph output; its persisted graph edges determine
the next ready node. Conditions retain skipped branches in execution history.

The queue authority claims due jobs using `FOR UPDATE SKIP LOCKED` within a short
transaction. Claims get a random token and worker ID. This trusted infrastructure
scan and the expired-job candidate scan are trusted infrastructure operations;
each worker opens a fresh
session bound to the claimed organization before reading execution data.

Dispatch locks the claimed job, records its one-time dispatch marker and prepares
the attempt in one commit. The interpreter releases database locks for execution.
Completion verifies organization, live job lease/token, attempt identity and run revision,
then commits attempt/step results, job completion and the next queued checkpoint
together. Final graph output and its final job completion also share a transaction.
Duplicate dispatches cannot execute or schedule the same checkpoint twice.

`GET /workflow-executions/{id}/jobs` exposes paginated queued/running/completed/
failed job history to authorized readers. It includes attempt linkage, worker,
timestamps and typed errors; claim tokens remain internal. Foreign executions
return 404. Job identity and terminal history are retained; downgrade refuses
to discard any jobs. The migration enqueues existing pending/running executions
that have no active logical steps, with a migration-origin creation event.

## Local worker

After applying migrations:

```powershell
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m src.worker
```

`WORKER_CONCURRENCY` defaults to 4 (1–32). `WORKER_POLL_SECONDS` defaults to 1.
Workers claim only their free execution slots. SIGINT/SIGTERM stop new claims
and drain current work. `--max-jobs N` exits after N dispatched checkpoints;
`--drain` exits when no queued work or active local work remains. These options
support repeatable local tests. A normal worker continues polling an empty queue.

The development Compose `worker` service uses the API image and database,
starts after API health/migrations, and has a 30-second graceful stop interval.
It exposes no public port. Production packaging follows in Phase 100.

## Current boundaries and evidence

Unexpected worker exceptions are logged by class without copying sensitive
exception text. Expired interrupted claims are recovered as described below.
Phase 77 adds [engine retries, backoff and deadlines](RETRIES_AND_DEADLINES.md).
Phases 78–81 add cancellation, durable waits and parallel execution. LLM calls
and external side effects arrive in later phases.

The PostgreSQL tests in `tests/test_durable_queue.py` cover atomic acceptance,
concurrent bounded claims, duplicate deliveries during and after execution,
completion/enqueue rollback, worker-process restart with queued checkpoints,
graceful draining, tenant reads, migration backfill and history retention.
These deterministic fixtures do not constitute hosted/provider deployment evidence.

## Leases, fencing and recovery (Phase 76)

Jobs persist their worker/token, heartbeat, lease expiry, dispatched attempt and
recovery count. `WORKER_LEASE_SECONDS` defaults to 30;
`WORKER_HEARTBEAT_SECONDS` defaults to 10 and must be shorter than the lease.
A heartbeat thread renews the job during executor work without changing the run's
business-state revision. Renewals require the same unexpired token and cannot
resurrect expired ownership. The database clock determines lease validity.

Dispatch, completion and recovery acquire execution locks before job locks.
Completion requires a live token and the prepared run revision. Losing ownership
rolls back outputs, events and downstream scheduling. Recovery increments the run
revision and returns the same checkpoint job to queued; its next claim receives
a new random token. Competing reclaimers cannot both recover the same claim.
Completed graph checkpoints remain complete and are not executed again.

Expired active attempts finish as failed with `worker_abandoned`, preserving
their input and logical idempotency key. A logical step resumes only within its
pinned `retry.max_attempts` budget and, from Phase 77, its durable backoff.
The default is **one attempt**, so an abandoned
in-flight attempt fails explicitly unless the definition allows more attempts.
`WORKER_MAX_RECOVERIES` defaults to 3 (0–10) and also bounds repeated crashes before
attempt preparation. Exhaustion fails the execution/job with `recovery_exhausted`;
it never silently erases an attempt or loops indefinitely.

Handler invocation is **at least once** when recovery permits another attempt.
Completion and downstream scheduling remain unique in PostgreSQL; this does not
guarantee exactly-once remote effects. Tool/effect reconciliation follows later.

Stop old worker binaries before applying `f076_worker_leases`, then restart the
new workers. The migration gives existing running jobs an expired lease, allowing
bounded recovery. Do not run mixed worker versions. Downgrade refuses to discard
job lease history when jobs exist; use a forward migration for retained data.

`tests/test_worker_leases.py` covers competing reclaimers, live heartbeat renewal,
expired renewal/result rejection, a delayed old result after reassignment,
abandoned-attempt and pre-attempt exhaustion, and real process kills before,
during and after a checkpoint. Tests also execute migrated old running jobs through
recovery. They use deterministic local handlers, not providers or a hosted cluster.

## Parallel regions and joins (Phase 81)

Forks start up to eight named branches. Nested regions preserve paths such as
`main/fork:left/inner:review` on steps and jobs; paths longer than 256 characters
are rejected when validating the graph. Worker concurrency still bounds active
executor slots. Waiting branches release their slot and keep a durable wait.
The execution remains running while any sibling has runnable work, and becomes
waiting when only waits remain.

Parallel jobs target one node and iteration. Result commits acquire the current
execution lock, then verify the job token and dispatched attempt. A sibling's
newer run revision does not invalidate another live branch. Linear jobs retain
the original revision fence. Recovery targets only the abandoned job's node and
iteration, preserving successful sibling results and existing wait records.

The scheduler records selected/skipped edges and schedules ready nodes under the
execution lock. A join waits until every incoming route is resolved; unselected
routes have skipped step records without attempts. Join input bindings assemble
named branch outputs; the executor returns keys in sorted order and validates
the declared output schema. Completion and scheduling the one join job commit
together. Duplicate deliveries cannot enqueue a second join.

A permanent branch failure fails the execution and cancels unfinished siblings,
their approvals and active jobs. Cancellation stops all branches; the overall
deadline fails unfinished work and expires pending approvals. Completed branch
outputs remain in history. Late results cannot reopen cancelled or failed work.
Infrastructure retries and human approval retries target their own branch.

Stop old workers before applying `f081_parallel_jobs`, then restart upgraded
workers. Existing linear receipts retain their identity and default target fields.
Downgrade refuses to remove parallel history. Parallel graphs require durable
workers; the local deterministic helper supports linear graphs only.

`test_parallel_runtime.py` and `test_parallel_recovery.py` exercise out-of-order
completion, nested regions, conditional skips, bounded worker concurrency,
branch waits/retries, decisions during sibling I/O, failure/cancellation/deadlines,
real worker-process death and recovery, and migration/history guards. These are
local PostgreSQL fixtures; they do not claim external-provider or hosted execution.
