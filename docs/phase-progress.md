# Phase Progress

Current next implementation phase: **Phase 80 — Durable Approval Steps and Resume**.

Completed autonomous target: Phase 46 through Phase 65.

Target range status: Phase 46 through Phase 65 complete.

**Active autonomous target: Phases 66–105**, authorized on 2026-09-15 with
phase-scoped commits and pushes to main and completed CI required before advancement.
The documentation-only revision
of 2026-09-14 defines Phases 66–105 in [phases.md](phases.md), based on the
[consolidated platform plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md).
Phases 66–79 are complete; Phases 80–105 remain planned.

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

### Phase 74: Deterministic Graph Interpreter

Status: In progress — authorized implementation run.

Scope: registry-dispatched deterministic code, transform and condition execution,
persisted selected/skipped routes and restartable checkpoints.
See [the full phase entry](phases.md#phase-74-deterministic-graph-interpreter) for
dependencies, acceptance checks, and the shared delivery gate.

## Planned Platform Phases

This is a status index; implementation details live only in `docs/phases.md`.

| Phase | Status | Scope |
| --- | --- | --- |
| 66 | Complete | State Transition Invariants |
| 67 | Complete | User Identity and Organization Membership |
| 68 | Complete | Tenant Ownership and Isolation; migration, CI and review passed. |
| 69 | Complete | Role Permissions and Approval Audit; fix, CI and review passed. |
| 70 | Complete | Typed Workflow Graph Schema; fix, CI and review passed. |
| 71 | Complete | Workflow Definitions and Immutable Versions; fix, CI and review passed. |
| 72 | Complete | Generic Step Runs and Attempts; fix, CI and review passed. |
| 73 | Complete | Idempotent Generic Run Starts; fix, CI and review passed. |
| 74 | Complete | Deterministic interpreter, persisted checkpoints, typed bindings/failures and fenced continuation. |
| 75 | Complete | Atomic durable queue, bounded worker dispatch, job reads and process restart evidence. |
| 76 | Complete | Live leases, heartbeat renewal, fenced bounded recovery and process-kill evidence. |
| 77 | Complete | Durable backoff, attempt classification, deadlines and bounded watchdog enforcement. |
| 78 | Complete | Durable cancellation intent/API, atomic work termination, I/O abort hooks and late-result fencing; CI/review passed. |
| 79 | Complete | Persisted UTC waits, bounded wake processor, atomic continuation and cancellation/deadline integration; CI/review passed. |
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
- Fix commit: `3b42ce928ddd059ede012b72feafc189eea0adbd`, pushed to main.
  [CI run 34935435952](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34935435952)
  completed successfully for API, Web, and Docker Compose; all commit check runs
  are successful.
- Follow-up review: initialization rollback and concurrent approval refresh are
  covered by independent PostgreSQL sessions; inspected the pushed fix and its
  diff. No unresolved blocking findings. Direct status-write exceptions and the
  synchronous cancellation limitation are documented in `ARCHITECTURE.md`.
- Completion: Phase 66 complete. Implementation, fixes, local validation, pushes,
  and both CI/review cycles passed. No live provider or deployment claim is made.
  The final documentation record is pushed separately; wait for its CI before
  beginning Phase 67.

### Phase 67 — User Identity and Organization Membership (2026-09-15)

- Dependency gate: Phase 66 final record `4a8211c1c132c89990426bcf6ec610592ea4cc03`
  pushed; [CI run 34935606696](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34935606696)
  passed API, Web, and Docker Compose. Tree clean before Phase 67.
- Inspected security dependency, shared web API client, navigation, models,
  configuration, migration chain, and existing security tests.
- Plan: additive users/organizations/memberships/service-principal schema;
  verify fixed-algorithm OIDC JWT signatures, issuer, audience, expiry and subject;
  resolve roles and organization access from active database records. Add
  authorization-code/PKCE sign-in, HttpOnly session and organization selection.
  Preserve local prototype mode while blocking public identity rollout until
  tenant isolation and full role enforcement land in Phases 68–69.
- Acceptance: real signed local token fixtures, wrong signature/issuer/audience,
  expiry, role-header forgery, disabled identity/membership and service scope;
  fresh/migrated PostgreSQL schema and session/organization frontend checks.
- Rollout: no existing data ownership backfill until Phase 68; no live IdP,
  external account, paid provider or public deployment required for this phase.
  Live issuer/client registration and callback configuration remain explicit setup.
- Implementation: additive identity/membership/service/session schema, RS256 OIDC
  validation and server-derived principals, revocable hashed browser sessions,
  PKCE/state/nonce sign-in and organization selection, shared web session forwarding,
  idempotent administrator provisioning CLI and public-startup rollout gate.
- Local validation: migration upgrade and downgrade/reapply passed on disposable
  PostgreSQL; `uv run --directory apps/api pytest -q` with PostgreSQL passed
  **281 tests**; `uv run --directory apps/api ruff check src tests` passed;
  `uv run --directory apps/api pip-audit` found no known vulnerabilities.
  `pnpm --dir apps/web lint`, `typecheck`, `test:smoke` (**7 tests**) and `build`
  passed. Browser tests simulate provider exchanges; no live IdP check is claimed.
- Scope size: identity schema, cryptographic verification, complete browser sign-in,
  provisioning, configuration/docs and security regression fixtures exceed the
  preferred phase size; all changes belong to this identity boundary.
- Local review: token verification uses configured keys/algorithm; bearer tokens
  stay outside request bodies to avoid validation-error echo; cookies store opaque
  sessions; membership/disablement is server-authoritative. Public identity rollout
  and operation-specific service scopes remain gated on Phases 68–69.
- Implementation commit: `2f926cd2985564c946af3f731e194394aaee0251`, pushed to main.
  [CI run 34937076289](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34937076289)
  passed API (fresh migration, tests, lint, audit), Web, and Docker Compose.
- Post-push review: checked fixed issuer/audience/algorithm validation, authoritative
  identity and membership lookup, disabled accounts, service organization boundaries,
  session hashing/expiry/revocation, state/nonce/PKCE, secret handling and migration
  compatibility. No blocking findings; no fix commit required.
- Completion: Phase 67 complete. Final provisioning adjustment passed 18 identity
  tests, lint and typecheck; final account rendering is dynamic and passed CI build.
  Public deployment and operation-specific scope enforcement remain gated for
  Phases 68–69. No live identity provider or hosted authentication is claimed.
  Final documentation record is pushed separately; wait for its CI before Phase 68.

### Phase 68 — Tenant Ownership and Isolation (2026-09-15)

- Dependency gate: Phase 67 final record `77dd80bfc2e889020351b79d86caf4a96cdc5636`
  pushed; [CI run 34937269071](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34937269071)
  passed all API, Web and Docker Compose jobs. Clean tree before this phase.
- Inspected every business model and router, prompt activation/uniqueness, agent
  settings, demo/evaluation seeding and the centralized workflow transactions.
- Plan: introduce one tenant-owned model contract; bind authenticated sessions to
  their verified organization; apply tenant filters to ORM reads (including nested
  and aggregate queries), enforce ownership and references on writes, and add
  database ownership constraints. Scope prompt/setting uniqueness and demo copies.
- Migration/rollout: assign all preexisting business records to an explicit default
  organization; retain original run/input ownership in a migration ledger for
  reversal, verify row counts, and preserve IDs/content. Keep public startup blocked
  until Phase 69. Local prototype/evaluation CLI sessions use the default organization.
- Acceptance: two-organization list/detail/nested reads, exports/aggregates, writes,
  prompt activation, demo copies, and foreign-reference attempts; migration
  upgrade/reversal with real legacy data and PostgreSQL constraint verification.
- Implementation: shared tenant-owned models and scoped ORM sessions; immutable
  ownership, application and composite database reference checks; organization-scoped
  prompt/settings constraints; independent demo copies; authenticated private browser
  exports. Migration records original owners/counts and refuses unsafe rollback.
- Validation: `uv run --directory apps/api pytest -q` with disposable PostgreSQL
  passed **288 tests** before the final two isolation cases; the final focused
  `pytest tests/test_tenant_isolation.py tests/test_tenant_migration.py -q` passed
  **9 tests**. API `ruff check src tests` and changed migration lint passed.
  Web `typecheck`, `test:smoke` (**9 tests**), `lint`, and `build` passed.
  Migration tests exercise the complete upgrade chain, real legacy contents,
  downgrade restoration, re-upgrade and refusal to lose new tenant ownership.
- Local review: all existing business routes share authenticated tenant sessions;
  aggregate/alias and nested reads are scoped, ownership is immutable, and ORM bulk
  writes cannot bypass entity checks. Public startup remains gated until Phase 69.
  No live provider or hosted deployment was attempted.
- Scope size: the ten-model ownership contract, reversible migration and two-tenant
  API/database/export regression coverage exceed the preferred phase size; all
  changes are required by the Phase 68 isolation boundary.
- Implementation commit: `9859b0592e3270750da69d8bf07ed8de7a85079b`, pushed to main.
  [CI run 34939013134](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34939013134)
  passed all API, Web and Docker Compose jobs, including the fresh migration,
  full test suite and dependency audits.
- Post-push review: inspected the committed session hooks, all business ownership
  constraints, nested/aggregate route access, prompt/settings uniqueness, exports,
  demo seed isolation and rollback data preservation. No blocking findings;
  no fix commit required. Database administration/raw SQL remains a privileged
  boundary and must explicitly scope reads; this is not database row-level security.
- Completion: Phase 68 complete. The final record is pushed separately and its CI
  must finish before beginning Phase 69. No public deployment or live IdP claimed.

### Phase 69 — Role Permissions and Approval Audit (2026-09-15)

- Dependency gate: Phase 68 record `1f952071dfebac0cee49118d9dc3c35bb8c823a6`
  pushed; [CI run 34939200348](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34939200348)
  passed all API, Web and Docker Compose checks. Clean working tree.
- Inspected identity resolution, all mutation routers, approval transactions,
  prompt/settings services, exports, existing security tests and action UI.
- Plan: one server-owned permission matrix and explicit service scopes; enforce
  request permissions plus sensitive service checks. Recheck current membership
  inside approval transactions, derive actors from identity, and require admin
  to approve high/critical findings. Persist append-only tenant audit events in
  the same transaction as starts, decisions/edits, prompts/settings, membership
  changes and accepted exports. Add admin membership/audit APIs and permission UI.
- Acceptance: role matrix, service scopes, actor forgery, membership revocation,
  cross-tenant decisions, high-severity approval, transaction rollback without
  success audit, audit actor/organization correctness and permission-aware UI.
- Migration/rollout: additive audit table; preserve legacy records and local
  development. Replace the temporary public-startup block with fail-closed verified
  identity/configuration checks. No live provider or hosted rollout is claimed.
- Implementation: shared role matrix and explicit service scopes; authenticated
  actors; decision-time membership rechecks/locks; admin-only high-severity
  approval and automated evaluation comparisons; append-only tenant audit table
  and database trigger; admin membership/audit APIs and permission-aware UI.
  Generic status PATCH only cancels, preventing advancement around approval gates.
- Local validation: `uv run --directory apps/api pytest -q` with disposable
  PostgreSQL passed **320 tests**. Final audit metadata/export changes passed
  `pytest tests/test_permissions_audit.py tests/test_evaluation_results_api.py -q`
  (**33 tests**). `ruff check src tests`, changed migration lint, web `typecheck`,
  `lint`, `test:smoke` (**11 tests**) and production `build` passed.
  The audit migration was upgraded, downgraded and reapplied in an isolated
  PostgreSQL schema; direct audit UPDATE/DELETE were rejected by its trigger.
- Local review fixes: the generic status route could bypass approval advancement;
  it now only cancels. Legacy automated comparisons can approve results, so they
  require admin. Migration logging now preserves existing application loggers
  after an in-process migration exposed a full-suite logging regression. Export
  fixtures were updated for their new audit commit contract. Initial test/build
  failures were resolved and are not counted as passing checks.
- Scope size: permission checks across all existing agent/API paths, transactional
  audit and migration, membership UI and the role/forgery/rollback matrix exceed
  the preferred phase size; all changes belong to the Phase 69 security gate.
- Limits: no live IdP or hosted rollout. Public startup now requires configured
  verified identity/HTTPS endpoints; deployment evidence follows in Phases 100–102.
  Initial provisioning and direct database administration remain privileged access
  outside the HTTP audit boundary. Audit downgrade requires retaining history.
- Implementation commit: `f391b604b0d7ad4f010824cffaeabac955b36654`, pushed to main.
  [CI run 34941875787](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34941875787)
  passed all API, Web and Docker Compose checks.
- Post-push review finding: a long-lived session could retain an old membership
  role after another session promoted that user, skipping the last-admin guard.
  Reproduced with a failing PostgreSQL regression. Membership/user lookups now
  refresh cached identities under the existing organization/membership locks.
  Fix validation: `pytest tests/test_permissions_audit.py -q` passed **31 tests**;
  API lint and `git diff --check` passed.
- Fix commit: `c1a1a20c140333c8801897949e47ba05b820da8a`, pushed to main.
  [CI run 34942274258](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34942274258)
  passed API, Web and Docker Compose. Follow-up review confirms the locked row
  overwrites stale cached state before the guard; failed changes roll back without
  audit success. No unresolved blocking findings remain.
- Completion: Phase 69 complete. Final record is pushed separately; finish its CI
  before Phase 70. No live identity-provider validation or public deployment claimed.

### Phase 70 — Typed Workflow Graph Schema (2026-09-15)

- Dependency gate: Phase 69 record `e93390002cb72e9b1c3bf3e2cda1fd74e7a90730`
  pushed; [CI run 34942474365](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/34942474365)
  passed all checks. Clean working tree before this phase.
- Inspected existing Pydantic schema conventions, the complete R01/R02 contract,
  architecture defaults and downstream interpreter/definition requirements.
- Plan: a versioned typed DAG schema for all eight primitives, bounded policies,
  closed data schemas and constrained expressions. Validate references, types,
  branch defaults, reachability/cycles, explicit merges and fork/join regions.
  Recognize bounded quality-revision metadata without permitting graph cycles.
  Keep executable support separately gated; no new runtime or persistence yet.
- Acceptance: round-trip fixtures with every primitive; both condition paths,
  missing/null/default bindings, invalid expressions/types/references/joins/cycles,
  graph complexity bounds and an explicit unsupported-executor check.
- Rollout: pure schema/validation code and fixtures; no database migration,
  provider call, public endpoint or existing workflow behavior change.
- Scope: typed configurations plus structural/type validation and security-focused
  rejection cases may exceed the preferred size; keep all work within this schema.
- Resumed with three existing untracked Phase 70 files and this phase plan;
  preserved that work. Verified local/remote main both point to `e933900` and
  rechecked the dependency CI through GitHub: all three jobs succeeded.
- Implementation: typed graph schemas and pure structural/type validation for all
  eight primitives; separate executor/revision capability checks. Added strict
  schema fixtures and graph-format documentation. Hardened pre-serialization
  depth checks and closed revision-region validation during local review.
- Validation: `uv run --directory apps/api pytest tests/test_workflow_graph.py -q`
  passed **37 tests**; `uv run --directory apps/api ruff check src tests` and
  `git diff --check` passed. No migration, frontend or runtime behavior changes.
- Local review: inspected graph topology, all expression/type checks, round-trip
  defaults, limits, missing/null handling and unavailable executor rejection.
  Scope exceeds the preferred size because typed configurations, validation and
  rejection fixtures form one graph contract. No provider calls or deployment.
- Implementation commit: `ad323ff231ea1a4f6d9c87cc1d9ce7f3819e4651`, pushed to main.
  [CI run 35003178420](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35003178420)
  passed API, Web and Docker Compose.
- Post-push review reproduced a valid graph rejected after a parallel join:
  internal conditional routes were incorrectly retained as separate downstream
  activations. The join now restores its matching fork's incoming route context;
  closed-region validation still checks all branch boundaries. Added a failing
  regression before the fix. Fix validation: **38 graph tests**, API lint and
  `git diff --check` passed.
- Fix commit: `dd3ce5da322e5754b238db0d06e10996381d50a0`, pushed to main.
  [CI run 35003435421](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35003435421)
  passed API, Web and Docker Compose. Follow-up review checked fork context,
  closed-region enforcement, conditional fan-in and unchanged rejection cases;
  no unresolved blocking findings remain.
- Completion: Phase 70 complete. Schema acceptance does not enable execution;
  no migration, provider call or deployment claimed. Final record is pushed
  separately; its CI must pass before Phase 71 starts.

### Phase 71 — Workflow Definitions and Immutable Versions (2026-09-15)

- Dependency gate: Phase 70 record `bdde1ca6b18e77e21f496648d2be2f355fe7e709`
  pushed; [CI run 35003717707](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35003717707)
  passed API, Web and Docker Compose. Working tree clean at phase start.
- Inspected schema, tenant session hooks, permission matrix, prompt API/model,
  transactional audit, migration chain and independent PostgreSQL test fixtures.
- Plan: tenant-owned definitions with editable bounded JSON drafts, optimistic
  revisions, immutable version graph snapshots and known prompt snapshots/links.
  Add create/read/update/validate/publish/archive/history/diff APIs; admin-only
  publication/archive, operator drafting and explicit unavailable-runtime results.
- Acceptance: stale and concurrent drafts/publishes, snapshot immutability,
  prompt retention, archived history, tenant/role isolation, failed-publication
  rollback and fresh/upgrade/downgrade/reapply PostgreSQL migration checks.
- Rollout: additive tables only; existing runs and prompts remain readable.
  Invalid drafts can be saved but cannot publish. Tool reference resolution is
  deferred until its registry exists; versions cannot start through an executor
  gate. No provider calls, new runtime or public deployment in this phase.
- Implementation: three tenant-owned tables, definition/version APIs, revision
  locks, transactional audit, snapshot hash and pinned prompt content/references;
  database immutability triggers and same-definition published-pointer constraint.
  The shared tenant hook now leaves non-ID composite context to database checks.
- Baseline: full API suite with disposable PostgreSQL passed **359 tests** before
  Phase 71 changes. Initial focused run found one test fixture invocation error
  and lint formatting errors; those were corrected. The next focused run passed
  **10 tests**, including migrations and independent-session races. Added a stale
  cache and wrong-definition pointer regression before full-suite validation.
- Rollout details: migration downgrade refuses to discard any saved definitions.
  Prompt activation remains mutable; referenced prompt content/deletion is blocked.
  Publication can store recognized unavailable types but cannot enable execution.
- Scope size exceeds the preferred range: persistence, reference retention,
  migration protections, complete API surface and PostgreSQL/security regression
  cases form one publication boundary.
- Validation: `uv run --directory apps/api alembic upgrade head` passed on the
  disposable PostgreSQL database. Full `uv run --directory apps/api pytest -q`
  with `WORKFLOW_TEST_DATABASE_URL` passed **370 tests** (including **11** Phase 71
  cases). API `ruff check src tests alembic/versions/f071_workflow_definitions.py`
  and `git diff --cached --check` passed. Fresh migration, downgrade/reapply and
  nonempty rollback refusal are covered in the isolated-schema migration test.
- Local review: verified locked fresh revisions, publication/rollback atomicity,
  permission/tenant checks, retained prompt activation compatibility and immutable
  history. No unresolved local findings; no live provider or deployment claims.
- Implementation commit: `f16425c09d799dd0ec4c55073bec5803620b04be`, pushed to main.
  [CI run 35005533543](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35005533543)
  passed API, Web and Docker Compose.
- Post-push review finding: the existing default prompt seeder rewrote version-one
  templates and could fail after publication froze a prompt. Reproduced against
  the migrated PostgreSQL database with a failing regression. Reseeding now
  preserves existing content/notes; changed defaults require a new version.
  Fix validation: `pytest tests/test_workflow_definitions.py tests/test_prompt_seed.py
  tests/test_prompt_versions_api.py -q` with PostgreSQL passed **19 tests**; API
  lint and `git diff --check` passed.
- Fix commit: `753599e1afa4b460894925848ab400d3201287d8`, pushed to main.
  [CI run 35005937682](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35005937682)
  passed API, Web and Docker Compose. Follow-up review confirms reseeding keeps
  existing version content and active custom prompts, while creating absent
  defaults. Publication, archived history and migration guards remain intact.
  No unresolved blocking findings remain.
- Completion: Phase 71 complete. No runtime, provider or deployment claim.
  Final record is pushed separately; wait for its CI before Phase 72.

### Phase 72 — Generic Step Runs and Attempts (2026-09-15)

- Dependency gate: Phase 71 record `61eb0937aedbfe1c94a8b266511b0072623b9381`
  pushed; [CI run 35006262965](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35006262965)
  passed all API, Web and Docker Compose checks. Working tree clean.
- Inspected legacy runs/agent steps, event/status authority, revision transactions,
  tenant foreign keys, version retention and historical API schemas.
- Plan: additive version-bound executions, logical steps, attempts and transition
  events; keep historical run/agent tables unchanged. Reuse the Phase 66 transaction
  authority for both run models and extend its centralized lifecycle operations.
  Add tenant-scoped generic reads and an explicitly labeled historical trace read.
- Acceptance: unique node/branch/iteration and attempt identity, non-LLM records
  without invented agent/model values, version pinning, illegal/stale transitions,
  independent-session duplicate attempts, atomic rollback/events, historical reads
  and migrations preserving traces/costs/evaluation links.
- Architecture/rollout: generic executions use additive tables with optional
  legacy run linkage and business labels for later template adapters. No fake
  historical graph/version backfill. New starts, dispatch and queueing remain
  Phases 73–75; this phase adds persistence/lifecycle/read contracts only.
- Implementation: four additive execution/step/attempt/event tables, unique logical
  and attempt identities, optional LLM metadata, pinned version/history guards,
  paginated tenant read APIs and explicitly labeled legacy trace compatibility.
  Extended the existing transaction/transition authority to both run models.
- Initial validation: `pytest tests/test_execution_records.py -q --tb=short`
  with PostgreSQL passed **6 tests**; API and migration lint passed. Migration
  upgrade head passed on the disposable database. Added attempt-bound/active-wait
  and pending-initialization checks before broad validation.
- Local review: strengthened generic writes to require the matching run transaction
  for output updates as well as statuses; immutable business labels preserve
  reporting identity. Added unlocked/wrong-run write regression cases. Existing
  legacy transaction semantics and APIs remain unchanged.
- Scope size: record schemas, migration/history protections, lifecycle/read APIs
  and PostgreSQL migration/race/compatibility coverage exceed the preferred size;
  all changes belong to this persistence boundary.
- Validation: full `uv run --directory apps/api pytest -q --tb=short` with
  PostgreSQL passed **377 tests**. Final write-guard changes separately passed
  `pytest tests/test_execution_records.py tests/test_workflow_transactions_postgres.py
  -q --tb=short` (**27 tests**). API/migration lint and staged diff checks passed.
  Fresh migration, downgrade/reapply, nonempty rollback refusal and complete
  legacy trace/cost/evaluation-row preservation passed in isolated schemas.
- Implementation commit: `226cf553b18ec42bb124d753be125028762be8ad`, pushed to main.
  [CI run 35008069264](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35008069264)
  passed API, Web and Docker Compose. No runtime/provider/deployment claim.
- Post-push review reproduced a child entering running before its execution.
  Added execution/step parent-state guards for child starts and protected terminal
  output/history from updates even inside a later authorized run transaction.
  Fix validation: `pytest tests/test_execution_records.py
  tests/test_workflow_transactions_postgres.py -q --tb=short` with PostgreSQL
  passed **28 tests**; API lint and diff checks passed.
- Fix commit: `ad09eb0494920679a745fa546f4ea1fa395ccdbb`, pushed to main.
  [CI run 35008525314](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35008525314)
  passed API, Web and Docker Compose. Follow-up review checked parent activation,
  terminal data preservation, atomic nested transitions, and legacy compatibility;
  no unresolved blocking findings remain.
- Completion: Phase 72 complete. Final record is pushed separately; finish its
  CI before Phase 73. No generic starts, queue, provider or deployment claimed.

### Phase 73 — Idempotent Generic Run Starts (2026-09-15)

- Dependency gate: Phase 72 record `d870fcf31079b57aa828a76a37b7c5aee09e5cdc`
  pushed; [CI run 35008772253](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35008772253)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected execution initialization/immutability, tenant transactions, published
  pointer/archive locking, graph data validation and unavailable-executor gate.
- Plan: an immutable tenant-scoped start receipt with canonical request hash and
  execution link; create receipt, pending execution, event and actor audit in one
  transaction. Add POST start with explicit/latest version resolution and retain
  the original accepted version across publication changes and request retries.
- Acceptance: independent-session duplicate starts, changed input/version conflicts,
  separate tenant key reuse, rollback without orphaned records, missing/archived/
  unavailable versions, invalid inputs, unauthorized starts and receipt retention.
- Rollout: additive receipt table; keys retained for the execution's lifetime with
  no expiry/reuse or purge API. No dispatch/queue yet; default unavailable-executor
  gate blocks real starts. Deterministic test capability fixtures exercise pending
  persistence; actual code/condition/transform executors arrive in Phase 74.
- Implementation: immutable tenant-scoped start receipts, canonical fingerprints,
  POST pending-start API, locked version resolution and atomic execution/event/
  audit acceptance. Retried requests retain their accepted version after publish
  or archive; changed requests conflict. Version reads refresh archival state.
- Initial validation: **6 focused start tests** passed with PostgreSQL, including
  concurrent duplicates, changed-request conflicts, independent tenant keys,
  rollback and receipt migration/immutability. API/migration lint passed; upgrade
  head passed on the disposable database. Added concurrent archive/cache coverage
  and broadened version, execution and authorization regression checks.
- Local review: checked stable request fingerprints, tenant boundaries, atomic
  duplicate resolution and archive locking. The uniqueness-race recovery path
  also rolls back its read transaction on failed replay. No queue/dispatch,
  provider call or deployment is claimed.
- Validation: `pytest tests/test_execution_starts.py tests/test_workflow_definitions.py
  tests/test_execution_records.py tests/test_permissions_audit.py -q --tb=short`
  with PostgreSQL passed **57 tests**. The final rollback refinement separately
  passed all **7 start tests**. API/migration lint, upgrade head and staged diff
  checks passed; fresh/downgrade/reapply and receipt retention checks passed.
- Implementation commit: `da95f9c8cf43da1defae91b0303fe2485791c671`, pushed to main.
  [CI run 35010056731](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35010056731)
  passed API, Web and Docker Compose.
- Post-push review reproduced a service-scope leak: replay returned full execution
  data to a start-only service whose read request was denied. The start API now
  returns only ID/version/status; stored I/O remains behind the read API. Added
  a failing authenticated service regression before the response projection fix.
  Fix validation: `pytest tests/test_execution_starts.py -q --tb=short` with
  PostgreSQL passed **8 tests**; API lint and diff checks passed.
- Fix commit: `a6e296f68822472b5d7c50f9f447123e3d1a6924`, pushed to main.
  [CI run 35010443711](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35010443711)
  passed API, Web and Docker Compose. Follow-up review confirmed the response
  projection applies to first starts and replays, stored actors remain correct,
  and read-scope enforcement protects I/O. No unresolved blocking findings remain.
- Completion: Phase 73 complete. Start acceptance remains behind unavailable
  executor gates; capability fixtures did not dispatch work or call providers.
  Final record is pushed separately; its CI must pass before Phase 74.

### Phase 74 — Deterministic Graph Interpreter (2026-09-15)

- Dependency gate: Phase 73 record `cf428ea6af15c5fa3c7104418265bb663ce27603`
  pushed; [CI run 35010717889](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35010717889)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected graph topology/bindings, generic records/attempt guards, revision
  transactions, start capability checks and all prior generic regression fixtures.
- Plan: server-owned versioned deterministic handler/type registry; constrained
  expression evaluation; persisted edge checkpoint state; prepare/execute/commit
  continuation functions that release database locks during executor work.
  Determine readiness from pinned graphs and persisted selected/skipped edges,
  resolve outputs and retain typed input/handler/output failures.
- Acceptance: both condition routes and output bindings, missing/null/default and
  existence/coalesce semantics, restart between checkpoints without duplicate
  completed work, stale completion, failing handlers, invalid outputs, unavailable
  primitives/handlers and bounded revision capability rejection.
- Rollout: additive checkpoint JSON on generic executions; no legacy changes or
  queue/worker deployment yet. Only code/condition/transform become executable;
  approved server registrations are required for code handler names/versions.
  Waits, parallelism, LLM/tools and quality revisions remain gated.
- Implementation: a server-owned executor registry, constrained expression evaluator,
  persisted selected/skipped edge checkpoints and a prepare/execute/complete
  continuation interface. Prepared work releases the run lock; completion checks
  the exact revision. Inputs, outputs and typed failures persist with transitions.
  Local continuation skips completed work and resolves final output bindings.
- Focused validation: `pytest tests/test_graph_interpreter.py -q --tb=short` with
  PostgreSQL passed **9 tests**. API/migration lint and disposable database upgrade
  to `f074_execution_checkpoints` passed. Migration tests covered fresh install,
  downgrade/reapply and refusal to discard nonempty checkpoints.
- Broader validation: `uv run --directory apps/api pytest -q --tb=short` with
  PostgreSQL passed **395 tests** in 377 seconds (one upstream TestClient
  deprecation warning). API/migration lint and diff checks passed. Reviewed
  capability gating, checkpoint readiness, lock release, failure atomicity,
  version pinning and legacy migration fixtures locally.
- Scope size: interpreter, expression evaluator, registry and PostgreSQL acceptance
  coverage require more than 700 changed lines together; all changes belong to
  Phase 74. No queue, live provider or deployment claim.
- Implementation commit: `99ba1abaef2c45919bb9955353b2b5129bd1c45d`, pushed to main.
  [CI run 35012920535](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35012920535)
  passed API, Web and Docker Compose.
- Post-push review reproduced uncaught numeric overflow in input/final-output
  bindings using large valid JSON integers. The evaluator now converts numeric
  overflow to a retained `expression_range` failure at every binding boundary.
  Both regressions failed before the fix. `pytest tests/test_graph_interpreter.py
  tests/test_workflow_graph.py -q --tb=short` with PostgreSQL passed **49 tests**;
  API lint and diff checks passed.
- Fix commit: `d3b6e60c57eb06ee98d64b738a908a418f132414`, pushed to main.
  [CI run 35013176751](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35013176751)
  passed API, Web and Docker Compose. Follow-up review checked typed errors at
  every binding boundary, transaction rollback/commit behavior and unchanged
  checkpoint fencing. No unresolved blocking findings remain.
- Completion: Phase 74 complete. No generic queue, crash recovery, provider or
  deployment claimed. Final record is pushed separately; finish its CI before
  Phase 75.

### Phase 75 — Transactional Durable Job Queue (2026-09-15)

- Dependency gate: Phase 74 record `898a24b4c77fc0307dcc5c8a7cc7001468615ffd`
  pushed; [CI run 35013557817](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35013557817)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected interpreter continuation, tenant isolation, transaction authority,
  idempotent starts, execution read routes, PostgreSQL fixtures and local Compose.
- Plan: durable tenant-owned checkpoint jobs; atomic initial enqueue with accepted
  starts; bounded PostgreSQL SKIP LOCKED claims; one-time dispatch and atomic
  completion/downstream scheduling. Add a local worker CLI/service with graceful
  draining, and a paginated execution-jobs read API.
- Acceptance: no executor in request handling; no orphan start/job on rollback;
  independent-session concurrent claims; duplicate dispatch/completion suppression;
  completion/enqueue rollback; real worker process restart with queued work;
  tenant-scoped job reads and migration retention.
- Rollout: additive job table with retained history and a pending-execution enqueue
  backfill. Worker deployment is local only. Running jobs interrupted by process
  death remain visible until Phase 76 adds leases/recovery; retries and waits are
  not introduced early. No provider or external effect execution.
- Implementation: tenant-owned durable checkpoint jobs, bounded SKIP LOCKED
  claims, one-time dispatch markers linked to attempts, fenced result/job/next-job
  commits and atomic final-output/job completion. Starts now return HTTP 202 after
  atomic enqueue; identical replays do not enqueue again. Added worker CLI with
  bounded concurrency and graceful draining, local Compose service, and scoped
  paginated job reads without claim tokens.
- Validation: `pytest tests/test_durable_queue.py tests/test_execution_starts.py
  tests/test_graph_interpreter.py tests/test_execution_records.py
  tests/test_workflow_definitions.py -q --tb=short` with PostgreSQL passed
  **47 tests** (one upstream TestClient deprecation warning). Includes real
  subprocess exit/restart, two-worker claims, duplicate dispatch while executing,
  atomic rollback, typed failure, tenant reads and migrated-database execution.
  Older start assertions were updated for the additional job creation event.
- API/migration lint, `alembic upgrade head`, `docker compose --env-file
  .env.example config --quiet` and diff checks passed. Migration tests covered
  empty downgrade/reapply, existing pending-run backfill and history retention.
- Local review checked tenant-bound claim consumption, attempt/job ownership,
  execution transaction authority, bounded capacity, no database lock during
  computation, and retained interrupted work. No provider/hosted deployment claim.
  This phase exceeds 700 lines because queue persistence, migration, worker,
  API contract and independent-process acceptance tests form one delivery unit.
- Implementation commit: `1d9719727c27803a25ea203ca9cc5bfad6a8a9ae`, pushed to main.
  [CI run 35015483000](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35015483000)
  passed API, Web and Docker Compose.
- Post-push review reproduced a false `checkpoint_not_ready` error when the local
  runner had completed an execution before its queued job was consumed. The worker
  now records completed jobs without a false error and does not repeat the handler.
  The regression failed before the fix. `pytest tests/test_durable_queue.py -q
  --tb=short` with PostgreSQL passed **10 tests**; API lint and diff checks passed.
- Fix commit: `220903d1c13b5ec000164cb84895036d86811405`, pushed to main.
  [CI run 35015916314](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35015916314)
  passed API, Web and Docker Compose, including the API dependency audit.
  Follow-up review confirmed successful terminal-job recording without repeated
  work, preserved failure reporting, and unchanged atomic scheduling. No unresolved
  blocking findings remain.
- Completion: Phase 75 complete. Running-process crash recovery remains Phase 76;
  no live provider or hosted deployment claimed. Final record is pushed separately;
  finish its CI before Phase 76.

### Phase 76 — Leases Heartbeats and Crash Recovery (2026-09-15)

- Dependency gate: Phase 75 record `5e02d0a1b3dbeb3c56562613d7848398fe465b5e`
  pushed; [CI run 35016450145](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35016450145)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected queue claims/dispatch, run revision fencing, generic terminal-history
  guards, attempt limits and existing process-restart fixtures.
- Plan: persisted lease expiry/heartbeat/recovery count, live-claim completion
  checks, heartbeat renewal during execution, ordered run/job locking, and bounded
  expired-job recovery. Retain abandoned attempts, resume retryable logical steps
  within their pinned attempt budget, and rotate claims without repeating completed
  checkpoints. Reapers use the existing execution transition authority.
- Acceptance: competing reclaimers, expiry/renewal races, delayed stale results,
  abandoned-attempt history and exhaustion, real worker kills before execution,
  during work and after a completed checkpoint, unique completion/downstream work.
- Rollout: stop old workers for the additive migration; existing running jobs get
  an expired lease and can be recovered by new workers. Recovery is bounded by
  configured reassignments and the pinned node attempt budget. Default one-attempt
  nodes fail explicitly if an in-flight attempt is abandoned. Handler invocation
  is at least once when retries are allowed; no remote exactly-once claim.
- Implementation: persisted lease expiry/heartbeat/recovery count, live-token
  result checks, heartbeat renewal during computation, and execution-before-job
  locking. Expired claims recover atomically under the run revision fence, retain
  abandoned attempts, and resume existing logical steps within bounded budgets.
  New claim tokens reject delayed old completions and renewals. Added job-read
  fields, worker configuration, migration and at-least-once delivery documentation.
- Initial validation: **8 lease/recovery tests** passed with PostgreSQL, including
  process kills before execution, during execution and after a checkpoint. Added
  expiry-before-reassignment and pre-attempt recovery-limit cases afterward.
- Broader command: `pytest tests/test_worker_leases.py tests/test_durable_queue.py
  tests/test_execution_starts.py tests/test_graph_interpreter.py
  tests/test_execution_records.py tests/test_workflow_transactions_postgres.py
  -q --tb=short` passed **66 tests** and exposed one batched-migration failure:
  deferred foreign-key checks from Phase 75's backfill blocked Phase 76's ALTER.
  The migration now validates pending constraints before altering the table.
  Both migration tests passed on rerun (`-k migration`, **2 passed**).
- API/migration lint, Compose configuration and the final running-lease constraint's
  empty disposable-database downgrade/reapply passed. The disposable database was
  first synchronized with the final uncommitted migration draft; no retained jobs
  were discarded. Fresh/batched upgrades and migrated old-running-job recovery are
  covered by isolated-schema tests.
- Final validation: `pytest tests/test_worker_leases.py tests/test_durable_queue.py
  -q --tb=short` passed **20 tests** with PostgreSQL; API/migration lint and diff
  checks passed. One upstream TestClient deprecation warning remains.
- Local review checked lease renewal/expiry, lock order, stale/no-op rollback,
  preserved terminal results, abandoned-attempt budgets, one-owner recovery and
  migration compatibility. Process tests are local deterministic fixtures; no
  provider/hosted deployment is claimed. The migration, recovery service and
  process acceptance coverage make this phase larger than 700 changed lines.
- Implementation commit: `9d09cecd86129a9cfd200905ea0b1ab3efd3810e`, pushed to main.
  [CI run 35018468312](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35018468312)
  passed API, Web and Docker Compose.
- Post-push review checked claim token/expiry validation before result commits,
  heartbeat versus reclaimer serialization, revision changes after reassignment,
  duplicate/no-op rollback, immutable abandoned attempts and budget exhaustion.
  Migration backfill and same-transaction upgrade paths were reviewed against the
  passing regressions. No actionable blocking findings or separate fix commit.
- Completion: Phase 76 complete. At-least-once handler invocation is documented;
  no remote exactly-once effects, provider or hosted deployment claimed. Final
  record is pushed separately; finish its CI before Phase 77.

### Phase 77 — Durable Retries Backoff and Deadlines (2026-09-15)

- Dependency gate: Phase 76 record `50c2db229a9b73f26fd141fcbc8cb204ccd546e8`
  pushed; [CI run 35018801384](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35018801384)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected pinned retry/timeout metadata, numbered attempts, lease recovery,
  atomic job scheduling, interpreter failures and legacy SDK retry behavior.
- Plan: persist run/attempt deadlines, error classification and next-attempt time;
  reuse immutable version retry policies and numbered attempt history. Apply
  bounded exponential jitter/backoff, atomically schedule retries, enforce deadlines
  in the worker control loop and reject late results. Keep quality iterations
  separate and document engine-owned retry policy for later provider adapters.
- Acceptance: fake-clock delay/deadline decisions, permanent versus retryable
  errors, exhaustion, durable due times through worker restart, duplicate failure
  delivery, timeout/completion/recovery/terminal-state races and no worker sleep
  during backoff. Use real PostgreSQL for transition/scheduling uniqueness.
- Rollout: additive deadline/retry fields with active-record backfill. Long-running
  synchronous handlers may continue until they return, while their late results
  are fenced; they retain their worker slot to keep physical concurrency bounded.
  Supported I/O abort arrives in Phase 78. No provider or quality-revision execution.
- Implementation: run/attempt deadlines, failed-attempt classification and durable
  next-attempt timestamps. Retry decisions use pinned policies, exponential capped
  jitter, recorded attempt numbers and separate quality iterations. Failure and
  retry enqueue are atomic; watchdog/completion deadline checks share the run/job
  fence. Recovery backoff preserves abandoned attempts. Graceful and max-job drains
  keep watchdog enforcement active while physical handler slots remain bounded.
- Validation: `pytest tests/test_graph_interpreter.py tests/test_durable_queue.py
  tests/test_worker_leases.py -q --tb=short` passed **31 PostgreSQL tests**. A broader
  retry/start/record run passed **24 tests** and exposed a SQL bind-parsing error
  in the new migration fixture's JSON literal; that fixture was corrected.
  The corrected retry suite passed **9 tests** before adding both drain variants.
- Final validation: `pytest tests/test_retry_runtime.py tests/test_graph_interpreter.py
  -q --tb=short` passed **22 tests**, including fake-clock decisions, process restart
  with queued backoff, duplicate failures, permanent/exhausted outcomes, active and
  queued deadlines, terminal-cancellation fencing, physical concurrency bounds and
  watchdog behavior during normal/max-job/graceful draining.
- API/migration lint, Compose configuration and diff checks passed. Fresh/active
  deadline backfill and guarded downgrade/reapply passed. The disposable database
  was synchronized with the final uncommitted classification constraint before its
  empty round trip; no execution history was discarded. Earlier migration fixtures
  now seed old execution columns directly and accept the earliest retention gate.
- Local review covered retry/deadline ordering, duplicate scheduling, stale results,
  pinned budgets, retention and worker capacity. The local interpreter's checkpoint
  bound now includes allowed infrastructure attempts. No live provider or deployment
  claimed. Migration, watchdog, retry service and process tests exceed 700 lines
  together and remain one Phase 77 delivery unit.
- Implementation commit: `362a5f8382b8890f73abc4d04418166e1e40d351`, pushed to main.
  [CI run 35021319370](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35021319370)
  passed API, Web and Docker Compose.
- Post-push review checked atomic retry/job transitions, deadline-versus-completion
  ordering, recovery budgets, duplicate/no-op rollback, immutable prior errors,
  watchdog behavior during draining, and bounded physical handler slots. Migration
  and historical-row compatibility were checked against passing regressions.
  No actionable blocking findings or separate fix commit.
- Completion: Phase 77 complete. Supported I/O abort and the actual cancel API
  remain Phase 78; no live provider or hosted deployment claimed. Final record is
  pushed separately; finish its CI before Phase 78.

### Phase 78 — Durable Cancellation (2026-09-15)

- Dependency gate: Phase 77 record `82a93907e63e2fc66dfa9ddb51e132fcc4abb030`
  pushed; [CI run 35021674637](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35021674637)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected workflow-control permissions, minimal action acknowledgements, actor
  audit, run/job locking, deadline/recovery paths and registered executor boundaries.
- Plan: persist cancellation intent/time/actor/reason; atomically cancel active
  attempts, logical work and queued/running jobs under the run fence. Return a
  minimal idempotent acknowledgement, retain completed outputs, and serialize
  claiming with cancellation through execution-first locks. Add a cooperative
  abort signal and polling for controlled I/O handlers without fabricating remote
  effect reversal or successful abort metadata.
- Acceptance: queued/running/backoff/wait cancellation, repeated requests and
  rollback, tenant/role/service-scope checks, claim/completion/recovery races,
  preserved partial history, no late scheduling and controllable I/O abort.
- Rollout: additive cancellation metadata and cancelled job state. Stop old
  workers before migration/restart. Cancellation wins only when its transaction
  precedes final success; accepted external effects may remain uncertain and need
  later effect-ledger reconciliation. No live provider cancellation is claimed.
- Implemented the minimal `POST /workflow-executions/{id}/cancel` control API,
  persisted intent/actor/reason, and atomic cancellation of active attempts,
  logical steps and jobs. Completed attempts/outputs remain unchanged. Claiming
  now locks executions before jobs, and terminal queued work settles without
  invocation. Registered controlled handlers receive an idempotent abort signal;
  workers check ownership before I/O and poll during I/O with bounded lease renewal.
- Validation: initial cancellation suite passed 11 tests. Pre-commit review added
  the immediate pre-I/O ownership check and its regression. Final command
  `uv run --directory apps/api pytest tests/test_execution_cancellation.py tests/test_durable_queue.py tests/test_worker_leases.py tests/test_retry_runtime.py tests/test_graph_interpreter.py tests/test_execution_records.py tests/test_execution_starts.py -q --tb=short`
  passed **70 tests** against disposable PostgreSQL, including independent
  cancellation/claim/completion/recovery sessions and existing process-kill tests.
  `ruff check src tests alembic/versions/f078_execution_cancellation.py`,
  `alembic upgrade head`, Compose config and `git diff --check` passed. Existing
  upstream TestClient/httpx deprecation warning remains non-blocking.
- Migration validation exercised empty downgrade/reapply, pre-existing execution
  defaults, actual cancelled-job transitions, terminal immutability and history
  retention guards. The API, migration, worker control and concurrency tests form
  one phase-scoped delivery unit slightly above 700 changed lines.
- Ordering/limitations: the first committed run transaction wins cancellation
  versus final success; later cancel requests return the existing terminal state.
  Logical cancellation never certifies physical abort or reversal. Accepted remote
  actions can remain uncertain; later effect-ledger/tool adapters must reconcile
  them rather than infer non-delivery from a cancelled attempt. Only controllable
  fixture I/O was exercised; no live provider or hosted deployment claimed.
- Implementation commit: `c6c440199526bcd5d05f071b66392193b2709e4a`, pushed to main.
  [CI run 35023922575](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35023922575)
  passed API, Web and Docker Compose, including full API tests and dependency audits.
- Post-push review checked decision-time membership/service scope, minimal response
  boundaries, execution-first claim locks, atomic rollback, cancel-versus-success
  and recovery ordering, no downstream enqueue after cancellation, pre-I/O checks,
  cooperative abort failure isolation, migration compatibility and immutable partial
  history. No actionable blocking findings; no separate fix commit required.
- Completion: Phase 78 complete. Final record is pushed separately; finish its CI
  before starting Phase 79. Physical reversal of remote effects is not guaranteed.

### Phase 79 — Durable Delay Steps (2026-09-15)

- Dependency gate: Phase 78 record `f8b8f50fabc30b7d1e5a2e1e1246dc91edf482a0`
  pushed; [CI run 35024351491](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35024351491)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected delay schema/capability gating, interpreter checkpoints, worker claims,
  cancellation and deadline authority, retained attempts and generic step reads.
- Plan: accept a bounded duration or timezone-aware wake timestamp; persist UTC
  wake time/reason on a waiting logical step. Finish timer registration and its
  job atomically, releasing the worker. A bounded wake processor serializes on the
  execution, completes due waits and enqueues exactly one continuation. Integrate
  cancellation and overall deadline expiry even when no active job exists.
- Acceptance: no early wake or sleeping executor, restart after persisted wait,
  competing/duplicate wake processors, rollback, cancellation/deadline suppression,
  lease recovery around wait registration, invalid/excessive timer values and
  tenant-scoped read visibility. Use fake clocks and real PostgreSQL/processes.
- Rollout: additive nullable step wait metadata/index, retention-guarded downgrade.
  Restart workers with the new wake processor before publishing delay graphs;
  old pinned deterministic workflows remain supported. Past explicit timestamps
  are immediately due; future timestamps are bounded to seven days at registration.
- Implemented bounded duration/aware-timestamp delay configuration, UTC wake
  metadata and generic step read fields. Timer registration completes its attempt
  and job atomically while the logical step/run wait. The worker's bounded wake
  processor serializes due waits, retains metadata, commits selected outgoing
  edges and one continuation, and expires waiting runs at their overall deadline.
  Cancellation suppresses wakeup, and existing local checkpoints can hand off to
  workers without leaving false job errors.
- Validation: initial delay suite passed **21 tests**. The broader command
  `uv run --directory apps/api pytest tests/test_durable_delays.py tests/test_execution_cancellation.py tests/test_durable_queue.py tests/test_worker_leases.py tests/test_retry_runtime.py tests/test_graph_interpreter.py tests/test_workflow_graph.py tests/test_execution_records.py -q --tb=short`
  passed **121 tests** using real disposable PostgreSQL and existing subprocess
  recovery fixtures. Pre-commit review added a UTC-overflow guard; the focused
  `tests/test_durable_delays.py -k excessive` rerun passed both timestamp boundary
  cases. `ruff check src tests alembic/versions/f079_durable_delays.py`, migration
  upgrade, Compose config and `git diff --check` passed. Existing TestClient/httpx
  deprecation warning remains non-blocking.
- Persistence checks cover migration downgrade/reapply and old-row compatibility,
  retained wait history, enqueue rollback, duplicate wake processing, worker
  restart after committed registration, expired pre-registration ownership,
  fake-clock no-early-wake, cancellation, and deadlines without active jobs.
- Limitations: delay outputs are empty objects; past timestamps are immediately
  due. A normal worker service polls for due waits; `--drain` exits when current
  runnable work ends, leaving future waits durable for a later worker. These are
  local/process fixtures, not hosted deployment evidence.
- Implementation commit: `3921e53818af19ab3ae20d6293fc713305e6da5c`, pushed to main.
  [CI run 35026013473](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35026013473)
  passed API, Web and Docker Compose, including full API tests and dependency audits.
- Post-push review checked pinned timer configuration, strict timestamp bounds,
  registration atomicity, worker release, no-early/duplicate wake behavior,
  transactional enqueue rollback, cancellation/deadline ordering, UTC history,
  tenant read boundaries, migration compatibility and local-to-worker handoff.
  No actionable blocking findings; no separate fix commit required.
- Completion: Phase 79 complete. Final record is pushed separately; finish its CI
  before starting Phase 80. No live provider or hosted deployment claimed.

When a future phase starts, add a record here using these fields:

- Phase and authorized target range.
- Plan: inspected code, changes, preserved behavior, acceptance cases, and migration/rollout impact.
- Implementation summary and affected files.
- Validation: exact commands/results and evidence paths; distinguish local fixtures from live checks.
- Implementation commit ID and push status; relevant CI result.
- Review of the pushed change: findings and disposition.
- Fix commit IDs, validation, push status, and follow-up review, if needed.
- Completion decision, remaining limitations, and next phase eligibility.

The 2026-09-14 planning update did not claim implementation commits, pushes, tests,
deployment results or completed expansion phases. Its documentation checks covered
feature coverage, numbering, dependencies, links and consistency with inspected
code. The active delivery loop is plan → implement → validate → commit → push →
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
