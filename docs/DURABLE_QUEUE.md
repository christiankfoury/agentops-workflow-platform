# Durable checkpoint queue

Phase 75 introduces PostgreSQL jobs and the local worker. Generic start requests
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
scan is the only cross-organization queue operation; each worker opens a fresh
session bound to the claimed organization before reading execution data.

Dispatch locks the claimed job, records its one-time dispatch marker and prepares
the attempt in one commit. The interpreter releases database locks for execution.
Completion verifies organization, job token, attempt identity and run revision,
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

Phase 75 does not recover a process killed during running work. Interrupted
claims remain visible as running, and unexpected worker exceptions are logged
by class without copying sensitive exception text. Phase 76 adds leases,
heartbeats and recovery. Engine retries, cancellation, waits, parallel execution,
LLM calls and external side effects arrive in later phases.

The PostgreSQL tests in `tests/test_durable_queue.py` cover atomic acceptance,
concurrent bounded claims, duplicate deliveries during and after execution,
completion/enqueue rollback, worker-process restart with queued checkpoints,
graceful draining, tenant reads, migration backfill and history retention.
These deterministic fixtures do not constitute hosted/provider deployment evidence.
