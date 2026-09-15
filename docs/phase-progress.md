# Phase Progress

Current next implementation phase: **Phase 66 — State Transition Invariants**.

Completed autonomous target: Phase 46 through Phase 65.

Target range status: Phase 46 through Phase 65 complete.

**Active autonomous target: Phases 66–105**, authorized on 2026-09-15 with
phase-scoped commits and pushes to main and completed CI required before advancement.
The documentation-only revision
of 2026-09-14 defines Phases 66–105 in [phases.md](phases.md), based on the
[consolidated platform plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md).
Phase 66 is in progress; Phases 67–105 remain planned.

The former Phase 66 Demo Video Script and Phase 67 Final Recruiter Case Study
are rescheduled as Phases 104 and 105. Completed Phases 1–65 retain their IDs and
history. Existing product refinement can continue when separately requested.

## Completed Phases

| Phase | Status | Notes |
| --- | --- | --- |
| 1 | Complete | Implemented and validated before this tracker was created. |
| 2 | Complete | Implemented and validated before this tracker was created. |
| 3 | Complete | Implemented and validated before this tracker was created. |
| 4 | Complete | Implemented and validated before this tracker was created. |
| 5 | Complete | Implemented and validated before this tracker was created. |
| 6 | Complete | Implemented and validated before this tracker was created. |
| 7 | Complete | Implemented and validated before this tracker was created. |
| 8 | Complete | Implemented and validated before this tracker was created. |
| 9 | Complete | Implemented and validated before this tracker was created. |
| 10 | Complete | Uploaded inputs and Sales Report input flow. |
| 11 | Complete | Sales Analyst run endpoint and agent step persistence. |
| 12 | Complete | Agent step timeline UI on workflow detail page. |
| 13 | Complete | Sales Reviewer Agent backend and UI action. |
| 14 | Complete | Score-based retry routing and analyst retry feedback. |
| 15 | Complete | Human approval backend and approval state transitions. |
| 16 | Complete | Human approval UI list/detail/actions. |
| 17 | Complete | Writer Agent backend, final output persistence, completion transition, focused tests, and workflow detail trigger. |
| 18 | Complete | Dedicated final output page with summary metrics, approval status, and expandable workflow trace. |
| 19 | Complete | Agent-level cost estimation, cost event persistence, workflow cost totals, and focused backend coverage. |
| 20 | Complete | Cost dashboard with spend metrics, workflow and agent cost breakdowns, token usage, and expensive-run table. |
| 21 | Complete | Structured workflow event model, migration, logging service, run event endpoint, and lifecycle logging across workflow creation, agents, retries, human approvals, completion, and failures. |
| 22 | Complete | Workflow run detail observability timeline UI backed by workflow event API client/types and smoke coverage. |
| 23 | Complete | Sales report baseline single-agent execution path with API/UI trigger, cost/event persistence, final output storage, and focused tests. |
| 24 | Complete | Evaluation case/result schema foundation, migration, read schemas, idempotent sales evaluation case seeding, and focused seed coverage. |
| 25 | Complete | Sales evaluation runner service and CLI for baseline and multi-agent modes with persisted evaluation results and focused runner coverage. |
| 26 | Complete | Deterministic sales evaluation scoring and aggregate metrics for factual accuracy, unsupported claims, completeness, approval rate, cost, latency, and retries. |
| 27 | Complete | Evaluation summary API and dashboard comparing baseline vs multi-agent metrics with navigation and smoke coverage. |
| 28 | Complete | Prompt version summaries recorded on evaluation results plus prompt-version performance comparison helper and tests. |
| 29 | Complete | Prompt version management UI for listing, creating, viewing, and activating prompts with API client wiring and smoke coverage. |
| 30 | Complete | Customer feedback classifier and product insight output schemas for themes, sentiment, feature requests, bug reports, recommendations, and supporting examples. |
| 31 | Complete | Customer Feedback Classifier Agent backend endpoint, structured output validation, agent step persistence, cost/event tracking, and focused API coverage. |
| 32 | Complete | Customer Feedback Insight Agent backend endpoint that consumes classifier output, validates product insight JSON, persists insight steps, and advances runs toward review. |
| 33 | Complete | Customer feedback reviewer and writer support through existing run endpoints, including human approval handoff and end-to-end workflow coverage. |
| 34 | Complete | Customer feedback evaluation case seeding, baseline and multi-agent evaluation runner support, and workflow-type evaluation summary dashboard grouping. |
| 35 | Complete | Incident workflow schemas for timeline events, ambiguous events, impact, confirmed facts, inferred claims, suspected root cause, and follow-up actions. |
| 36 | Complete | Incident Timeline Agent backend endpoint that extracts chronological events, validates timeline JSON, and persists timeline steps with cost/event tracking. |
| 37 | Complete | Incident Root Cause Agent backend endpoint that consumes timeline output, separates confirmed facts from likely/inferred claims, tracks unknowns, and persists root cause steps. |
| 38 | Complete | Incident reviewer and writer support through existing run endpoints, including human approval handoff, final post-incident report persistence, and end-to-end workflow coverage. |
| 39 | Complete | Incident evaluation case seeding with timeline expectations, baseline and multi-agent incident evaluation runner support, and incident workflow metrics in evaluation summaries. |
| 40 | Complete | Optional Router Agent workflow detection endpoint plus new workflow form controls for manual selection or auto-detect before creating uploaded inputs and workflow runs. |
| 41 | Complete | Router confidence thresholds for auto-select, confirmation, and manual-selection fallback plus router accuracy/confidence tracking in evaluation results and dashboard summaries. |
| 42 | Complete | Workflow cancellation recovery with cancellation events, in-flight step failure messages, cancel UI action, and workflow detail recovery summaries for failed or cancelled runs. |
| 43 | Complete | Structured output guardrails with strict Pydantic validation, repair prompts for invalid structured agent JSON, safe failure after failed repairs, router output repair, and typed writer inputs. |
| 44 | Complete | Agent settings persistence and runtime resolution for model, temperature, max tokens, timeout, max retries, and active prompt overrides, with LLM request-option plumbing and focused backend coverage. |
| 45 | Complete | Admin settings UI and API for per-agent model, temperature, max tokens, timeout, retry limit, reviewer/human thresholds, and active prompt version configuration. |
| 46 | Complete | Advanced human review editing with workflow-aware structured edit controls, JSON payload assembly for writer input, and frontend smoke coverage. |
| 47 | Complete | Human feedback loop summary with reviewer issue aggregation, edited-field tracking, approval decision trends, edit event logging, dashboard section, and focused API/frontend coverage. |
| 48 | Complete | Agent performance API and dashboard with per-agent latency, cost, failure, retry, reviewer score, and schema validation failure metrics. |
| 49 | Complete | Workflow comparison API and UI pairing baseline and multi-agent evaluation runs with outputs, reviewer issues, scores, cost deltas, and latency deltas. |
| 50 | Complete | Evaluation export endpoints and dashboard links for CSV, JSON, and Markdown reports with aggregate metrics and failure cases. |
| 51 | Complete | Multipart text, Markdown, and CSV upload endpoint with UTF-8 extraction, file metadata persistence, frontend upload wiring, and focused API/frontend coverage. |
| 52 | Complete | Customer feedback CSV parsing with feedback-column validation, normalized feedback text extraction, CSV preview table, and focused upload/frontend coverage. |
| 53 | Complete | Incident log parser that normalizes timestamped pasted or uploaded logs into ordered event lines while preserving ambiguous raw lines for timeline analysis. |
| 54 | Complete | Deterministic evaluation checks now include expected customer feedback themes, incident timeline timestamps/events, unsupported generated numbers, and runner judge notes. |
| 55 | Complete | Failure case explorer dashboard for low-scoring runs, failed agent steps, schema validation failures, common failure types, and human-rejected outputs. |
| 56 | Complete | Improvement tracking dashboard with evaluation trends over time for factual accuracy, unsupported claims, completeness, approval rate, cost, and latency. |
| 57 | Complete | Polished demo dataset seeding with 10 cases per workflow, demo uploaded inputs, baseline and multi-agent runs, evaluation results, and agent trace steps. |
| 58 | Complete | Demo mode API and UI controls for seeding sales, feedback, incident, or full evaluation demo data and jumping into comparison/evaluation dashboards. |
| 59 | Complete | README case study with project overview, architecture/workflow diagrams, demo metrics, portfolio screens, evaluation methodology, setup, validation, and roadmap. |
| 60 | Complete | Technical docs for architecture, agent roles, evaluation methodology, prompt versioning, observability, and deployment operations. |
| 61 | Complete | Testing foundation expanded with shared structured-output repair tests and OpenAPI route/schema surface coverage across workflow, evaluation, demo, and approval endpoints. |
| 62 | Complete | Sales workflow integration tests covering analyst-to-reviewer flow, reviewer retry trigger, human approval pause, writer approval gate, and completion after approval. |
| 63 | Complete | Evaluation foundation tests covering deterministic score math, unsupported generated numbers, latest completed baseline vs multi-agent comparison pairing, reviewer issue extraction, and evaluation result storage metadata. |
| 64 | Complete | Basic security and input safety controls for secret masking, opt-in API key authentication, role checks, opt-in rate limiting, upload MIME/size limits, and persisted input length limits. |
| 65 | Complete | Portfolio polish for the recruiter-facing web app shell, landing dashboard, workflow run list, approvals list, evaluation error states, mobile navigation, and offline API handling. |

