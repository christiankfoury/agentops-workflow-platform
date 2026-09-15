# Durable retries and deadlines

Phase 77 applies the immutable version's node retry policy and timeout settings
to generic execution. Each numbered `StepAttempt` is retained; the number counts
infrastructure attempts, while `StepRun.iteration` remains the separate quality
revision identity. Infrastructure retries keep the same logical idempotency key.

## Retry policy and persisted decisions

`retry.max_attempts` includes the first attempt and defaults to 1. Ordinary
failures retry only when their code appears in `retry.retryable_errors`; input,
output, binding and graph-contract failures remain permanent even if listed.
Each failed attempt stores its original code/message and `error_classification`
(`retryable` or `permanent`). Historical attempts retain a null classification
when none was recorded at execution time.

For attempt number `n`, the base delay is the smaller of `max_delay_seconds` and
`initial_delay_seconds * backoff_factor ** (n - 1)`. Symmetric jitter varies that
delay by `jitter_fraction`, with the result capped again at `max_delay_seconds`.
The chosen timestamp is persisted on the logical step's `next_attempt_at` and
the new job's `due_at`; worker restart does not choose another delay.

Attempt failure, the step's retrying state, failed job history and the next queued
job commit atomically. Due jobs release worker execution slots while waiting.
Preparing the next attempt clears the retry timestamp and prior logical-step
error; the earlier attempt's error remains immutable. Duplicate failure delivery
cannot allocate another retry or change the chosen timestamp.

Lease-abandoned attempts use the same pinned attempt budget and backoff, plus
the Phase 76 recovery-count bound. Crashes before any attempt exists remain
bounded by the recovery count. Abandoned attempts remain visible; recovery never
erases them or resets attempt numbers. Exhaustion ends in explicit failed run/job
state with `retry_exhausted` or `recovery_exhausted` rather than a runnable job.

## Deadlines and stale results

Starts persist the run's `deadline_at` using the graph's `overall_timeout_seconds`.
Attempt allocation persists an attempt deadline from its node's `timeout_seconds`,
capped by the run deadline. The database clock supplies runtime time. New schema
fields backfill active historical generic records; no past timeout enforcement
or failure classification is fabricated for completed history.

The worker's control loop checks deadlines independently of executor threads.
It can fail an active attempt and schedule a permitted retry, or fail queued,
running or backing-off work whose run deadline has expired. A retry that cannot
fit before the run deadline fails with `run_deadline`. Completion checks deadlines
again inside the same execution/job locks, so a late result cannot become success
between watchdog polls. Timeout, completion, recovery and terminal-state changes
are serialized by the execution revision; the first committed decision wins.

Timed-out synchronous Python handlers may continue until they return. Their late
results are fenced, and they retain their physical worker slot while running;
the engine does not create unbounded replacement threads. Other workers may run
the durably scheduled retry. Supported I/O abort follows in Phase 78. Handler
invocation is at least once where retries are allowed, and remote side effects
require the later effect ledger/provider reconciliation contract.

`--drain` continues polling while future queued retries exist, without occupying
execution slots during backoff. Normal workers continue polling an empty queue.

## Retry ownership and validation

The generic engine owns infrastructure retries. Future generic provider adapters
must disable hidden SDK retries (`max_retries=0`) and return typed failures to the
engine, so attempt history reflects actual engine attempts. Existing legacy LLM
paths retain their earlier SDK configuration; Phase 77 makes no provider calls.
Quality revision control remains a separate later capability.

`tests/test_retry_runtime.py` covers fake-clock jitter/deadline decisions, durable
backoff across a worker subprocess restart, permanent failures, exhaustion,
duplicate failure races, watchdog timeout/stale results, physical concurrency
bounds, queued deadlines and a centralized terminal-cancellation race fixture.
The actual cancel API and I/O abort are Phase 78. Migration tests cover active
deadline backfill, queued deadline failure and retained history on downgrade.
