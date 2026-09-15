# Generic execution records

Phase 72 adds persistence, centralized lifecycle transitions and read APIs.
Phase 73 adds the idempotent pending-start contract below. Phase 74 adds the
deterministic interpreter; Phase 75 adds the [durable queue](DURABLE_QUEUE.md).
Provider calls follow in later phases.

## Identity and history

- `workflow_executions` permanently pins a tenant-owned immutable workflow
  version. Input/output, lifecycle timestamps, heartbeat, errors, actor and a
  revision counter belong to the execution. Optional business/run-mode labels and
  a legacy run reference support later compatibility adapters.
- `step_runs` identifies one logical node invocation by execution, node ID,
  branch and iteration. A database unique constraint protects that identity.
- `step_attempts` identifies each numbered attempt of a logical step. Attempt
  numbers are unique per step, and infrastructure attempts share the logical
  step's stable idempotency key. This local identity does not guarantee remote
  exactly-once effects; the effect ledger follows in Phase 86.
- `execution_events` records entity creation/transitions within the same fenced
  transaction as the state change. Non-LLM steps do not require an agent name,
  model, token usage or cost. Optional attempt `llm_metadata` is reserved for
  actual model execution information.

Live records begin pending. Version/node/branch/iteration/attempt identities and
history cannot be changed or deleted. The migration installs identity guards in
PostgreSQL; ORM guards reject updates outside the matching run's shared authority,
including output changes and writes made while holding a different run's lock.
Execution/attempt heartbeat fields remain storage; Phase 76 renews ownership on
the durable job's heartbeat/lease fields. Attempt allocation uses the pinned node's bounded retry policy, but durable
retry scheduling/backoff remains Phase 77.

## Transitions and transactions

`services/workflow_state.py` owns transitions for legacy and generic entities.
`workflow_transaction` locks the actual run model, compares its persisted revision
and status, commits output/events together, and increments its revision once.
Nested operations share one transaction. Rollback removes all related changes.
Stale writers cannot adopt a newer revision implicitly or reopen terminal records.
Child starts require running parents, and terminal I/O/history remains frozen
even inside a later transaction that has acquired the current run revision.

Logical steps may wait/retry; individual attempts finish before a logical step
waits, retries or terminates. An execution cannot terminate with active steps, and
successful completion requires successful/skipped steps. The later interpreter
also validates graph completion and final outputs. Lifecycle support for waiting
does not yet implement durable approvals or delays.

## Reads and compatibility

All APIs use the existing verified organization and read permission:

- `GET /workflow-executions` and `/{id}` list/read generic records.
- `GET /workflow-executions/{id}/steps` returns logical steps.
- `GET /workflow-executions/{id}/steps/{step_id}/attempts` returns ordered attempts.
- `GET /workflow-executions/{id}/events` returns transition history.
- `GET /workflow-executions/legacy/{id}` returns an explicitly labeled historical
  run and its original `AgentStep` records. Existing business APIs remain intact.

Lists, steps and events are paginated. Nested reads validate both tenant and
parent identity. Historical outputs, labels, costs and evaluation links remain in
their original tables; no fabricated version or attempt backfill is performed.
Migration rollback refuses to discard generic execution history when it exists.

`tests/test_execution_records.py` uses independent PostgreSQL sessions for races,
checks state/output/event rollback, logical uniqueness, optional metadata, version
pinning, tenant reads and complete historical-row preservation across migration.

## Idempotent starts (Phase 73)

`POST /workflow-executions` accepts `definition_id`, optional `version_id`, object
`input` and a required `idempotency_key` (1–128 ASCII letters/digits or `._:-`).
Operators/admins with `workflow.start` permission may start. HTTP 202 acknowledges
the execution ID, version and status for first acceptance and identical retries.
Execution input/output and other data require the separate `read` permission. Input
must satisfy the pinned graph's strict schema and bounded JSON payload contract.

The server fingerprints the canonical JSON of the requested definition, version
selection and input. Object-key order is ignored; JSON numeric representations
remain distinct. The key is unique within an organization, across definitions
and callers. Reusing it with a changed request returns 409. A client must generate
one key per intended start and retain it across network retries.

The first acceptance resolves the published pointer while holding the definition
lock, or uses an explicit version belonging to that definition. Receipt, execution,
initial job, events and authenticated audit commit together. Duplicate attempts cannot
leave orphaned executions. A receipt retry returns its original execution even
after a newer publication or archival; a new key cannot start an archived version.

Receipts remain immutable for the full retained execution history. There is no
expiry, key reuse or purge API; therefore there is no expired-key fallback that
could silently create another run. Different organizations may reuse the same key.
Migration downgrade refuses to discard receipts once they exist.

Start acceptance checks the server's executor registry. Phase 74 supports code,
condition and transform nodes. Phase 75 atomically enqueues a durable job with
acceptance. No in-process background dispatch is used by this endpoint.

## Deterministic checkpoints (Phase 74)

`execution_registry.py` registers supported node executors and versioned code
handlers. The initial `builtin.identity` version 1 returns its validated inputs.
Graph data cannot import code or register handlers. Constrained expressions
provide references, explicit missing/default/null behavior, lazy boolean/coalesce
operations, comparisons, arithmetic and string concatenation without `eval`.

`graph_interpreter.prepare_next` resolves readiness from the pinned graph,
completed outputs and persisted selected/skipped edges. It commits a running
attempt with resolved inputs and returns a `WorkItem`. `execute_work` runs without
a database session or lock; `complete_work` fences its result against the prepared
execution revision and commits outputs, transitions and edge selections together.
Final output binding and execution completion use another checkpoint. Workers
can consume these operations; `run_deterministic_execution` is a bounded local
runner. The start API enqueues work for the Phase 75 worker.

Continuation after a completed checkpoint does not repeat completed handlers.
An interrupted running attempt is retained as abandoned when Phase 76 recovers
its expired job lease. Missing bindings and invalid results fail with typed errors;
handler exception details are not copied into stored user-visible errors.
Unselected condition routes get skipped logical steps without fabricated attempts.
Checkpoint migration rollback refuses to discard nonempty checkpoint data.

Wait, parallel, LLM and tool executors and bounded quality revisions remain
explicitly unavailable. Retry policy metadata does not schedule infrastructure
retries yet. These capabilities are enabled by their respective later phases.
