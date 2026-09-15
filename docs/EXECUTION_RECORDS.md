# Generic execution records

Phase 72 adds persistence, centralized lifecycle transitions and read APIs. It
does not accept starts, interpret graphs, enqueue jobs or call providers. Those
boundaries follow in Phases 73–75 and the primitive implementation phases.

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
Heartbeat fields are storage only at this stage; no lease or recovery claim is
made. Attempt allocation uses the pinned node's bounded retry policy, but durable
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
