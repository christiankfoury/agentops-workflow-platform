# Phase Progress

Current next implementation phase: **Phase 71 — Workflow Definitions and Immutable Versions**.

Completed autonomous target: Phase 46 through Phase 65.

Target range status: Phase 46 through Phase 65 complete.

**Active autonomous target: Phases 66–105**, authorized on 2026-09-15 with
phase-scoped commits and pushes to main and completed CI required before advancement.
The documentation-only revision
of 2026-09-14 defines Phases 66–105 in [phases.md](phases.md), based on the
[consolidated platform plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md).
Phases 66–70 are complete; Phase 71 is in progress; Phases 72–105 remain planned.

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

### Phase 71: Workflow Definitions and Immutable Versions

Status: In progress — authorized implementation run.

Scope: tenant-owned definitions, revisioned drafts, immutable publication snapshots,
version history and archive APIs.
See [the full phase entry](phases.md#phase-71-workflow-definitions-and-immutable-versions) for
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
| 71 | In progress | Workflow Definitions and Immutable Versions |
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
- Commit, push, CI and post-push review: pending.

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