## Next Phase

### Phase 66: State Transition Invariants

Status: In progress — authorized implementation run.

Scope: inspect and centralize runtime transitions, preserve existing workflow
behavior, reject stale/illegal state changes, and cover lifecycle races.
See [the full phase entry](phases.md#phase-66-state-transition-invariants) for
dependencies, acceptance checks, and the shared delivery gate.

## Planned Platform Phases

This is a status index; implementation details live only in `docs/phases.md`.

| Phase | Status | Scope |
| --- | --- | --- |
| 66 | In progress | State Transition Invariants |
| 67 | Planned — not started | User Identity and Organization Membership |
| 68 | Planned — not started | Tenant Ownership and Isolation |
| 69 | Planned — not started | Role Permissions and Approval Audit |
| 70 | Planned — not started | Typed Workflow Graph Schema |
| 71 | Planned — not started | Workflow Definitions and Immutable Versions |
| 72 | Planned — not started | Generic Step Runs and Attempts |
| 73 | Planned — not started | Idempotent Generic Run Starts |
| 74 | Planned — not started | Deterministic Graph Interpreter |
| 75 | Planned — not started | Transactional Durable Job Queue |
| 76 | Planned — not started | Leases Heartbeats and Crash Recovery |
| 77 | Planned — not started | Durable Retries Backoff and Deadlines |
| 78 | Planned — not started | Durable Cancellation |
| 79 | Planned — not started | Durable Delay Steps |
| 80 | Planned — not started | Durable Approval Steps and Resume |
| 81 | Planned — not started | Parallel Branches and Joins |
| 82 | Planned — not started | LLM Executor and Bounded Quality Revisions |
| 83 | Planned — not started | Sales Workflow Template Migration |
| 84 | Planned — not started | Customer Feedback Template Migration |
| 85 | Planned — not started | Incident Template and Evaluation Compatibility |
| 86 | Planned — not started | Tool Contracts Credentials and Effect Ledger |
| 87 | Planned — not started | HTTP REST Tool |
| 88 | Planned — not started | PostgreSQL Query Tool |
| 89 | Planned — not started | GitHub SaaS Tool |
| 90 | Planned — not started | Governed LLM Tool Calling |
| 91 | Planned — not started | Webhook Triggers |
| 92 | Planned — not started | Scheduled and Cron Triggers |
| 93 | Planned — not started | Generic Workflow Builder Editor |
| 94 | Planned — not started | Builder Validation Publication and Version History |
| 95 | Planned — not started | Generic Graph Run Debugger |
| 96 | Planned — not started | Safe Manual Retry and Recovery Controls |
| 97 | Planned — not started | Worker Observability and Live Updates |
| 98 | Planned — not started | Deterministic Throughput Benchmark |
| 99 | Planned — not started | Crash and Concurrency Reliability Experiments |
| 100 | Planned — not started | Production Container Packaging |
| 101 | Planned — not started | Kubernetes Deployment Manifests |
| 102 | Planned — not started | Kubernetes Operations and Recovery Verification |
| 103 | Planned — not started | Platform README and Architecture Reconciliation |
| 104 | Planned — not started | Platform Demo Video Script |
| 105 | Planned — not started | Final Workflow Platform Case Study |

## Per-Phase Execution Record

### Phase 66 — State Transition Invariants (2026-09-15)

- Authorized range: 66–105. Initial tree clean; local main and remote main both
  `f671899c84b5b5772755340d892c40c474a8e4dd`; prior CI run `34902055126` succeeded.
- Inspection: legacy agent setters bypass validation; step output, cost, events,
  approvals and cancellation use independent commits. Existing tests mostly use
  fake sessions and cannot establish database race safety.
- Plan: centralize validated transitions and explicit short workflow transactions;
  serialize mutations on the run, fence provider results using a persisted revision,
  atomically commit step/result/event/approval changes, and retain fixture imports
  through an explicit construction path. No database lock is held during LLM I/O.
- Acceptance: preserve three workflows and baselines, quality retries and human
  edits; reject terminal reopen, stale completion and conflicting decisions; verify
  rollback and cancellation/completion races with disposable PostgreSQL sessions.
- Rollout: additive run revision migration; existing runs begin at revision zero.
  No destructive backfill, provider calls, or production deployment required.
- Scope size: all legacy execution services must adopt the same transaction
  boundary; mechanical indentation may exceed the preferred 300–700 changed lines.
- Implementation: centralized run/step transitions, revision-checked transactions
  across all legacy agents and approval/recovery services, atomic result/cost/event
  commits, cancellation through status PATCH, and completion telemetry after commit.
  Added PostgreSQL CI service, migration checks, 17 database/domain tests, and
  frontend support for the state-transition event type.
- Validation (local, deterministic providers): `uv run --directory apps/api
  alembic upgrade head` passed on a fresh disposable PostgreSQL 16 database;
  `uv run --directory apps/api ruff check src tests` passed;
  `uv run --directory apps/api pytest -q` with `WORKFLOW_TEST_DATABASE_URL`
  passed **260 tests**; `pnpm --dir apps/web typecheck` passed;
  `pnpm --dir apps/web test:smoke` passed **2 tests**. The full API suite completed;
  no fallback or paid provider call was required. An existing Starlette/httpx
  deprecation warning remains.
- Local review: checked lifecycle branches and direct-write search. Only the
  explicit demo fixture import assigns run/step statuses outside the authority;
  evaluation-result statuses are separate scoring bookkeeping. Existing approval
  decisions remain under validated, run-serialized transactions. Historical
  fixture construction is covered by the existing demo seed/reseed tests.
- Implementation commit: `74bd87921c9e791bc57bd0843b6bdb53dfb5f0d6`, pushed to
  main. [CI run 34935129063](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34935129063)
  completed successfully: API (including PostgreSQL and audit), Web, Docker Compose.
- Post-push review found two actionable gaps: creation and its first event still
  had separate commits; a decision could overwrite concurrently edited feedback
  from a cached approval. Fix: atomic initialization for API/evaluation starts and
  approval refresh under the run lock. Added rollback, accepted-start, feedback-race,
  and rollback-telemetry regression assertions; 44 focused tests passed.
- Migration downgrade to `e7f8a9b0c123` and re-upgrade passed on the disposable
  database; six demo fixture tests, lint, and diff checks passed.
- Fix validation: full `uv run --directory apps/api pytest -q` with PostgreSQL
  passed **263 tests**; `uv run --directory apps/api ruff check src tests` passed.
- Fix commit/push/CI and follow-up review: pending; phase is not complete.

When a future phase starts, add a record here using these fields:

- Phase and authorized target range.
- Plan: inspected code, changes, preserved behavior, acceptance cases, and migration/rollout impact.
- Implementation summary and affected files.
- Validation: exact commands/results and evidence paths; distinguish local fixtures from live checks.
- Implementation commit ID and push status; relevant CI result.
- Review of the pushed change: findings and disposition.
- Fix commit IDs, validation, push status, and follow-up review, if needed.
- Completion decision, remaining limitations, and next phase eligibility.

No new implementation commits, pushes, tests, deployment results, or completed
phases are claimed by this planning update. Documentation validation checks
feature coverage, numbering, dependencies, links, and consistency with the inspected
code. The future delivery loop is plan → implement → validate → commit → push →
review → fix/revalidate/commit/push/review as needed.

## Last Known Validation Pattern

### Documentation planning revision — 2026-09-14

- All 13 detailed findings and 9 concluding recommendations map to R01–R14.
- Phase headings are unique and continuous from 1–105; all 40 future phases
  have dependencies, requirement references, implementation scope, and acceptance checks.
- All eight requested step primitives are covered; phase dependencies point backward.
- Completed Phase 1–65 definitions and the completed ledger match their prior content.
- All 24 new local Markdown links/anchors resolve; code fences are balanced.
- `git diff --check` passed. Application tests were not run for this documentation-only revision.

### Prior implementation validation

Recent phases used:

```powershell
uv run --directory apps/api pytest <focused API test files>
uv run --directory apps/api ruff check src tests
pnpm --dir apps/web typecheck
pnpm --dir apps/web test:smoke
```

Note: the full API test suite passed quickly in Phase 42.
