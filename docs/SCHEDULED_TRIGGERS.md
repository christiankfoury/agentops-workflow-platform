# Scheduled triggers

Workers fire enabled schedules through the shared durable start service. No schedule
exists by default. Apply migration `f092_workflow_schedules` before running the new
API and workers; install the locked croniter and tzdata dependencies on both.

## Configuration

Administrators use `POST /workflow-schedules` and full replacement
`PUT /workflow-schedules/{id}` with `expected_revision`. Reads and paginated
`/{id}/fires` history require tenant-scoped `read` permission.

```json
{
  "name": "Weekday report",
  "definition_id": "<workflow definition UUID>",
  "service_principal_id": "<service principal UUID>",
  "version_policy": "published",
  "cron": "0 9 * * mon-fri",
  "timezone": "America/Toronto",
  "input": {"value": 1},
  "enabled": true,
  "concurrency_policy": "forbid",
  "missed_run_policy": "coalesce"
}
```

The configured service principal needs operator role and `workflow.start`; its
account and organization must remain active. Identity checks also apply to local
development mode. `published` resolves the current version at acceptance; `pinned`
requires an explicit `version_id`. Accepted history retains that version and
configuration revision. Input must satisfy the selected workflow's schema.

Cron uses five fields: minute, hour, day of month, month, day of week. Numbers,
month/weekday names, lists, ranges, steps and wildcards are supported. If both day
fields restrict dates, ordinary cron OR semantics apply. Seconds, years, macros,
random/hash fields and special calendar extensions are rejected. Search is bounded
to five years and 2,000 timezone candidates. Invalid or unsatisfiable schedules
fail validation. Next occurrences are strictly after the reference instant.

## Time, missed ticks, and overlap

The persisted next-fire instant is UTC; cron selection follows the named IANA zone.
Nonexistent local times are skipped. Ambiguous times use their earlier occurrence
once. Cron is evaluated in naive local time, then checked through a ZoneInfo UTC
round trip, so this behavior does not depend on croniter's own DST adjustment.
The implementation follows [croniter's bounded search contract](https://github.com/pallets-eco/croniter)
and [Python's fold and timezone rules](https://docs.python.org/3/library/zoneinfo.html).

At a due tick, the worker coalesces all missed ticks into one decision. The receipt
retains the earliest pending tick, decision time, and whether more ticks were
coalesced; next-fire advances beyond the current clock. It never creates an
unbounded catch-up queue. If the preceding scheduled run remains pending, running,
waiting or retrying, this tick is recorded as `skipped/active_run`. Already accepted
runs continue when their schedule is paused. Worker deadline enforcement occurs
before schedule firing, allowing an expired run to become terminal first.

Pause with `enabled:false`. Pause/name changes preserve the pending tick, and resume
performs one catch-up decision if due. Changing cron, zone, input, service identity
or workflow routing resets the pending tick to a future occurrence and audits that
reset. Such edits do not remove an already active run's overlap protection.
Configuration and fire history are retained; disable schedules instead of deleting.

## Claims, recovery, and operations

Every worker performs a bounded schedule maintenance batch before claiming jobs.
Replicas lock due schedules with `FOR UPDATE SKIP LOCKED`. Service validation,
version resolution, run/job acceptance, immutable fire history and next-fire
advancement commit together. There is no provider call inside this transaction.
An abrupt process exit before commit rolls it back; another worker can fire the
original tick. A unique schedule/tick receipt and the schedule lock prevent duplicate
acceptance. The ordinary queue handles execution after acceptance.

Known authorization/input/version failures retain a `rejected` receipt and advance
the tick; repairing configuration affects future ticks. Unexpected errors roll back
the entire decision, log only an error class, and leave the tick available on the
next poll. They do not block other candidates in the current batch. Check worker
logs for repeated transaction failures; fire history contains committed decisions,
not attempts that failed to commit. Keep worker clocks and timezone data consistent.

Configuration responses expose next/last-fire time, last outcome/error, revision
and the most recently accepted execution ID. That execution may already be terminal;
use its execution status for current state. Fire history provides the exact pinned
version, principal, revision, original tick, coalescing flag and execution ID.

Validation uses fake schedule clocks, real disposable PostgreSQL, competing
scheduler sessions and an abruptly exiting subprocess after queue insertion. A
deterministic workflow is also completed through the real worker loop. No live
model/provider call or production deployment is part of this validation.
