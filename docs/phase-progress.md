# Phase Progress

Current implementation phase: **Phase 105 — final workflow platform case study**.

Completed autonomous target: Phase 46 through Phase 65.

Target range status: Phase 46 through Phase 65 complete.

**Active autonomous target: Phases 66–105**, authorized on 2026-09-15 with
phase-scoped commits and pushes to main and completed CI required before advancement.
The documentation-only revision
of 2026-09-14 defines Phases 66–105 in [phases.md](phases.md), based on the
[consolidated platform plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md).
Phases 66–104 are complete; Phase 105 is active.

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

### Phase 105: Final Workflow Platform Case Study

Status: In progress — Phase 104 completion-record CI passed.

Scope: evidence-backed final case study, complete R01–R14 checklist and delivery
ledger review, with measured, seeded and unperformed results distinguished.
See [the full phase entry](phases.md#phase-105-final-workflow-platform-case-study) for
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
| 80 | Complete | Immutable approval snapshots, authorized decisions, superseding edits and bounded durable resume; CI/review passed. |
| 81 | Complete | Parallel Branches and Joins |
| 82 | Complete | Immutable LLM settings, bounded schema repair, usage accounting and quality revisions; implementation/fix CI and review passed. |
| 83 | Complete | Published sales/baseline templates, durable starts, compatibility reads and delegated controls; fix CI/review passed. |
| 84 | Complete | Customer Feedback Template Migration |
| 85 | Complete | Incident templates and durable evaluations; 577 API tests, all CI and review passed. |
| 86 | Complete | Versioned tenant tools, worker credentials, fenced effects and explicit reconciliation; implementation and fix CI passed. |
| 87 | Complete | Governed HTTP tool, pinned destination policy, bounded transport and safe effect recovery; fix CI passed. |
| 88 | Complete | Registered tenant data queries, restricted read-only roles, bounded async transport, worker receipts and fixture evidence. |
| 89 | Complete | Configured issue reads/approved creation, durable correlation and backoff, ambiguity recovery and fixture evidence. |
| 90 | Complete | Pinned LLM tools, durable continuation, exact approval, bounded budgets, recovered usage and ledger trace linkage. |
| 91 | Complete | Signed, scoped webhook triggers; atomic replay-safe starts, rotation and retained delivery history. |
| 92 | Complete | Scoped cron schedules, explicit DST rules, atomic replica-safe firing, bounded catch-up and crash recovery. |
| 93 | Complete | Generic workflow draft builder, typed node forms and conflict-safe editing. |
| 94 | Complete | Revision-bound publication, immutable history/diffs, idempotent manual starts and masked trigger controls. |
| 95 | Complete | Immutable graph debugger, paginated traces, bounded detail and historical compatibility; 850 API tests and all CI green. |
| 96 | Complete | Safe linked recovery, fresh approvals, preserved effects/budgets, scoped controls; implementation `9524627`, CI `35165725922` passed. |
| 97 | Complete | Scoped worker metrics and bounded live updates; implementation `202adc1`, fix `f73d4a1`, all CI passed with 874 API tests. |
| 98 | Complete | 10,000 workflows, 33,333 jobs and 3,333 sink effects reconciled; implementation `450c8c4`, CI `35177537976` passed. |
| 99 | Complete | 45 fault experiments and 15 fix checks reconciled; implementation `8d45828`, fix `bfe6c73`, CI `35181619634` passed all 891 API tests. |
| 100 | Complete | Production images and authenticated deployment; 11 runs/207 jobs including two active drains; implementation `d7d172c`, CI `35188845395` passed 896 API tests. |
| 101 | Complete | Authenticated kind deployment, migration, approval/PVC persistence and metrics; implementation `918db61`, CI `35195207152` passed 896 API tests. |
| 102 | Complete | Local rollout, scaling, Pod loss/fencing, readiness, backup/restore and rollback; 21 runs/21 effects reconciled; implementation `3c30652`, CI `35200997403` passed 898 API tests. |
| 103 | Complete | Implementation `242c611`, fix `39b8f4f`; CI `35205261374` and `35207650946` passed 898 API tests; documentation review resolved. |
| 104 | Complete | Rehearsed script; implementation `677c6bb`, fixes `9133592`/`7055664`; all CI and review passed, 906 API tests. |
| 105 | In progress | Final case study, requirement checklist and complete delivery review. |

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

### Phase 80 — Durable Approval Steps and Resume (2026-09-15)

- Dependency gate: Phase 79 record `7af753ebdab27ca7f02a3d588ada216daa276d9a`
  pushed; [CI run 35026486138](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35026486138)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected existing approval review/issue contracts, actor/audit and high-severity
  permission checks, generic wait/continuation semantics, iteration identity and
  the Phase 82 boundary for upstream LLM quality-revision execution.
- Plan: persist tenant-owned approval snapshots bound to version/node/iteration
  and hashes of governed input plus candidate output/review. Registration releases
  the worker. Approve/reject/edit/request-retry decisions serialize on the run,
  enforce current membership/scopes, and append actor evidence. Edits supersede
  old approvals; changed governed input invalidates stale snapshots. Accepted
  decisions enqueue one continuation atomically; retries create a bounded new
  approval iteration, separately from infrastructure attempts. Upstream revision
  subgraphs remain Phase 82 scope.
- Acceptance: concurrent conflicting decisions/cancellation, identical replay,
  rollback/no duplicate resume, restart while waiting, stale payloads, edited
  outputs, rejection, review retry exhaustion, expiry and high-severity overrides,
  role/revocation/service scopes and cross-tenant access.
- Rollout: additive approval records with tenant FKs, pending uniqueness and
  history guards. Restart API/workers before publishing approval graphs; legacy
  approvals remain readable and their endpoints retain existing behavior.
- Implemented immutable approval snapshots and revision history, tenant-scoped
  reads and minimal decision acknowledgements, current-role/high-severity checks,
  superseding edits, stale-input invalidation, and atomic approve/retry resume.
  Approval registration releases workers; cancellation and deadline/expiry close
  pending approvals. Review retries preserve feedback/candidate edits and use a
  new logical approval iteration with a fresh infrastructure attempt budget.
- Initial validation: seven lifecycle tests passed. The expanded suite passed
  20 tests with one invalid service-role fixture; corrected the fixture to assert
  the existing prohibition on service reviewer/admin roles. All nine focused
  role/revocation/service-scope cases then passed. Pre-commit review reproduced
  and fixed a local-runner receipt collision; that handoff regression passed.
  A separate regression verifies execution/step IDs participate in approval hashes
  even for identical versions and payloads. Migration upgrade, Ruff, Compose
  config and diff checks passed.
- Scope/limitations: immutable snapshots, migration guards, four decision paths,
  expiry processing and concurrency/security tests require more than 700 lines
  together; they remain one Phase 80 delivery unit. Approval inputs carry a
  `payload` and the existing structured `review` shape; approved outputs use the
  pinned node output schema. Edits retain reviewer issues and cannot bypass high
  severity. Phase 80 retries re-register bounded approval iterations; upstream
  reviewer/LLM subgraph revisions are explicitly Phase 82. No live provider or
  hosted deployment was performed.
- Final validation:
  `uv run --directory apps/api pytest tests/test_execution_approvals.py tests/test_execution_cancellation.py tests/test_durable_delays.py tests/test_durable_queue.py tests/test_worker_leases.py tests/test_retry_runtime.py tests/test_graph_interpreter.py tests/test_permissions_audit.py -q --tb=short`
  passed **131 tests** against disposable PostgreSQL. The approval-only rerun
  passed **25 tests**. Final pre-commit review added a locked fresh read of governed
  step inputs; its cached-session stale-input regression passed separately.
  `ruff check src tests alembic/versions/f080_execution_approvals.py`, migration
  upgrade, Compose config and `git diff --check` passed. The existing upstream
  TestClient/httpx deprecation warning is non-blocking. PostgreSQL migration
  tests exercised empty downgrade/reapply, old-run compatibility, immutable
  snapshot/decision guards, edit/approve transitions and retention refusal.
- Implementation commit: `e803bb5d888057a1ade96bcbda7ca9105ec5dcac`, pushed to main.
  [CI run 35029277139](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35029277139)
  passed API, Web and Docker Compose, including full API tests and dependency audits.
- Post-push review checked run/step/version/hash binding, refreshed governed inputs
  under lock, permission/revocation and high-severity enforcement, service-role
  restrictions, idempotent/conflicting decisions, superseded edits, expiry/cancel
  ordering, bounded review iterations, queue receipt settlement, rollback and
  migration/history compatibility. Existing legacy approval endpoints are unchanged.
  No actionable blocking findings; no separate fix commit required.
- Completion: Phase 80 complete. Final record is pushed separately; finish its CI
  before starting Phase 81. This phase changes 1,422 lines including migration,
  immutable snapshot model, decision runtime and 574 lines of focused acceptance
  tests; the scope remains approval lifecycle only. No live provider or hosted
  deployment claimed.

### Phase 81 — Parallel Branches and Joins (2026-09-15)

- Dependency gate: Phase 80 record `2a2756451649930fdf04f954eb85ac5eba6c0b8f`
  pushed; [CI run 35029941182](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35029941182)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected validated fork/join regions and branch bindings, single-active-job
  assumptions, global revision fences, durable waits, approval retry checkpoints,
  deadline/cancellation and recovery ownership.
- Plan: assign stable nested branch paths and persist node/iteration job targets.
  Schedule ready branch work and joins under the run lock; use per-attempt and
  claim ownership for parallel result commits so siblings do not invalidate one
  another. Keep worker capacity/fan-out bounded. Join inputs explicitly bind branch
  outputs and produce deterministic named output; skipped routes settle before
  joins. Integrate branch waits, targeted retry/recovery, fail-fast sibling
  cancellation, run deadlines and immutable branch traces.
- Acceptance: out-of-order/simultaneous completion, one join under replay,
  conditional skips and nested forks, delay/approval waits within branches,
  cancellation/failure/deadline propagation, crash/recovery without sibling
  overwrite, malformed region/binding rejection and worker capacity limits.
- Rollout: additive job target fields and revised active-job uniqueness; stop old
  workers before migration/restart. Preserve linear receipts and pinned runs.
  Retention guards prevent dropping active parallel history. Parallel graphs run
  through durable workers; the local deterministic helper remains for linear
  graphs. The scheduler, lifecycle integration and real concurrency fixtures may
  exceed 700 lines as one phase-scoped delivery unit.
- Implemented stable branch paths, persisted fork/join checkpoints and independently
  targeted node/iteration jobs. Scheduling and join creation share the execution
  lock; parallel completion uses the live claim/attempt fence and current run state.
  Delay/approval waits, infrastructure and human retries, cancellation, deadlines
  and recovery now preserve independent siblings and fail unfinished work together.
  Added queue/runtime documentation and migration `f081_parallel_jobs`.
- Local validation (disposable PostgreSQL): all 19 new parallel cases passed across
  focused runs in `test_parallel_runtime.py` and `test_parallel_recovery.py`,
  including real branch process kill/recovery and migrated history. Two initial
  fixture errors (approval request field and raw SQL job status) were corrected
  and affected cases rerun successfully. Broader command
  `uv run --directory apps/api pytest tests/test_workflow_graph.py tests/test_graph_interpreter.py tests/test_durable_queue.py tests/test_worker_leases.py tests/test_retry_runtime.py tests/test_execution_cancellation.py tests/test_durable_delays.py tests/test_execution_approvals.py -q --tb=short`
  passed **140 tests**. Ruff (`src tests` and the migration), `alembic upgrade head`,
  Compose configuration and `git diff --check` passed. Existing upstream TestClient
  deprecation warning remains; no provider or hosted deployment was performed.
- Scope size: approximately 1,350 changed lines, including 649 test lines. The
  scheduler, node ownership migration and lifecycle integrations form one phase;
  concurrency, recovery and rollback evidence are kept with that implementation.
- Pre-push review checked lock order, live attempt/claim fencing, unique joins,
  deterministic bindings/skips, retry targeting, wait release, terminal history,
  tenant scoping and linear compatibility. No unresolved finding.
- Implementation `23a19c2346e9961f6422bb030feb3677172fdc3d` pushed to main;
  [CI run 35032721841](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35032721841)
  passed API, Web and Docker Compose, including full API tests, migrations,
  dependency audits and frontend lint/typecheck/smoke/build.
- Post-push review confirmed the implementation satisfies Phase 81: run-first lock
  order and claim/attempt ownership, unique join scheduling after selected/skipped
  routes settle, independent branch retries and recovery, released wait slots,
  sibling cancellation, immutable migrated history and preserved linear behavior.
  No actionable findings or fix commit. Phase 81 is complete; Phase 82 becomes
  eligible after this final record is pushed and its CI passes. No external
  providers or hosted deployment were exercised. Parallel execution requires
  upgraded durable workers; existing retention and at-least-once I/O limits apply.

### Phase 82 — LLM Executor and Bounded Quality Revisions (2026-09-15)

- Dependency gate: Phase 81 record `ea64f978d1fab7466bf00d007e645f9bf067f9c3`
  pushed; [CI run 35033116582](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35033116582)
  passed API, Web and Docker Compose. Working tree clean.
- Inspected prompt publication snapshots, agent settings resolution, structured
  output guardrails, provider timeout/retry options, cost estimates, generic
  attempts/events, targeted jobs and approval payload/retry fencing.
- Plan: pin per-node runtime configuration at acceptance, including published
  prompt, explicit or selected agent settings, schemas and pricing estimates.
  Add a generic LLM executor using the existing client with SDK retries disabled,
  bounded schema repair, abort/deadline handling and accounting for every returned
  provider response. Persist usage/cost/repair metadata with fenced attempts/events.
- Quality revisions: explicitly declare the entry-to-review region and its human
  escalation approval. Track quality iteration and feedback independently of
  infrastructure attempts; restart only the declared region, re-evaluate its
  continuation, preserve sibling/prefix outputs and invalidate superseded approvals.
  Route exhausted or non-retryable quality failures to the declared human gate;
  downstream writer bindings consume approved/human-edited outputs.
- Acceptance: provider fixtures cover schema repair/failure, usage, SDK retry
  coordination, timeout/abort, immutable paused-run settings, quality bounds,
  re-review, stale approval rejection and approved writer inputs. No paid calls
  or new credentials are required for automated validation.
- Rollout: additive immutable execution configuration snapshot; old deterministic
  runs retain empty snapshots. Update workers together with migration. Keep
  legacy business APIs working; template migration belongs to Phases 83–85.
  The LLM, revision lifecycle and regression fixtures may exceed 700 lines as one
  complete phase.
- Implemented immutable run configuration with ORM/SQL guards and migration
  `f082_execution_config`; opt-in agent settings resolution; generic LLM execution
  through the existing provider client; bounded JSON/schema/reviewer repair;
  typed provider failures, abort/timeout handling and per-response usage/cost events.
  Added targeted quality iterations, bounded human retries, forced escalation,
  preserved feedback/edits and independent sibling/prefix history. Runtime and
  rollout details are in [LLM execution](LLM_EXECUTION.md).
- Local validation used disposable PostgreSQL and credential-free provider fixtures:
  `pytest tests/test_execution_config.py tests/test_graph_interpreter.py tests/test_workflow_definitions.py tests/test_execution_starts.py -q --tb=short`
  passed **32 tests** after correcting a test schema import. The broader command
  `pytest tests/test_workflow_graph.py tests/test_durable_queue.py tests/test_worker_leases.py tests/test_retry_runtime.py tests/test_execution_cancellation.py tests/test_durable_delays.py tests/test_execution_approvals.py tests/test_parallel_runtime.py tests/test_parallel_recovery.py tests/test_quality_revisions.py tests/test_llm_execution.py tests/test_execution_config.py -q --tb=short`
  passed **167 tests**. Final focused LLM/quality/settings/client/guardrail validation
  (`test_llm_execution.py test_quality_revisions.py test_agent_settings_api.py test_llm_client.py test_structured_output_guardrails.py`)
  passed **48 tests**; the additional impossible-review-schema rejection case
  passed separately. All pytest commands used `uv run --directory apps/api`.
  Ruff, `alembic upgrade head`, Compose configuration and diff checks passed.
  Existing TestClient deprecation warning remains. No paid provider request,
  credential change or hosted deployment was performed.
- Pre-push review checked configuration pinning, tenant-scoped settings, provider
  schema compatibility, SDK/engine retry separation, returned usage preservation,
  terminal fencing, iteration bounds, human-edited writer input and retained
  migration history. Hardened reviewer contract validation before provider I/O.
  No unresolved finding. Approximately 1,600 changed lines include more than 680
  new test lines; provider execution, quality lifecycle and their evidence remain
  one phase-scoped unit.
- Implementation `303a7eb1f3d900e1c33f52fca0bd9587f6af628c` pushed to main;
  [CI run 35035588150](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35035588150)
  passed API, Web and Docker Compose, including full API tests and audits.
- Post-push review found two edge cases: a setting inserted after the initial
  settings read could change a later node in the same acceptance, and an unrelated
  route could enter the quality policy's approval without its reviewer. Fixes pass
  the complete settings snapshot (including absence) into existing resolution and
  reject unrelated incoming routes to the quality approval. Independent-session
  insertion and malformed-gate regressions cover both findings.
- Fix validation: `uv run --directory apps/api pytest tests/test_execution_config.py tests/test_quality_revisions.py tests/test_agent_settings_api.py -q --tb=short`
  passed **16 tests**; Ruff and diff checks passed.
- Fix `d0fb0d40cd79a1e0086ad9b323eba6e776ca62c0` pushed to main;
  [CI run 35035996529](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35035996529)
  passed API, Web and Docker Compose. Follow-up review verified that missing
  settings remain absent for the whole acceptance, legacy settings callers retain
  their default behavior, and direct/conditional quality gates exclude unrelated
  predecessors. Regression coverage matches both findings; no blocking issue remains.
- Phase 82 is complete. Phase 83 becomes eligible after this final record is
  pushed and its CI passes. Repeated quality regions exclude waits and external
  effects; abrupt process death can leave remote usage unknown. No live provider
  call or hosted deployment is claimed.

### Phase 83 — Sales Workflow Template Migration (2026-09-15)

- Dependency gate: Phase 82 record `1aec42fcba51a2adcd59f8a3e31dc077841a1671`
  pushed; [CI run 35036368896](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35036368896)
  passed API, Web and Docker Compose. Working tree clean before this plan.
- Inspected sales agents/prompts, mandatory human approval, legacy run/step/cost
  readers, evaluation promotion, durable starts and immutable execution links.
- Plan: publish tenant-owned sales multi-agent and one-step baseline templates;
  reuse sales schemas and prompts, pin graph revision bounds, and preserve the
  mandatory human gate. Route new sales API starts to durable jobs. Materialize
  compatibility records inside the execution transaction so existing pages,
  comparisons and evaluation links retain their run IDs. Legacy controls reject
  migrated runs; cancellation and approval actions delegate to the durable engine.
- Acceptance: fixture-driven success, edits, rejection, retry exhaustion, baseline,
  costs, final output and evaluation links; duplicate-control and stale-approval
  rejection; historical reads and tenant isolation. Check migration, focused API
  regressions, Web typecheck/smoke and all CI jobs, then review the pushed change.
- Rollout: install published templates with an authorized admin operation before
  new sales starts; update API/workers together. An explicit backout setting affects
  only future starts; accepted durable runs retain their execution owner. Add a
  unique legacy/execution link without rewriting historical runs. Shared evaluation
  orchestration migration completes in Phase 85; this phase preserves its readers.
  The compatibility layer and parity fixtures may exceed the suggested commit size.
- Implemented admin-installed published sales/baseline graphs, durable sales API
  starts, unique immutable execution ownership, atomic read projections, delegated
  approval/cancellation and legacy duplicate-control rejection. Updated Web forms
  to carry approval hashes and follow replacement IDs. Added registered final-report
  validation, explicit sales quality retry options and approved feedback propagation.
  Compose now supplies the configured provider key to workers and exposes the
  future-start backout flag. Provider construction unwraps the secret value; its
  regression uses a dummy key. See [business templates](BUSINESS_TEMPLATES.md).
- Validation on disposable PostgreSQL with provider fixtures:
  `uv run --directory apps/api pytest tests/test_sales_template.py tests/test_workflow_runs_api.py tests/test_sales_workflow_integration.py tests/test_human_approvals_api.py -q --tb=short`
  passed **32 tests**. The final overlong-approval-body regression passed separately.
  `uv run --directory apps/api pytest tests/test_quality_revisions.py tests/test_llm_execution.py tests/test_execution_config.py tests/test_execution_approvals.py tests/test_workflow_transactions_postgres.py tests/test_sales_analyst_api.py tests/test_sales_reviewer_api.py tests/test_sales_writer_api.py tests/test_sales_baseline_api.py tests/test_evaluation_runner.py tests/test_evaluation_promotion_api.py tests/test_evaluation_comparisons_api.py tests/test_cost_tracking.py -q --tb=short`
  passed **135 tests**. Sales plus role-matrix checks passed **13 tests**; concurrent
  installation and migration ownership checks passed **2 tests**; provider-factory
  and output-validator contract checks passed **2 tests**. These focused runs overlap.
  Initial failures exposed legacy test doubles and installation audit expectations;
  adapters retain the domain-double path, legacy start tests explicitly exercise
  backout, and role tests separate setup publication records from tested actions.
- `pnpm --dir apps/web typecheck` and `pnpm --dir apps/web test:smoke` passed
  (**11 smoke tests**). Ruff, `alembic upgrade head`, Compose configuration and
  `git diff --check` passed. Existing TestClient deprecation warning remains.
  No live provider request, credential modification or hosted rollout was performed.
- Pre-push review checked mandatory approval, stale edit/decision protection,
  single execution ownership, idempotent costs, immutable source history, rollback
  safety, tenant authorization, concurrent installation and historical comparisons.
  The compatibility and parity coverage forms one phase-scoped change; commit size
  exceeds the suggested range. Implementation push, CI and post-push review pending.
- Implementation `d80ade2b2274130a2f4fadbcb2a4f15c59bc4536` pushed to main.
  [CI run 35038501298](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35038501298)
  passed Web and Docker Compose; API reported **545 passed, 1 failed**. The remaining
  legacy start-event fixture needed the explicit backout setting. Post-push review
  also found that queued sales starts should expose their compatibility start event
  immediately, before a worker first polls. The fix projects acceptance atomically
  and maps the initial generic event to `workflow_started`; an API regression checks
  the event before worker execution. No other blocking review finding. The phase
  remains in progress pending fix validation, push, CI and follow-up review.
- Fix validation: `uv run --directory apps/api pytest tests/test_workflow_events.py tests/test_sales_template.py -k 'workflow_events or api_start or acceptance_projection' -q --tb=short`
  passed **7 tests**, including injected projection failure rolling back both run
  records and the durable job. The preceding broader start/sales/event run passed
  25 cases and exposed an overly strict new event assertion, corrected to allow the
  existing queued-job event while requiring exactly one start event. Ruff and diff
  checks passed. The fix is limited to acceptance projection and event fixtures.
- Fix `08f02de2c274e0c044cd95a7b61dfc6399299c79` pushed to main;
  [CI run 35039151726](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35039151726)
  passed API, Web and Docker Compose, including the complete API suite and audits.
  Follow-up review verified that acceptance projection is inside the same commit
  as both run records and the queue receipt, start events appear once, and the
  legacy event fixture explicitly selects backout. No blocking finding remains.
- Phase 83 is complete. Implementation size was 1,281 changed lines, including
  410 new test lines and the compatibility layer; the separate fix remains scoped
  to acceptance events. Template installation is required per organization, and
  existing durable runs retain their owner during backout. Shared evaluation/demo
  orchestration migration remains Phase 85 scope. No live-provider parity or hosted
  deployment is claimed. Phase 84 follows this final record's push and successful CI.

### Phase 84 — Customer Feedback Template Migration (authorized 66–105)

- Dependency gate: Phase 83 record `47efc47b5cc2115dac7ea4152bc6a5be39ac241d`
  is pushed; CI 35039507488 and all commit checks passed (API, Web, Docker Compose).
- Plan: reuse the sales template installation/start and compatibility mechanisms;
  publish feedback classifier → insight → reviewer → approval → writer plus a
  single-step baseline. Keep existing normalization, prompts, output models and
  supporting evidence. Repeat classifier/insight/reviewer together on bounded
  quality revisions; consume only current-iteration outputs. Validate generated
  output and human edits against existing semantic models before acceptance.
- Acceptance: provider-fixture success/edit/rejection/retry/baseline parity,
  fresh worker resumption, current classifier-to-insight bindings, invalid edits,
  CSV API starts, duplicate legacy controls, historical reads and evaluation checks.
- Rollout: per-organization admin installation; new feedback starts use the
  durable owner by default, with a future-start backout flag. Existing rows remain
  readable and retain their owner. No schema migration or live provider is needed.
  Shared evaluation/demo orchestration remains Phase 85.
- Implemented published feedback graphs, shared tenant-serialized installation and
  start helpers, default durable feedback starts and a documented backout flag.
  Sales keeps its template IDs and fallback prompt names. Reused feedback models
  as registered output/approval validators; pinned task instructions preserve
  evidence and report guidance. Added old/new provider-fixture parity and worker
  resumption coverage. No schema migration or frontend component change is needed.
- `uv run --directory apps/api pytest tests/test_feedback_template.py -q --tb=short`
  passed **9 tests**. The initial run passed 6 and failed one new retry assertion
  that named the existing context field incorrectly; it was corrected. Coverage
  includes equal old/new outputs, decisions and observed usage; revised classifier
  dependencies, bounded quality exhaustion, human feedback, invalid edit rollback,
  strict nullable provider schemas, CSV starts, cancellation and legacy backout.
- `uv run --directory apps/api pytest tests/test_customer_feedback_schemas.py tests/test_customer_feedback_classifier_api.py tests/test_customer_feedback_insight_api.py tests/test_customer_feedback_reviewer_writer_api.py tests/test_uploaded_inputs_api.py tests/test_human_approvals_api.py tests/test_evaluation_runner.py tests/test_evaluation_comparisons_api.py tests/test_evaluation_promotion_api.py tests/test_quality_revisions.py tests/test_workflow_graph.py -q --tb=short`
  passed **112 tests**. Existing TestClient deprecation warning remains.
- Web typecheck and **11 smoke tests**, Ruff, Compose configuration and diff checks
  passed. Constructing both modes of both published graph types passed after moving
  the unchanged reference helper into the shared schema module.
- `uv run --directory apps/api pytest tests/test_feedback_template.py tests/test_sales_template.py tests/test_execution_approvals.py tests/test_permissions_audit.py tests/test_workflow_runs_api.py -q --tb=short`
  passed **86 tests** (overlaps the feedback run above). This run used the original
  seven feedback cases; the final nine-case run includes the subsequent quality
  exhaustion and provider schema assertions. No test process remains running.
- Pre-push review checked graph dependencies, retained schema semantics, mandatory
  approval, invalid edit atomicity, source normalization, compatibility ownership,
  and preserved sales installation behavior. Corrected feedback definition labels
  in the shared installer and added a regression assertion. Provider schemas require
  every property, including nullable source fields. No live-provider or hosted
  rollout claim.
- Implementation `dd846c0681f86e73716f211cf8ec69477fefb8b1` pushed to main.
  [CI run 35041028754](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35041028754)
  passed API, Web and Docker Compose, including the full API suite and dependency
  audits. Post-push review verified current-iteration bindings, frozen template
  configuration, semantic repair and edit validation, mandatory approval, tenant
  installation locks, shared acceptance rollback and retained control ownership.
  No blocking findings or separate fix commit were required.
- Phase 84 is complete. The 1,049 changed lines include 349 test lines and moving
  shared installation/schema helpers out of sales; all changes serve feedback
  migration and compatibility. Existing prompts and source normalization remain
  supported. This is provider-fixture evidence, not live-provider parity or a
  hosted rollout. Phase 85 follows the final record's push and successful CI.

### Phase 85 — Incident Template and Evaluation Compatibility (authorized 66–105)

- Dependency: Phase 84 record `ae8ffe5a4e470c0cc31fd16d4c90a052b6bafc3c`
  is pushed and CI 35041373284 passed API, Web and Docker Compose.
- Plan: publish timeline → root cause → reviewer → approval/revision → writer
  and incident baseline graphs using existing prompts, normalization and semantic
  models. Repeat timeline/root-cause/review together, preserving ambiguity and
  confirmed/inferred distinctions. Switch new incident starts with a backout flag.
- Complete evaluation integration by accepting durable work promptly, recording
  pending results atomically with queued runs, and scoring from committed terminal
  projections. Preserve administrator-authorized evaluation auto-approval with a
  recorded initiator and a fresh permission check at decision time; clearly label
  those decisions. Promotion/correction paths return queued run links and retain
  same-source comparisons. Historical results remain readable.
- Demo integration: install templates for fresh execution from seeded inputs;
  retain explicitly synthetic historical fixture histories and scores without
  fabricating versions. Prevent reseeding from overwriting durable-owned records.
  Compatibility readers remain the single representation for business costs and
  traces. Document legacy agent endpoint deprecation and asynchronous evaluation.
- Acceptance: incident fixture parity (success, ambiguity, edits, rejection,
  retry, cancellation, baseline); durable evaluations for all three workflows,
  same-input deterministic scoring, pending/terminal recovery, revoked initiator
  authorization, historical comparisons and demo reseed safety. Broaden API/Web
  regressions after shared changes. Add only the evaluation policy metadata/schema
  needed for durable automation; no live provider or hosted deployment is planned.

- Implementation: published incident graphs with registered semantic schemas,
  current-iteration timeline bindings, mandatory approval, bounded revisions and
  baseline; default durable starts with `INCIDENT_TEMPLATE_ENABLED` backout.
  Shared evaluations atomically enqueue results/run/jobs, persist immutable admin
  delegation, reauthorize decisions, and score committed terminal projections.
  Router diagnostics are pinned and their observed usage is included. Promotion
  serializes duplicate requests and keys provenance to the original uploaded input;
  correction queues source text with explicit reviewer guidance. Demo installation
  preserves synthetic historical records and excludes durable-owned runs from reseeds.
  Eight legacy agent endpoints are deprecated in OpenAPI. Historical readers remain.
- Migration: `f085_durable_evaluations` adds requester/policy fields, an execution
  lookup index and immutable-policy/binding trigger. Pending automatic evaluations
  block downgrade. Fresh disposable `phase85_validation` database successfully ran
  `uv run --directory apps/api alembic upgrade head` and `alembic current` reports
  `f085_durable_evaluations (head)`. No application database was migrated.
- Local validation: initial durable evaluations 5 passed; incident/legacy evaluation,
  promotion/comparison/demo/router/CLI regression group 38 passed; automation,
  execution-record and tenant isolation group 20 passed; automation plus migration
  group 7 passed. Latest automation group (including independent-upload provenance)
  7 passed; correction queue test 1 passed; incident normalization/deprecation/API
  no-provider-key test 1 passed; final migration test 1 passed. The latter API test
  first exposed an invalid test fixture (`None` instead of an empty `SecretStr`);
  correcting the fixture made it pass. Earlier promotion JSON-null and old-schema
  fixture failures were fixed and their affected suites passed.
- `uv run --directory apps/api ruff check src tests
  alembic/versions/f085_durable_evaluations.py`, Web typecheck, 11 Web smoke tests,
  Compose configuration and `git diff --check` passed. An explicit-file full API
  run was interrupted after output inactivity; a verbose explicit-file run is
  still in progress and is not claimed as passing. CI will run the full suite.
- Scope size exceeds the usual target because this phase closes three workflow
  evaluation paths, atomic queue/result persistence, revocable approval delegation,
  migration/history compatibility, incident graphs and real-PostgreSQL regression
  coverage together. No later-phase tools, triggers or builder UI are included.
- Pre-commit review covered control ownership, immutable policy, revoked membership,
  concurrent promotion, approval restart/idempotency, cancellation, scoring lock
  ordering and compatibility costs. Remaining evidence boundary: fixture provider
  responses only; no live-provider equality or hosted deployment is claimed.
  Implementation `31b4879c0da7e0614958bb9557e67aad2a9674b7` is pushed to main;
  CI [35044572077](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35044572077)
  passed API, Web and Docker Compose, including the full API suite and dependency
  audits. Phase 85 remains open for the separate review fix.
- Post-push review found a backout edge case: accepting queued evaluations without
  an API provider key is correct, but selecting legacy evaluation must reject a
  missing key before creating evaluation records. The fix adds that preflight to
  both legacy runner and promotion entry points, with a 503 API regression. It also
  removes trailing blank lines caught when newly added files entered the staged
  diff check (the earlier unstaged check did not include untracked files).
  Affected incident API, evaluation runner and promotion tests: 15 passed. Ruff
  and the complete fix diff check passed.
- Fix `7d4f9766d535f770ba6b2bdd7708cfa630df6a4f` is pushed to main.
  [CI 35044958344](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35044958344)
  and every check on that commit passed: API (**577 tests**), Web and Docker Compose,
  including fresh migration and dependency audits. Follow-up review found no
  additional blocking issue. The implementation CI also passed **577 tests**.
  The redundant local verbose full run was stopped after the CI pass; neither
  interrupted local full run is claimed as passing. Focused local results above
  remain valid. Existing TestClient deprecation warning is unchanged.
- Phase 85 is complete: 1,966 implementation changed lines (including 716 new test
  lines) plus the scoped review fix. No hosted deployment or live provider check
  was performed. Phase 86 follows this completion record's push and successful CI.

### Phase 86 — Tool Contracts Credentials and Effect Ledger (authorized 66–105)

- Dependency: Phase 85 final record `e6a543109c1a3fef22a404e871f98b9ee675169d`
  is pushed; CI 35045407019 and all commit checks passed.
- Inspected the consolidated R07/R08 requirements, graph tool placeholder, tenant
  ORM/composite foreign keys, publication/permission/audit services, execution
  identities and durable worker claim fences. Existing tools remain non-executable
  until an adapter is registered; this phase adds the shared foundation.
- Plan: persist tenant-owned tool definitions, immutable numbered contracts,
  revocable credential references and redacted tool execution/effect records.
  Admin APIs manage contracts/references and explicitly resolve uncertain effects.
  Credentials are worker configuration values addressed by tenant/alias; no secret
  is stored in a graph, contract or trace. Resolve only for a live owned worker
  attempt and recheck revocation before dispatch; audit each use.
- Effect acceptance binds a logical step/call identity to a canonical request
  fingerprint. Concurrent duplicates share a ledger; changed arguments conflict.
  Persist the dispatch boundary before I/O, fence outcomes with a reservation token,
  and distinguish definite failure from possible remote acceptance. Registered
  adapters must provide idempotency or reconciliation to recover ambiguous writes;
  otherwise require explicit operator resolution. No local exactly-once claim.
- Validation: real PostgreSQL version/tenant/credential tests, concurrent claims,
  crash-before/after-dispatch fixtures, changed-input conflicts, independent
  iterations, redaction and revoked credential checks. Additive migration with
  immutable contracts/history retention; preserve existing business/runtime data.
  HTTP, PostgreSQL and GitHub adapters and workflow dispatch integration follow
  in their own phases. No live external credential or service is required here.
- Implemented the catalog/reference APIs with admin permissions, immutable numbered
  contracts, tenant-qualified references and sanitized validation errors. Worker
  configuration is scoped by organization/alias. Credentials are rechecked before
  dispatch, audited without values, and bound to each effect with a private salted
  fingerprint to prevent replay under a rotated account credential.
- Added stable logical-call keys, argument/version fingerprints, serialized
  reservations, dispatch markers, token-fenced receipts, bounded retries, provider
  idempotency/reconciliation contracts and explicit admin resolution. Lost dispatches
  become unknown even when worker recovery is exhausted. Reconciliation proof is
  retained before another write; confirmed late receipts remain separate from
  cancelled workflow outcomes. Ledger locking preserves the prepared workflow
  revision. Timeouts use the smaller of the tool budget and pinned deadlines.
- Added `f086_tool_contracts` with four tables, tenant foreign keys and immutable
  contract/effect triggers. Fresh-schema upgrade/downgrade and old-data preservation
  passed. A real credential-backed fixture dispatch against Alembic-created tables
  passed; SQL attempts to alter confirmed output/credential binding or delete effect
  history were rejected. The disposable `phase85_validation` database upgraded to
  `f086_tool_contracts (head)`. No application database was migrated.
- Validation: `pytest tests/test_tool_effects.py tests/test_tool_catalog.py
  tests/test_tool_migration.py -q --tb=short` passed **30 tests** after the checkpoint
  revision fix. The subsequently added deadline-budget test passed separately;
  the expanded migrated-table dispatch test also passed. Earlier fixture runs
  passed 19, 10, 13 and 29 tests as coverage grew; these overlap, not additional
  unique tests. `pytest` with the exhausted-recovery effect test plus
  `test_durable_queue.py test_worker_leases.py test_permissions_audit.py
  test_api_surface.py` passed **54 tests**. The sanitized-error test with
  `test_api_surface.py test_security_controls.py` passed **7 tests**.
  All commands used `uv run --directory apps/api` and disposable PostgreSQL.
- Ruff (including the migration), Compose configuration and local diff checks
  passed. No frontend files changed. Reviewed effect uncertainty, claim ownership,
  late responses, revocation/rotation, tenant isolation, immutable history and
  compatibility with prepared checkpoints. This scope exceeds the usual line target
  because the shared security/recovery foundation, migration, API and real-database
  acceptance tests must be delivered together. Concrete external adapters remain
  unimplemented here, and no live external service/deployment claim is made.
  Implementation `12b9759bf06691ce40ce463f4242bc184028c77d` is pushed to main;
  [CI 35048012543](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35048012543)
  passed API, Web and Docker Compose, including fresh migration and dependency audits.
- Post-push review found a second-crash recovery gap: reserving an uncertain effect
  previously changed it to pending before reconciliation, losing the original
  uncertainty if the replacement worker died before dispatch. The fix retains
  unknown status through recovery reservation and blocks concurrent manual resolution
  while that reservation is live. A regression uses real lease recovery twice and
  proves the accepted write is reconciled without invoking it again. All **18 effect
  tests**, Ruff and fix diff checks passed.
- Fix `c661817754eeb57e407c357d4cc21252ec10d02c` is pushed to main;
  [CI 35048490433](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35048490433)
  and all commit checks passed: API (**609 tests**), Web and Docker Compose,
  including migration and dependency audits. Implementation CI passed **608 tests**.
  Follow-up review confirmed repeated recovery preserves uncertainty and live
  reservation fencing; no unresolved blocking findings remain.
- Phase 86 is complete. The implementation changed 1,963 lines, including 667 new
  test lines, followed by the scoped recovery fix. No external provider or hosted
  deployment was tested. Phase 87 follows this record's push and successful CI.

### Phase 87 — HTTP REST Tool (authorized 66–105)

- Dependency: Phase 86 completion record `e7479e94f25a5f27462684d86ad9f6373f617329`
  is pushed; CI 35048993851 and all commit checks passed.
- Inspected the effect ledger, durable dispatch/lease/cancellation boundary,
  publication and start validation, immutable approval snapshots and retry taxonomy.
  Reviewed Python HTTP/socket/TLS documentation and OWASP SSRF guidance.
- Plan: add a deny-by-default, tenant-scoped server destination policy and a
  schema-bound HTTP adapter. Restrict methods, paths, credentials, body/response
  bytes, DNS/connect/read time and redirects; validate all DNS addresses and connect
  directly to a vetted address with original-host TLS verification. Explicit private
  network exceptions cannot permit metadata/link-local addresses. No proxy or cookies.
- Integrate pinned tool contracts into publication/start validation and worker-only
  dispatch. Writes require an approved envelope naming the consumer node, tool,
  version and exact arguments. Recheck approval, revocation, ownership and deadlines
  before I/O. Bind effects to server policy as well as arguments and credentials;
  only configured provider guarantees permit ambiguous replay within retention.
- Acceptance: local HTTP fixtures for reads/writes, errors/rate limits, limits,
  redirects, DNS bypasses, TLS, cancellation and lost-response recovery. Real
  PostgreSQL tests exercise approval binding, tenant isolation, duplicate effects
  and durable worker integration. Broaden lifecycle/catalog/approval regressions.
- Rollout: no database migration; empty destination configuration disables all HTTP
  access. Existing contracts/history remain readable. No live external credential
  or hosted deployment is needed or claimed; later integrations stay out of scope.
- Implemented a tenant destination allowlist, fixed method/path contracts, protected
  credential headers, bounded DNS/connect/TLS/streaming transport, vetted-IP sockets,
  metadata/transition-address denial and bounded same-origin read redirects. Provider
  errors map to the shared retry taxonomy without retaining bodies or exception text.
  Absolute timeouts and cancellation close sockets; resolver concurrency is bounded.
- Connected catalog validation, immutable publication, starts and durable workers.
  Publication binds each tool node to the server policy fingerprint; changed policy
  requires republication and fresh approval. Writes recheck the exact approved node,
  version, arguments, source hash, expiry and current human reviewer authorization.
  Effect recovery pins policy/credentials and respects provider idempotency retention.
- Final local validation: `uv run --directory apps/api pytest tests/test_http_tool.py
  tests/test_http_tool_runtime.py tests/test_tool_effects.py -q --tb=short` passed
  **75 tests** against local HTTP/TLS fixtures and disposable PostgreSQL. Evidence:
  `.phase87-final-tests-2.log` (local ignored log). The cancellation test plus
  `test_tool_effects.py test_graph_interpreter.py test_workflow_definitions.py` passed
  **41 tests** (`.phase87-regression.log`). Earlier fixtures passed 36 transport tests
  and 13 worker tests; a cancellation fixture timing assumption was corrected to
  hold the response open. A later test-only missing import was fixed before the
  final 75-test pass. Existing TestClient deprecation warning is unchanged.
- Ruff, Compose configuration and the full staged diff check passed. Reviewed tenant
  boundaries, approval/policy binding, response ambiguity, DNS/TLS/redirect behavior,
  lifecycle fences and retained history. No frontend change or migration is needed.
  Scope exceeds the usual line target because the security transport, worker/catalog
  integration and 843 new fixture-test lines form one deployable adapter phase.
  Implementation `9029e5549fd9b4be50889f46a52c4f14d394710e` is pushed to main.
  [CI 35051088246](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35051088246)
  passed Web and Compose; API had **661 passed, 5 failed**. The five failures were
  existing fault-injection hooks receiving the new tool-only dispatch keyword on
  non-tool steps. The fix preserves their existing call path and supplies tool
  context only for tool work; the failing tests remain intact.
- Post-push review also found provider retention used the worker wall clock and
  HEAD responses were incorrectly subject to represented-body size limits. The
  separate fix uses PostgreSQL effect age plus monotonic elapsed time, preserves
  fail-closed handling for negative age, and treats HEAD as bodyless. ORM timestamp
  immutability now matches the existing SQL trigger. Tests cover clock rollback,
  HEAD metadata and immutable uncertain-effect timestamps. The HTTP, worker tool,
  effect, durable queue, retry and lease suites passed **107 tests** with
  `uv run --directory apps/api pytest tests/test_http_tool.py
  tests/test_http_tool_runtime.py tests/test_tool_effects.py tests/test_durable_queue.py
  tests/test_retry_runtime.py tests/test_worker_leases.py -q --tb=short`
  (`.phase87-fix-tests.log`). A final targeted retention/negative-age regression,
  Ruff and fix diff checks also passed.
  All five previously failing tests passed without weakening their assertions.
  Fix `7272ead2dd1ad6af523dc89b2086cd985c3e464a` is pushed to main;
  [CI 35052177161](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35052177161)
  and all commit checks passed: API (**667 tests**), Web and Docker Compose,
  including fresh migration and dependency audits. Follow-up review verified
  non-tool dispatch compatibility, database-based retention, HEAD semantics and
  immutable timestamps; no unresolved blocking findings remain.
- Phase 87 is complete. The implementation changed 1,754 lines (843 new test lines),
  followed by the scoped fix. All network evidence uses local HTTP/TLS fixtures;
  no live provider or hosted deployment was tested. Phase 88 follows this record's
  push and successful CI.

### Phase 88 — PostgreSQL Query Tool

- Authorized scope: Phases 66–105. Phase 87 completion record
  `a7ef748908b419e2f1714d27e92ade903e8f58e4` is pushed; all checks and
  [CI 35122976874](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35122976874)
  passed before implementation began. The worktree was clean.
- Plan: extend the existing catalog, pinned policy, worker credential resolution
  and effect ledger with a PostgreSQL read adapter. Only tenant-scoped, registered
  SELECT queries accept schema-bound parameters. Use a separate data database and
  restricted role, deny control database/user reuse, enforce read-only transactions,
  and bound connections, statement time, rows and serialized results. Cooperative
  polling must close connections on cancellation without exposing SQL or secrets.
- Acceptance: disposable PostgreSQL fixtures cover allowed reads, SQL parameter
  injection, write/DDL/multi-statement denial, restrictive roles, tenant boundaries,
  schema mismatch, revoked credentials, retries, timeouts, limits and cleanup.
  Review shared HTTP/catalog/worker compatibility and run affected regressions.
- Rollout: no migration or frontend change; empty server configuration disables
  access. Data credentials remain worker-only aliases. No live database credentials
  or deployment is needed or claimed; later GitHub/LLM integrations stay out of scope.
- Implemented tenant-scoped server connection/query registration, policy binding,
  separate read-only async libpq connections, restricted-role checks, parameter
  binding, bounded server cursor/JSON output, statement and total deadlines,
  cancellation cleanup and shared safe error mapping. Added operator documentation
  and Compose configuration; reused catalog, worker credentials and effect receipts.
- Local validation: `uv run --directory apps/api pytest tests/test_postgres_tool.py
  tests/test_postgres_tool_runtime.py tests/test_http_tool.py
  tests/test_http_tool_runtime.py tests/test_tool_effects.py tests/test_tool_catalog.py
  -q --tb=short` passed **125 tests** in 327.92s (`.phase88-regression.log`).
  A final transport run after tightening column/sequence and system-schema checks
  passed **29 tests**, including two additional handshake/privilege regressions
  (`.phase88-transport-final.log`). All tests used disposable local PostgreSQL and
  HTTP/TLS fixtures. The existing TestClient deprecation warning is unchanged.
- The initial transport run passed 26 tests. The initial worker run had 6 passed
  and 3 failed because its revocation test hook also intercepted control-database
  connections. The hook now targets only the data adapter; all worker cases passed
  in the final regression run. No production behavior was weakened for the fixture.
- Ruff, Compose configuration and the staged diff check passed. Local review
  covered query/tenant boundaries, privileges, byte/row/deadline limits, cleanup,
  credential revocation, retry effects, schema validation and HTTP compatibility.
  The phase exceeds the usual line target because 553 new test lines accompany
  one bounded transport, its security policy and operator documentation.
- Implementation `84c659c5d33e5fcfb4eaa483baf4dc10cea29b58` is pushed to main
  (1,015 changed lines, including 553 new test lines).
  [CI 35125600075](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35125600075)
  and every commit check passed: API (**705 tests**, existing TestClient warning),
  Web and Docker Compose, including fresh migration and dependency audits.
- Post-push review verified registered SQL versus bound scalar values, separate
  data/control credentials, tenant and pinned-policy checks, role privileges,
  read-only transaction enforcement, bounded cursor transfer, cancellation cleanup,
  redacted errors/receipts, retry behavior and existing HTTP compatibility. No
  actionable blocking findings or fix commit were needed. Fixture cleanup was
  verified: no Phase 88 data databases or roles remained on the disposable service.
- Phase 88 is complete. No production data source, external credential, hosted
  deployment or production TLS endpoint was exercised. Operator-owned queries and
  grants remain part of the trust boundary, and server resource sizing/OS-dependent
  disconnect detection are documented. Phase 89 follows this record's push and CI.

### Phase 89 — GitHub SaaS Tool

- Authorized scope: Phases 66–105. Phase 88 evidence record
  `4365780aa4d0028bde3e08f9cfa20d984a1413a5` is pushed and all checks in
  [CI 35126478047](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35126478047)
  passed before this phase began. The worktree was clean.
- Plan: reuse the bounded HTTP transport, tenant catalog, credential resolution,
  exact human approval and effect ledger for configured GitHub repositories. Add
  bounded issue reads and approved creation; bind repository/operation policy and
  expected author. Persist a credential-bound correlation marker before dispatch,
  reconcile uncertain creation through bounded reads, and require operator resolution
  when no unique matching receipt can be established. Never replay an ambiguous POST.
- Preserve provider rate-limit delays in effect metadata and durable retry timing,
  including worker recovery. Keep response headers/errors private and retain only
  validated issue fields and safe execution metadata. Use server-owned HTTP hooks;
  workflow inputs cannot alter endpoints, headers, credentials or marker identity.
- Acceptance: local provider fixtures and real PostgreSQL worker tests cover reads,
  pagination/limits, approved and denied creation, credentials, tenant policy,
  rate limits, redaction, lost responses, restart and ambiguous reconciliation.
  Broaden HTTP/effect/retry/approval regressions and review the pushed change.
- Rollout: empty repository configuration denies GitHub calls. Reuse existing JSON
  effect metadata without a schema migration. Document an optional live sandbox
  check and its credential/authorization prerequisites; only fixture evidence is
  planned. LLM tool calling and later triggers remain out of scope.
- Implemented configured repository/operation/author policies, bounded issue reads
  and approved creation over the existing HTTP transport. Creation commits a stable
  credential-bound HMAC marker before POST; recovery only reads and validates exact
  receipts. Missing/forged/ambiguous matches retain unknown effects for operators.
  Marker and provider backoff survive retry, worker loss and manual resolution.
- Rate-limit handling uses safe provider headers/messages, provider Date for reset
  durations, database-based retry timestamps and a retained pre-dispatch guard.
  The shared retry scheduler honors that floor and workflow deadlines. Read/write
  argument validation, closed result fields, redaction, cancellation and page/byte
  limits remain enforced. Added operator configuration and optional live-check docs.
- Local validation: `uv run --directory apps/api pytest tests/test_github_tool.py
  tests/test_github_tool_runtime.py tests/test_http_tool.py
  tests/test_http_tool_runtime.py tests/test_postgres_tool_runtime.py
  tests/test_tool_effects.py tests/test_retry_runtime.py tests/test_durable_queue.py
  -q --tb=short` passed **142 tests** in 478.34s (`.phase89-regression.log`).
  Final contract tests passed **30 tests** (`.phase89-contract-final-2.log`);
  a final targeted manual-resolution regression passed **1 test**
  (`.phase89-resolution.log`). Ruff, Compose configuration and staged diff checks
  passed. Existing TestClient deprecation warning is unchanged.
- Initial contract tests passed 23 tests. Initial worker tests had 9 passed and
  1 failed because the early-recovery fixture attempted a prohibited ORM bulk write.
  The fixture now uses scoped Core writes against its disposable schema; the
  corrected worker suite passed 11 tests, and the broader run verifies actual
  queued retry timing without an extra provider request. Local review also added
  explicit reconciliation-read permission, malformed timing/state validation and
  marker retention without stale outcome metadata during manual resolution.
- Scope exceeds the usual line target because the provider contract, durable
  correlation/backoff integration and extensive HTTP/PostgreSQL fixture coverage
  form one deployable integration. No live GitHub issue or external credential was
  used. Implementation `47399d7a0bdcb10576d08bab8d1fcbd671886d6a` is pushed to main
  (1,262 changed lines, including 603 new test lines).
  [CI 35129735975](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35129735975)
  and all commit checks passed: API (**746 tests**, existing TestClient warning),
  Web and Docker Compose, including fresh migration and dependency audits.
- Post-push review verified repository/operation/credential boundaries, exact human
  approval, marker commit before POST, credential identity, recovery without a second
  create, retained rate-limit deadlines, cancellation and safe receipts/errors.
  Existing HTTP/PostgreSQL, lifecycle and retry behavior remain compatible. No
  blocking findings or separate fix commit were needed.
- Phase 89 is complete. No live issue creation, real token or deployment was tested.
  Bounded reconciliation can require operator resolution on busy/edited repositories;
  provider backoff is per effect rather than a token-wide limiter. These limitations
  and the optional authorized sandbox check are documented. Phase 90 follows this
  record's push and successful CI.

### Phase 90 — Governed LLM Tool Calling — complete

- Authorized target remains Phases 66–105. Phase 89 evidence commit
  `f40a6052f496085f5f73948905ca5121b3a90e1a` passed all checks in
  [CI 35130613280](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35130613280).
- Inspected graph configuration, pinned provider execution, effect reservations,
  exact approval checks, durable worker claims, identity permissions and accounting.
  Add explicitly declared/versioned LLM tool bindings and bounded sequential execution
  of provider call batches. Validate the entire batch before dispatch. Reuse all
  adapter, credential, tenant, policy, approval and recovery checks.
- Persist conversation checkpoints and provider reservations/usage before tool I/O;
  resume pending calls and completed results after worker loss. Side effects require
  an upstream approval of the exact action envelope; one approval authorizes one
  logical effect even if the model changes its call ID. Recheck starter permissions.
- Enforce cumulative call, provider-round, estimated-cost and time budgets. Tool
  output is untrusted data and cannot alter bindings or authority. Expose safe call
  linkage and usage without credentials or raw conversation text in the trace.
- Acceptance: fixture-only provider tests plus real PostgreSQL worker/recovery tests
  for multiple calls, malformed/unknown arguments, duplicate IDs, budget exhaustion,
  restarts, exact approval/rejection/cancellation, revoked authority, injected output,
  stable effects and accounting. Broaden shared tool/LLM/lifecycle regressions.
- Rollout: additive tenant-owned conversation migration; empty tool bindings retain
  existing LLM behavior. Preserve the pinned Chat Completions/model interface. No
  live provider credentials, key changes, external calls or deployment are required.
- Implemented pinned tool declarations, full-batch validation, sequential ledger
  dispatch and exact upstream approval. Approved writes use approval-derived ledger
  identities; model call-ID changes cannot multiply an approved action. Current
  starter permissions and existing adapter/credential/policy boundaries are checked.
- Added the tenant-owned `llm_conversations` migration and owned-worker checkpoint
  service. Provider reservations/responses precede tool I/O; completed receipts and
  pending calls survive recovery. Call, provider-round, estimated-cost, repair and
  conversation-time limits persist across attempts. Unknown usage retains a cost
  reservation. Attempts expose safe ledger IDs/status and usage from original
  attempts; business projections include recovered usage. Existing LLM nodes remain
  on their previous execution path. See [LLM_TOOL_CALLING.md](LLM_TOOL_CALLING.md).
- Focused provider/runtime/migration run initially passed 40 tests with two fixture
  failures: the cancellation test did not expect the existing stale-result fence,
  and rejection expected failed rather than cancelled. These expectations were
  corrected. An earlier expanded fixture used a nonexistent service-principal name
  field; it was removed. The first runtime batch passed 13 tests before expansion.
- Final `tests/test_llm_tools.py` passed **28 tests** in 162.31s
  (`.phase90-final-focused.log`), including approved-write recovery, schema repair,
  revocation, pricing, exact approval, cancellation, credential redaction and tenant
  isolation. Final checkpoint recovery tests passed **2 tests** in 14.79s
  (`.phase90-checkpoint-final.log`); final trace/linkage tests passed **2 tests** in
  13.83s (`.phase90-trace-final.log`). Sales-template/durable-evaluation projection
  regressions passed **20 tests** in 135.52s (`.phase90-projection.log`). Migration
  round trip, populated retention and provider-contract tests passed in the initial
  40-test result. Ruff, Compose configuration and local diff checks pass. Existing
  TestClient deprecation warning remains.
- The combined explicit-file regression run was stopped after its buffered output
  remained at 72 passing test markers and a database snapshot showed no active work
  (`.phase90-regression.log`). Those observations did not establish a hang, and no
  completion is claimed for that run. Reran the suites separately
  with verbose output and a 90-second faulthandler diagnostic. The provider/LLM/
  migration group passed **36 tests** in 20.56s (`.phase90-provider-regression.log`).
  Final disabled-catalog regression passed **1 test** in 8.18s
  (`.phase90-revocation-final.log`), confirming denial before a provider request.
  The shared tool/lifecycle group passed **124 tests** in 666.75s
  (`.phase90-shared-regression.log`): `test_tool_effects.py`,
  `test_http_tool_runtime.py`, `test_github_tool_runtime.py`,
  `test_postgres_tool_runtime.py`, `test_execution_approvals.py`,
  `test_worker_leases.py`, `test_execution_cancellation.py`, `test_durable_queue.py`
  and `test_execution_starts.py`, with `-v --tb=short -o faulthandler_timeout=90`.
  No diagnostic timeout or failure occurred in the rerun.
- Final review aligned model/migration storage constraints and bounded provider
  usage to prevent aggregate overflow. Schema/runtime checks passed **2 tests** in
  16.37s (`.phase90-schema-final.log`); malformed usage passed **1 test** in 7.97s
  (`.phase90-usage-final.log`). Conversation deadlines now also retain the original
  attempt deadline, verified by **2 tests** in 13.37s (`.phase90-deadline-final.log`).
  Only local fixtures and disposable PostgreSQL were exercised.
- The phase exceeds the usual line target because durable provider conversation,
  authorization/ledger integration, migration/trace accounting and extensive crash
  fixtures form one bounded feature. No future trigger or frontend scope is included.
  Implementation `98241de95b0da3159e93905e017cc40be6854e61` is pushed to main
  (1,773 changed lines, including 670 added test lines).
  [CI 35135807330](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35135807330)
  and every commit check passed: API (**778 tests** in 315.54s, existing TestClient
  warning), Web and Docker Compose, including fresh migration and dependency audits.
- Post-push review checked pinned tool/schema/policy boundaries, current starter and
  reviewer authority, one effect per approved action, batch validation before I/O,
  worker-loss/cancellation fencing, retained conversation limits, original-attempt
  usage and ledger trace linkage. Migration ownership/retention and existing LLM,
  adapter and business projection compatibility were reviewed. No blocking findings
  or separate fix commit were needed.
- Phase 90 and the R08 integration/tool-calling sequence are complete. No live
  provider request, real credential, external action or deployment was tested.
  Approval occurs at an explicit upstream gate; provider requests with lost responses
  retain unknown usage/reserved cost, and adapter guarantees still govern uncertain
  remote effects. Estimated application budgets are not provider billing guarantees.
  These limits are documented. Phase 91 follows this record's push and successful CI.
- Delivery-record commit `a6037c19792cc074f5f60442ef2185aa6be9e29e` is pushed.
  [CI 35136566471](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35136566471)
  attempt 1 was cancelled prematurely after its API test step exceeded the preceding
  run's duration. Retrieved logs showed continued progress through 75% with no test
  failure; it was a slower run, not a demonstrated stall. The cancelled API job was
  rerun as attempt 2; all checks passed, including **778 API tests** in 434.15s and
  dependency audits. Every latest commit check was verified successful. No code fix
  was indicated by the cancelled logs, and Phase 91 is eligible to start.

### Phase 91 — Webhook Triggers — completed

- Authorized target remains Phases 66–105. Inspected the shared start/idempotency
  service, caller-owned evaluation transactions, identity/service scopes, graph
  references, audit records and API authentication boundaries. Phase 90's evidence
  commit and CI rerun are complete as recorded above; existing work is preserved.
- Add tenant-owned webhook configuration with pinned/published version selection,
  an explicit scoped service principal, bounded input references, revision-checked
  administration, server-owned signing-key aliases and bounded previous-key grace.
  No caller-supplied organization, workflow version or principal selects authority.
- Verify HMAC-SHA256 over the trigger ID, timestamp, event ID and exact body bytes;
  enforce freshness, size, enablement and current principal scope. Persist stable
  event/payload fingerprints, delivery outcomes and audit history. Replays retain
  the accepted version; changed bytes under the same event ID conflict.
- Under the trigger lock, use a caller-owned savepoint around shared run acceptance
  so receipt, pinned run and queue job commit atomically. Retain signed, authorized
  input rejections for retry/conflict history without storing raw rejected payloads.
  Preserve existing manual and evaluation starts when clarifying rollback ownership.
- Acceptance: real disposable PostgreSQL concurrent replay/publication/revocation
  tests; local API fixtures for signatures, freshness, payload limits, tenant/scope
  boundaries, mapping, rotation, retry history and transactional fault injection.
  Broaden start, permission, tenant and evaluation tests; inspect migration retention.
- Rollout: additive trigger/delivery tables and a service-principal tenant identity
  constraint. Empty API signing-key configuration denies webhooks. Tests use synthetic
  local keys and deterministic workflows; no external account, live hook or LLM call
  is required. Schedules and frontend trigger controls remain outside this phase.

- Implemented tenant-owned, revision-checked trigger administration, published/pinned
  selection, scoped service identities, bounded input references and signing-key
  rotation. Public delivery checks HMAC/freshness/limits and current service access;
  exact-byte replay retains the accepted run/version. Delivery/audit history is
  paginated and tenant scoped. Shared start savepoints preserve atomic receipt/run/job
  acceptance and retain safe input rejection history. Streaming reads are bounded;
  database acceptance runs in the thread pool. See [webhook operations](WEBHOOK_TRIGGERS.md).
- Local validation on disposable PostgreSQL 16.14 with synthetic keys:
  - `uv run --directory apps/api pytest tests/test_webhooks.py -q --tb=short`:
    **20 passed**, 73.99s (`.phase91-tests.log`). The initial run found a test-fixture
    actor reuse issue; configuration edits now simulate a separate administrator request.
  - `uv run --directory apps/api pytest tests/test_webhooks.py tests/test_webhook_migration.py
    tests/test_execution_starts.py tests/test_durable_evaluations.py tests/test_permissions_audit.py
    tests/test_tenant_isolation.py tests/test_security_controls.py -q --tb=short`:
    **80 passed**, 326.64s (`.phase91-regression.log`). An earlier invocation referenced
    a nonexistent `test_security.py` and ran no tests; the corrected command above passed.
  - Final additions: `pytest tests/test_webhooks.py -k 'pinned_selection or moved_between'
    -q --tb=short`: **2 passed**, 9.08s (`.phase91-extra.log`).
  - Explicit migration/race rerun: `pytest tests/test_webhook_migration.py tests/test_webhooks.py
    -k 'migration or races' -vv -o faulthandler_timeout=90 --tb=short`: **3 passed**, 19.47s
    (`.phase91-races-migration.log`). The broader run completed normally; no test was cancelled.
  - Ruff (`src tests`), Docker Compose configuration and `git diff --check` passed.
    Existing TestClient deprecation warning remains. No live webhook or deployment ran.
- Local review covered permissions, signature domain separation, current principal
  revocation, concurrent deduplication, pinned retries, rejected-input recovery,
  savepoint rollback ownership and migration retention. No blocking finding remains.
  The phase exceeds the suggested line target because its API, retained schema,
  signature/rotation protocol and real-database acceptance tests form one delivery unit.
- Implementation `9c56a1d8c1e5f09b2ae3549b079d674cc9503faf` pushed to `origin/main`:
  18 files, 1,509 changed lines including 464 test lines. GitHub CI
  [35141230134](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35141230134)
  passed **API, Web and Docker Compose**. API: **803 passed**, 456.13s;
  both dependency audits reported no known vulnerabilities. All commit check runs
  were separately verified successful. Phase 92 implementation has not started.
- Post-push review of the implementation inspected signature canonicalization and
  trigger binding, scoped administration/history, current service permissions,
  serialized publication/revocation, receipt/version retention, atomic queue acceptance,
  rollback ownership and migration compatibility. No actionable finding or fix commit.
- Completion: Phase 91 implementation, validation, push, CI and review are complete.
  This evidence record will be committed/pushed and its CI checked before advancing.
  No deployment or external webhook provider was exercised; fixture-backed limits
  and operation details are explicit in the guide. Phase 92 follows the record gate.

- Evidence record `87f570c83474b3044af54334ed80e6db2001226a` pushed to main;
  [CI 35142183434](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35142183434)
  passed API/Web/Compose, **803 tests**, 477.14s, and both dependency audits.
  All commit check runs were verified successful; the worktree was clean before Phase 92.

### Phase 92 — Scheduled and Cron Triggers — completed

- Inspected the shared start contract, webhook service-principal validation, tenant
  scopes, immutable history patterns, worker maintenance loop and execution terminal
  states. Phase 91's implementation and evidence-record CI are complete.
- Add tenant-owned schedule configuration, revision-checked administration, fixed
  input, explicit pinned/published selection, service identity, UTC next-fire time
  and retained fire history. Persist the planned `forbid` overlap and `coalesce`
  missed-run policies. Pausing retains the pending tick; resume coalesces once.
  Changes to timing, input or routing reset the next tick and are audited.
- Evaluate standard five-field cron in local wall time with bounded croniter search;
  use IANA ZoneInfo round trips to skip nonexistent times and select fold 0 once.
  Add locked croniter/tzdata dependencies for portable Windows/Linux behavior.
- Worker replicas select due IDs, then claim each schedule using tenant-scoped row
  locks with skip-locked behavior. Under one transaction, retain a unique fire receipt,
  revalidate service access, resolve a version, call shared start without committing,
  and advance the next tick. Rollback leaves the intended fire available to retry.
  Existing active runs suppress overlap; failures/skips retain bounded audit history.
- Acceptance: fake-clock DST, exact-boundary, invalid-cron, downtime, pause/resume,
  overlap, version/config/revocation cases; real PostgreSQL competing schedulers and
  rollback fault injection; tenant/admin API and migration retention checks. Broaden
  webhook/start/worker regressions after integration.
- Rollout: additive schedule/fire tables and worker maintenance integration; no
  schedule exists by default. Tests use deterministic workflows and local service
  fixtures, with no live provider or external account. Frontend controls are later scope.

- Implemented revision-checked schedule APIs, scoped target/input validation, retained
  schedule/fire models, bounded cron selection, atomic skip-locked firing and worker
  maintenance integration. The additive migration prevents fire-history mutation or
  populated downgrade. The dependency lock adds croniter 6.2.4, tzdata 2026.4,
  python-dateutil and six without updating existing packages.
- Local checks completed so far:
  - `uv run --directory apps/api pytest tests/test_cron_schedule.py -q --tb=short`:
    **17 passed**, 0.34s (terminal output).
  - `uv run --directory apps/api pytest tests/test_cron_schedule.py tests/test_schedules.py
    -q --tb=short`: **29 passed**, 49.39s (`.phase92-tests.log`).
  - `uv run --directory apps/api pytest tests/test_schedules.py -k process_crash
    -q --tb=short`: **1 passed**, 9.67s (`.phase92-crash.log`), with an actual child
    process exiting after queue insertion and before commit.
  - `uv run --directory apps/api pytest tests/test_schedules.py -k failed_candidate
    -q --tb=short`: **1 passed**, 5.94s (`.phase92-isolation.log`).
  - Ruff and diff checks passed; `uv run --directory apps/api pip-audit` reported
    no known vulnerabilities (`.phase92-audit.log`).
  - `uv run --directory apps/api pytest tests/test_schedules.py tests/test_schedule_migration.py
    tests/test_webhooks.py tests/test_execution_starts.py tests/test_durable_queue.py
    tests/test_worker_leases.py tests/test_durable_delays.py -q --tb=short`:
    **90 passed**, 416.19s (`.phase92-regression.log`). This includes migration retention,
    publication/revocation/configuration races and shared worker/start regressions.
- [Schedule operations](SCHEDULED_TRIGGERS.md) documents five-field cron, DST,
  pause/resume, edit resets, overlap, rejected ticks, crash recovery, worker logs and
  bounded search. Sources are the official croniter and Python ZoneInfo documentation.
  All run/clock/process evidence uses local deterministic fixtures; no provider call
  or deployment is claimed. Scope size includes the API, migration, clock rules,
  worker transaction and real database/process coverage as one phase delivery.
- Local review checked tenant authority, no external I/O under schedule locks,
  current service scope, atomic acceptance/advancement, immutable history, publication
  pinning, config resets, overlap, deadline ordering and compatibility with existing
  worker maintenance. No blocking finding remains. Final check:
  `uv run --directory apps/api pytest tests/test_schedules.py -k input_is_validated
  -q --tb=short`: **1 passed**, 5.84s (`.phase92-input.log`), covering validation both
  on configuration and after a published workflow changes its input schema.
  Implementation `969a56f4412dd212b08af87377c4ae2e287e5eab` pushed to main:
  18 files, 1,351 changed lines, including 507 test lines. GitHub CI
  [35145325829](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35145325829)
  passed **API, Web and Docker Compose**: **839 tests**, 521.48s, and both dependency
  audits reported no known vulnerabilities. All commit check runs were separately
  verified successful; no next-phase implementation has started.
- Post-push review checked standard cron validation and bounded DST selection,
  tenant/principal authority, skip-locked replica claims, pause/edit behavior,
  retained fire identities and version selection, atomic crash rollback, no external
  I/O under locks, rejected-tick advancement and existing worker compatibility.
  No actionable finding or fix commit.
- Completion: Phase 92 implementation, local validation, push, CI and review are
  complete. The completion record will be committed/pushed and its CI checked before
  Phase 93. No live model/provider call or deployment was performed. The documented
  schedule policy supports one active run and one coalesced catch-up decision, with
  bounded cron search and retained rejection/skip history.
- Delivery-record push note: GitHub reported `fatal error in commit_refs` for
  `de86ed824adaf6b4cfc2a4bfada27c2b28dae8b9`, but `git ls-remote` and a fetch confirmed
  that exact record on `origin/main`. No Actions run or check run appeared for it.
  This follow-up record uses a normal fast-forward push to obtain CI verification;
  no branch history is rewritten and Phase 93 remains gated on successful CI.

### Phase 93 — Generic Workflow Builder Editor (2026-09-16)

- Authorized scope: Phases 66–105. Phase 92 record `d65b295a46f6e63e6005cbc0e298b69190cf8934`
  is pushed and verified: CI [35146614924](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35146614924)
  passed API, Web and Compose; 839 API tests passed in 958.02s and both dependency
  audits were clean. All commit check runs were separately verified successful.
- Plan: reuse tenant-authenticated definition draft APIs and revision checks. Add
  listing/creation, accessible graph and edge editing, typed forms for all eight
  node types, bindings/schema/retry/deadline/quality settings, and save/reopen.
  Preserve incomplete drafts and unsaved edits on errors/conflicts. Recheck the
  organization at server-action boundaries and use backend permissions for editing.
- Acceptance: deterministic non-business graph creation/save/reopen; interactions
  across every node form, malformed JSON, read-only access, stale revisions and
  organization changes. Run frontend lint, typecheck, interaction/smoke tests and
  build, then pushed CI and review. No migration; additive frontend rollout only.
  Publication, server validation UI and trigger UI remain Phase 94.
- Implementation: definition listing/pagination and creation; SVG connection view
  plus keyboard controls; all eight node forms; prompt/tool catalog choices with
  unavailable values retained; bindings, schemas, retry, approval, delay, parallel
  and bounded revision settings. Unknown structural drafts retain a raw repair
  editor. Local diagnostics include node/field paths, missing endpoints, cycles
  and missing bindings. Incomplete drafts remain saveable; malformed JSON does not.
- Revision-aware server actions recheck current organization and draft permission,
  preserve edits on failure and invalidate the listing after successful saves.
  Archived/read-only drafts remain inspectable. Pending saves synchronously freeze
  controls and reject duplicate submissions. [Builder guide](WORKFLOW_BUILDER.md)
  documents authoring, conflicts and the boundary between draft hints and runtime
  validation. No backend schema/API behavior or published version is changed.
- Local validation: `pnpm --dir apps/web test:smoke`: **24 passed**, 4.25s
  (`.phase93-smoke.log`). Tests cover every node form, deterministic save/reopen,
  common schema/binding/retry/revision fields, malformed JSON retained across node
  switches, conflict retries, pending/network failures, read-only/archive access,
  structural repair, deletion diagnostics, tenant/permission guards and API error
  mapping. Initial harness navigator/label issues and a transition-priority pending
  control issue were corrected and the final suite passed.
- Browser acceptance used a fresh owned PostgreSQL schema `phase93_ui`, migrated
  through f092; API on localhost:8007 and frontend on localhost:3107, with identity
  and model calls disabled for this local fixture. Created **Dispatch confirmation**
  via the UI, added a zero-duration delay, connected it to the starter transform,
  saved revision 1, reopened equivalent node/edge values and saved revision 2.
  Existing backend validation returned `valid: true`, `executable: true`, no errors
  (`.phase93-ui-validation.log`). Mobile overflow inspection reported equal client
  and scroll widths; browser logs contained no warnings/errors. No deployment or
  external provider call is claimed. The temporary dev server was stopped and its
  generated instruction files removed; existing repository instructions are intact.
- Final local checks: `pnpm --dir apps/web lint`, `typecheck`, `build` and `audit`
  all passed (`.phase93-lint.log`, `.phase93-typecheck.log`, `.phase93-build.log`,
  `.phase93-audit.log`); audit reports no known vulnerabilities. `git diff --check`
  passed. Local review covered phase scope, tenant authority, revision conflicts,
  retained JSON buffers, unsupported drafts, catalog failures, read-only inspection
  and no mutation of published workflows. Implementation exceeds the suggested
  size because it includes the editor, eight forms, routes, interaction harness,
  dependency lockfile and guide as one coherent UI phase. Pushed CI/review pending.
- Implementation `e2c0ccb97a176e290ec7e105a3ef3181a7dca91c` pushed to main
  (14 files, 1,170 changed lines, including 428 lockfile and 192 interaction-test
  lines). Post-push review found that structurally supported drafts with extra
  fields lacked a raw repair path, and literal objects resembling node references
  could receive misleading diagnostics. A separate scoped fix adds synchronized
  raw/visual editing, specific object-shape errors and expression-aware reference
  checks. `pnpm --dir apps/web test:smoke`: **25 passed**, 11.90s
  (`.phase93-fix-smoke.log`); typecheck, lint, build and diff checks passed
  (`.phase93-fix-typecheck.log`, `.phase93-fix-lint.log`, `.phase93-fix-build.log`).
  Original CI [35150972881](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35150972881)
  passed API, Web and Compose: 839 API tests in 533.00s; both dependency audits clean.
  All implementation check runs were verified successful before pushing the fix.
  Phase 94 has not started.
- Repair fix `04e2ab52e398a28025466e2ada5ac9a0da00516e` is pushed (5 files,
  51 changed lines). Follow-up review found a second consistency edge case: the
  editor accepted a returned revision but retained its older local graph/name.
  The next correction adopts returned content and revision together while controls
  remain frozen. A regression covers a changed server snapshot and the subsequent
  save body. Local smoke/interaction checks: **26 passed**, 4.53s; typecheck, lint
  and diff checks passed (`.phase93-snapshot-smoke.log`,
  `.phase93-snapshot-typecheck.log`, `.phase93-snapshot-lint.log`). Repair CI
  [35151952306](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35151952306)
  passed API, Web and Compose: 839 API tests in 534.47s; both audits clean. All
  repair commit checks were verified successful before the snapshot correction
  push. No later phase implementation has begun.
- Snapshot correction `9c62fc45b74ab63eacd4dd9dae448a5687ed9b8f` pushed to main
  (3 files, 33 changed lines). CI
  [35152925598](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35152925598)
  passed API, Web and Docker Compose: **839 API tests**, 524.47s; frontend's
  **26 smoke/interaction tests**, typecheck, lint and production build passed;
  both dependency audits clean. All commit check runs were verified successful.
- Final review verified returned content/revision consistency, preserved failures,
  raw/visual synchronization, literal/reference distinction, tenant and permission
  boundaries, malformed draft recovery and compatibility with existing screens.
  No unresolved actionable finding. Phase 93 implementation, validation, pushes,
  CI and review are complete; the completion record is pushed and its CI checked
  before Phase 94. Local hints are not full runtime validation; advanced nested
  settings use JSON editors. No live provider call or deployment was performed.

### Phase 94 — Builder Validation Publication and Version History (2026-09-16)

- Authorized scope: Phases 66–105. Phase 93 record
  `11de96adda12d35073b14741e6b674dd458d2b91` is pushed; CI
  [35153883493](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35153883493)
  passed all API, Web and Compose checks, including 839 API tests in 516.54s and
  clean dependency audits. All record commit check runs were verified successful.
- Plan: add a saved-draft release view with validation bound to its exact revision,
  runtime capabilities, paginated immutable versions/diffs and admin publication.
  Manual starts send an explicit version and retain the same request/key through
  retries. Add paginated webhook/schedule configuration and history screens using
  current service principal, revision, enablement and version-policy contracts;
  signing aliases are write-only masked inputs and actual keys never enter the UI.
  Recheck tenant/permission boundaries inside every server action and retain edits
  on conflict. Preserve published snapshots and existing business screens.
- Acceptance: publish two versions in the UI; an older waiting run retains v1,
  a later start pins v2, duplicate/retried starts retain one key/run. Cover invalid
  graphs, unavailable runtime capabilities, stale publication, permission/tenant
  rejection, trigger edits/history and masked signing references with focused API
  and frontend interaction checks plus browser fixtures. No migration; validation
  responses gain an additive nullable draft revision. Debugger/recovery stays in
  Phases 95–96. Run relevant lint/typecheck/build/audits, push, wait CI and review.
- Implementation: added revision-bound saved-draft validation/publication,
  immutable version selection, capability checks, bounded diffs and explicit
  version/manual-input starts. Duplicate clicks are suppressed; retries retain
  the exact request/key for the page lifetime. Added paginated trigger listings,
  webhook/schedule editors, enablement, revision conflicts, masked write-only
  signing aliases/rotation and delivery/fire history. Server actions recheck
  current organization/permissions. Added builder operations documentation.
- Browser acceptance: production Next build against the isolated `phase93_ui`
  PostgreSQL schema, with synthetic service-principal/signing fixtures only.
  Published v1 (`9dd83268-e8b8-4656-ace5-ccdc058fa814`) and v2
  (`a8eda1c0-13f9-432d-8529-38e29d4f2e89`) through the UI. Run
  `dac895fc-ac16-46a4-9a88-7929a6bd787b` retained v1 and its waiting delay;
  `8febe05a-b9eb-4333-9ab2-7730b191d169` selected v2 and completed after worker
  execution. UI retries returned those same runs; capabilities/diff showed the
  saved delay change. Created/enabled/rotated/paused a webhook, sent the same
  signed fixture twice and observed one delivery/run with two attempts in UI
  history. Created a cron schedule, ran its due/coalesced fire, inspected history
  and paused it. Desktop and 390×844 trigger layout were inspected; document
  scroll/client widths both measured 375px at the narrow viewport.
- Acceptance uncovered expired-ORM schedule create/update responses serializing
  as empty objects. The API now materializes configuration fields while its
  session is open; response-body regression assertions cover create/update/read.
  Retested both creation and update in the browser, showing saved revisions 1/2.
  Local review also corrected historical version pages to select a visible
  version, with a focused start-selection regression test. No schema changes.
- Validation so far: 40 frontend smoke/interaction checks passed (32772.50ms),
  typecheck, lint, production build and `pnpm --dir apps/web audit` passed
  (no known vulnerabilities). Evidence: `.phase94-final-{smoke,typecheck,lint,build}.log`,
  `.phase94-audit.log`, `.phase94-browser-api-evidence.log` and worker fixture logs.
  `uv run --directory apps/api pytest tests/test_workflow_definitions.py
  tests/test_schedules.py -q --tb=short` passed all 30 real-PostgreSQL checks in
  533.97s; `ruff check src tests` passed. The test output was buffered until
  completion; active database work was observed and the run was not interrupted.
  `.phase94-final-api.log` and `.phase94-final-ruff.log` retain these results.
  Staged diff review and `git diff --cached --check` passed before committing.
- Implementation commit: `56a6ed56bba4f7203a467af87fa8425ad79ecc67`, pushed to
  main (22 files, 693 changed lines). CI
  [35158016397](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35158016397)
  passed API, Web and Docker Compose. API passed 840 tests in 435.06s; frontend
  passed all 40 smoke/interaction checks. Both dependency audits were clean.
  The commit's complete set of check runs was independently verified successful.
- Post-push review: checked current backend permission mappings and tenant guards,
  exact-revision validation/publication, immutable version selection, duplicate
  click suppression, frozen retry payloads, archive rejection, trigger revision
  conflicts, alias masking, pagination and partial history failures. No unresolved
  blocking findings. The schedule response and historical selection findings were
  corrected and validated before the implementation commit. No fix commit needed.
- Completion decision: Phase 94 is complete. Limits: start request keys are retained
  for the open page lifetime; compare versions within one history page; service
  principal UUIDs and signing aliases must already be provisioned. No provider
  requests, real signing keys or production deployment were used. Phase 95 may
  begin after this completion-record commit is pushed and all its CI checks pass.

### Phase 95 — Generic Graph Run Debugger (2026-09-16)

- Authorized scope: Phases 66–105. Phase 94 completion record
  `ac22853d9acbaa3b1b9e6c70e1fc02876539ab5e` is pushed; CI
  [35158752466](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35158752466)
  passed every check, with 840 API tests in 515.59s, clean audits and independently
  verified successful check runs. Worktree was clean before this phase.
- Inspected current execution/step/attempt/event, tool-effect, approval and legacy
  readers; immutable version and runtime snapshots; branch/quality checkpoints;
  recovered LLM usage and AgentStep compatibility projections. Preserve all
  execution/control behavior and existing APIs. No schema migration is needed.
- Plan: add tenant-authorized trace readers with bounded/redacted payload previews
  and explicit detail access, paginated steps/attempts/events/tools/approvals and
  historical steps. Render immutable graph topology/current edge decisions and
  latest node status separately from selected branch/iteration/attempt history.
  Show model/prompt, usage/cost/latency, waits, approval details and errors. Route
  projected historical runs to their canonical generic trace; never combine their
  usage with AgentStep projections. Add graph-run listing, run/detail navigation
  and useful independent failure states. Keep retry/recovery and live polling in
  Phases 96–97.
- Acceptance: tenant/missing-resource/pagination and redaction boundaries; stable
  version after draft publication; repeated nodes with distinct branch/iteration
  and attempt IDs; deterministic, LLM/tool, approval/delay/parallel, failed,
  cancelled and historical trace fixtures; large and empty payloads; frontend
  interaction, typecheck, lint/build and browser checks. Push and wait all CI,
  then review and fix any actionable findings before completing this phase.
- Implementation: additive `/execution-traces` readers expose metadata pages,
  immutable topology/current edge decisions, exact logical-step/attempt details,
  tool effects, events and approvals. Payloads load only on explicit inspection,
  with credential-field/URL-userinfo redaction, traversal and shared string bounds.
  Legacy readers preserve original labels/totals and direct projected runs to
  their canonical generic trace. Added graph-run listing/debugger, historical
  links, focused detail navigation, independent section failures and operations
  guide [WORKFLOW_DEBUGGER.md](WORKFLOW_DEBUGGER.md). No execution mutations,
  provider calls, schema migration, recovery controls or polling were introduced.
- Validation: initial 9 debugger API tests passed in 38.08s; broader
  `pytest tests/test_execution_traces.py tests/test_execution_records.py -q --tb=short`
  passed 17 real-PostgreSQL checks in 99.99s. After tightening preview allocation,
  all 10 final debugger API checks passed in 24.37s, including a 32 MB synthetic
  source whose preview allocated under 2 MB. Ruff passed. Frontend smoke/interaction
  checks passed all 47 tests in 42910.92ms; typecheck, lint, production build and
  dependency audit passed. Corrected the shared browser-test FormData binding;
  the final rerun had no earlier Node/browser FormData errors. Evidence:
  `.phase95-api-{tests,regression}.log`, `.phase95-final-api.log`,
  `.phase95-final-{smoke,typecheck,lint}.log`, `.phase95-build.log`,
  `.phase95-audit.log` and `.phase95-ruff.log`.
- Browser acceptance: production UI against owned `phase93_ui` schema. Inspected
  the real completed v2 run and exact transform attempt/output; all-node synthetic
  history fixture `6f5f5ed7-fc62-4511-aea3-6cd9336d18f9` showed parallel, LLM/tool,
  approval/delay, failed/cancelled and repeated-node records. Selected its exact
  iteration/branch/attempt, verified 64,000-character truncation, usage and redacted
  tool/approval detail. Historical fixture `bb9a89b2-ac74-42d4-b6ac-554d99f56faa`
  retained original labels and 12-token/$0.01 source totals. Narrow viewport
  inspection measured document/scroll width 375px at 390×844, without overflow.
  Created a new disposable run `42681e7e-bccb-4b82-af6f-afc645798edf`, cancelled it
  through the existing API and verified retained status/reason in UI. A separate
  built-in code fixture `046af59b-9236-4540-93eb-90a324eb65f7` executed in the worker
  and failed its output contract; UI showed `output_invalid` and the pinned node.
  Evidence includes `.phase95-{browser,legacy,cancel,failed}-fixture.log` and
  `.phase95-worker-failure.log`. Synthetic history is reader acceptance, not a claim
  that external integrations or providers were exercised.
- Local review: verified ownership joins, immutable graph source, pagination,
  payload loading/redaction, exact step identity, recovered usage and exclusion of
  legacy projections. Hardened the shared preview string budget before commit;
  no remaining local findings. The phase exceeds the preferred 300–700-line size
  because the complete debugger includes scoped/redacted APIs, historical adapters,
  UI and API/frontend acceptance coverage; all changes belong to Phase 95.
  Final staged diff and whitespace checks passed (22 files, 1,100 additions and
  5 deletions).
- Implementation commit `d4ecca767d138fccc905d149d7be90d005401fc2` pushed to
  `origin/main`. [CI run 35162214976](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35162214976)
  completed successfully: 850 API tests in 425.81s, API lint/fresh migrations/audit,
  47 frontend checks, typecheck/lint/production build/audit, and Compose validation.
  Both audits reported no known vulnerabilities; independent commit check-runs
  confirmed API, Web and Docker Compose success. Evidence: `.phase95-ci.log`.
- Post-push review: checked pinned versions/current versus historical graph state,
  tenant-scoped joins and record ownership, read-only lifecycle behavior, stable
  pagination, bounded/redacted payloads, exact attempt navigation, per-attempt
  accounting, historical compatibility and partial failure handling. No blocking
  or actionable findings; no fix commit required.
- Completion: Phase 95 implementation, validation, push, CI and review are complete.
  The completion-record commit must also pass CI before Phase 96 begins. Retained
  limitations are explicit: bounded previews, current checkpoint edge state,
  known-field redaction, and selected-attempt rather than aggregate generic cost.
  Recovery controls and polling remain scoped to Phases 96 and 97.

### Phase 96 — safe manual retry and recovery controls

- Authorized range: Phases 66–105. Phase 95 completion record
  `c59e53f3cfe9461ca2dfd5b39ee590b37c11fc79` was pushed; all checks in
  [CI 35162885131](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35162885131)
  passed (850 API tests in 431.30s, Web and Compose green, both audits clean).
  Independent check-runs confirmed success; `.phase95-record-ci.log` retains evidence.
- Plan/inspection: reviewed the required context docs, Phase 96 requirements,
  graph/parallel/quality checkpoints, lifecycle immutability, cancellation,
  worker lease recovery, retry budgets, effect ledger/reconciliation, private LLM
  continuations, permissions and debugger. Preserve their existing authorities.
- Implementation plan: add an immutable tenant-scoped recovery receipt with one
  child per terminal source, preserving original version/input/runtime settings.
  Copy safe completed checkpoints with explicit provenance; rerun approval gates
  and their dependent computation. Link logical tool actions to original effect
  identities and retain bounded LLM continuation budgets. Block uncertain effects
  until recorded reconciliation; never manufacture a new effect key to bypass a
  confirmed result or exhausted effect budget. Keep original terminal rows intact.
  Active-run retry invokes existing expired-lease recovery, including its budgets
  and backoff; it does not reopen terminal jobs or accelerate scheduled retries.
- UI/API plan: current eligibility/reasons, cancel, expired-lease retry, linked
  terminal recovery and administrator effect-resolution controls in the debugger.
  Recheck permissions and scope at mutation time; suppress duplicate pending UI
  requests and serialize competing operators. Preserve trace availability when
  control requests fail; expose recovery provenance without duplicating usage.
- Migration/rollout: additive recovery receipt table and nullable logical-step
  provenance field with tenant foreign keys; deploy migration before updated
  API/workers. Retain historical runs/attempts/effects and existing API contracts.
- Acceptance: independent-session duplicate recovery and cancel races; immutable
  terminal snapshots; pinned settings/input and rejection of changed-input requests;
  reused output/effect identity, unknown and exhausted-effect blocking, fresh/expired
  approval behavior, continuation budget preservation and unauthorized access.
  Validate migrations, focused PostgreSQL/worker regression tests, frontend
  interaction/type/lint/build, and local browser control flows. Push, wait all CI,
  review and fix before completion; observability/polling remains Phase 97.
- Implementation: additive `f096_execution_recovery` receipt/provenance migration,
  scoped eligibility and control APIs, source-serialized recovery receipts, safe
  checkpoint reuse and fresh approval gates, lineage-bound effect identities,
  retained private LLM continuation budgets and scoped expired-lease retry audit.
  Added debugger controls with reason/evidence forms, pending-request guards,
  current permission/scope checks and retained error state. Operations semantics
  and rollout are documented in [WORKFLOW_RECOVERY.md](WORKFLOW_RECOVERY.md).
- Local validation so far: initial 4 recovery PostgreSQL checks passed in 29.82s;
  57 recovery/LLM/tool-effect checks passed in 339.78s. Expanded recovery/migration
  suite initially had one incorrect test helper name (11 passed); corrected it.
  All 14 subsequent recovery/migration checks passed in 89.03s, including real local
  HTTP lost-response reconciliation, fresh/expired approvals, LLM round/cost
  retention, migration roundtrip/retention, parallel joins and quality iteration.
  Local review caught and fixed initial recovery scheduling for quality iteration
  greater than zero, with dedicated regression coverage. Final broader backend
  validation passed 63 checks in 386.12s (`test_execution_recovery`, recovery migration,
  parallel runtime, worker leases, cancellation and quality revisions), including
  exhausted-effect policy. After metadata-only eligibility reads and current-actor
  audit hardening, all 15 final recovery/migration checks passed in 94.15s.
  The migration additionally rejected direct SQL provenance changes (1 final check
  passed in 8.80s). Evidence: `.phase96-api-final.log`, `.phase96-migration-final.log`.
- Frontend: all 53 smoke/interaction checks passed in 11941.42ms; typecheck, lint
  and production build passed. Ruff and diff whitespace checks passed. Evidence:
  `.phase96-api-{initial,effects,expanded,final-focused,regression}.log`,
  `.phase96-web-{smoke,typecheck,lint,build}.log`.
- Browser acceptance: migrated only owned `phase93_ui` schema from f092 to f096
  and ran production UI/API. Created new disposable deterministic run
  `3a88b9ed-7852-4e68-aecf-d72732374944`, cancelled through the UI, and created
  linked recovery `15bda07b-3221-4b8f-877b-85f96a0b7b9b`. Repeated recovery returned
  that same child. The child retained pinned v2, completed in the worker, exposed
  its original source link and disabled terminal mutations. The original remains
  cancelled. At 390×844, document/scroll widths were both 375px; restored normal
  viewport afterward. Evidence: `.phase96-ui-migration.log`,
  `.phase96-browser-{fixture,worker,recovery}.log`. No paid provider or real external
  account was used; HTTP effects and LLM responses in tests are explicit fixtures.
- Scope size: this phase exceeds the preferred 300–700 changed lines because safe
  recovery spans immutable schema, checkpoints, logical effects, LLM budgets,
  permissions, controls and meaningful concurrency/integration coverage. All
  changes are Phase 96; commit/push, CI and post-push review remain required.
- Local review: checked lock ordering and decision-time permissions, immutable
  source/receipt/provenance, original input/settings/version, branch/quality
  scheduling, expired approval replacement, LLM continuation/accounting,
  successful and uncertain effects, bounded policies and duplicate operator
  actions. Tool eligibility queries now omit payloads and refresh effect metadata
  under lock. No unresolved local findings; all required local checks passed.

- Delivery: implementation `9524627e4842e659c38e06379aba5ec381897db2` pushed to
  `main`. [CI 35165725922](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35165725922)
  passed API, Web and Docker Compose; all three independent commit check-runs
  confirmed success. API: **865 passed**, 1 warning, 567.84s; fresh migrations and
  Ruff passed. Web: all 53 checks, typecheck, lint and production build passed.
  Both dependency audits reported no known vulnerabilities.
- Post-push review: checked phase acceptance against source/receipt immutability,
  source-lock serialization, tenant/current permission checks, effect reconciliation,
  preserved attempt budgets and usage, fresh approvals, parallel/quality scheduling,
  migration compatibility and error/pending UI behavior. No blocking findings or
  fix commit required. Phase 96 is complete. Phase 97 may begin after this
  completion-record commit is pushed and every required CI check passes.
- Limitations: explicit recovery lineage is bounded to 100 generations; changed
  input/policy or exhausted conversation/effect budgets requires a new start.
  Tests use deterministic LLM/HTTP fixtures; no production deployment is claimed.

### Phase 97 — Worker Observability and Live Updates

- Authorized range: 66–105. Dependency 96 is complete. Completion record
  `4a0ec2e5076ea2373d01a1d49a8a688def43e2f4` was pushed; CI `35166525941`
  passed all three independent check-runs, 865 API tests in 566.69s, 53 frontend
  checks, build/type/lint, fresh migrations, Compose and both dependency audits.
- Inspected queue claims, lease recovery, execution events/attempts, tenant
  enforcement, legacy projection revisions, debugger controls and approval pages.
- Plan: add tenant-scoped metadata operations summaries and bounded job history
  for queued/running/failed/retrying/dead-letter/stale work. Derive claim, recovery,
  wait, attempt and completion metrics from persisted records; include measured
  queue wait and fixed-window throughput. Add a small infrastructure heartbeat
  registry for worker liveness. Tenant worker visibility is limited to workers
  associated with that tenant's jobs, with no hostnames, foreign workloads or
  fleet capacity exposed. Export fleet metrics through an infrastructure-only
  database CLI, separate from tenant HTTP permissions.
- UI plan: operations page and bounded, permission-aware polling for run lists,
  run/debugger details, approvals and operations. Single-flight polling pauses
  offline/hidden, backs off on failures/waits, stops on terminal details and
  refreshes after mutations while retaining form state. Metadata pulses avoid
  periodically fetching payloads. Document incident diagnosis and metric meaning.
- Migration/rollout: additive ephemeral worker presence table/indexes; migrate
  before updated workers/API. Existing durable records remain authoritative;
  old workers are reported as unobserved, not falsely healthy. No new dependencies.
- Acceptance: real PostgreSQL counts across claim, retry/lease loss, waits,
  completion and recovery; independent tenant/API permission checks and bounded
  pagination; worker start/stop/staleness and secret-free low-cardinality export.
  Fake-clock frontend checks cover non-overlap, offline/reconnect, backoff,
  terminal stop and mutation refresh. Run affected worker/migration regressions,
  frontend/type/lint/build and browser acceptance; push, await all CI and review.

- Implementation: additive `f097_worker_presence`, best-effort expiring/stopped
  worker presence, persisted claim-wait observations, tenant metadata summaries,
  bounded filtered jobs, tenant Prometheus export and infrastructure-only fleet
  CLI. Added metadata change tokens, operations UI, and permission-aware bounded
  polling on runs/debugger/approvals/operations. Mutation refresh retains form
  text and refreshes trace history/eligibility, including terminal effect changes.
  [WORKER_OPERATIONS.md](WORKER_OPERATIONS.md) documents definitions, incident
  diagnosis, isolation, rollout and visibility limits.
- Backend validation: initial fixture import typo was corrected. Five focused
  checks then reported 4 passed and one incorrect expected claim count; corrected
  the expectation to include the terminal scheduling checkpoint. Broader worker,
  delay, recovery, operations and migration validation ran **51 passed, 1 failed**
  in 272.49s: the migration test needed to commit DDL before a second connection
  read it. Corrected the fixture; **7 focused checks passed** in 43.23s.
  Local review found a real bounded-pool risk from holding the authorization
  connection while borrowing a second snapshot connection. The read route now
  ends its authorization transaction and reuses the request session for a
  repeatable-read snapshot. Final **8 operations/migration checks passed** in
  53.56s, including a one-connection/no-overflow pool and foreign-worker/approval
  isolation. Ruff passed. Logs: `.phase97-api-{focused,regression,final,accepted}.log`.
- Frontend validation: **63 smoke/interaction checks passed** in 5671.182ms,
  including single-flight/queued mutation refresh, bounded backoff, offline and
  hidden-state pause, reconnect, terminal stop/manual retry, late-response disposal,
  current organization checks, terminal effect refresh and retained reason text.
  Final lint initially identified JSX inside a try/catch in the live wrapper;
  moved rendering after the guarded request. Final lint, typecheck and production
  build passed. Logs: `.phase97-web-ready-smoke.log`,
  `.phase97-web-accepted-{lint,typecheck,build}.log`. Diff whitespace checks passed.
- Browser acceptance: migrated only owned `phase93_ui` schema to f097. Operations
  showed bounded job history and queued filtering. New deterministic run
  `b360e7a2-d28c-474e-92ba-1c9ed3c78795` advanced from pending to running via one
  real worker checkpoint; debugger/history/eligibility updated automatically and
  the typed reason remained. UI cancellation immediately refreshed to cancelled
  and stopped polling. UI recovery linked `0c11ba57-7f2c-4665-85f1-87f896e6c480`;
  worker drain completed it and polling automatically stopped at completed.
  Operations/CLI reconciled 19 retained claims, 3 new wait samples, 2 linked
  recoveries and 1 completion in the current 15-minute window. These include prior
  synthetic UI fixtures and are not benchmark claims. At 390×844, client and
  scroll widths were both 375px; restored the normal viewport. Evidence:
  `.phase97-ui-migration.log`, `.phase97-browser-{fixture,worker-one,worker-drain,
  operations-final,fleet-metrics,completed}.log`. No paid providers or real effects.
- Local review: checked tenant filters on every Core aggregate/job query, absence
  of global HTTP overrides, stable low-cardinality exports, stopped worker fencing,
  queue/attempt accounting, bounded pool use, polling disposal/backoff and mutation
  refresh. No unresolved local findings. Scope exceeds the preferred 300–700 lines
  because it spans schema, worker telemetry, scoped APIs, multiple live UI surfaces
  and meaningful regression coverage. All changes belong to Phase 97. Commit,
  push, full CI and post-push review remain required before completion.

- Pushed implementation: `202adc1284a9a82012b8d44375ff522727b0b516`, CI
  `35169468174`. Post-push review found that legacy run/approval list refreshes
  still used unbounded list endpoints, including approval-to-run lookup fanout.
  The separate fix adds opt-in API pagination, 25-row live pages with a one-row
  lookahead, page-local count/search explanations, and a scoped one-row pending
  approval lookup on run detail. Existing unpaginated callers retain compatibility.
  Polling now also pauses during a React page refresh and retains pending forced
  refresh requests across that pause, even when a terminal token is unchanged.
- Fix validation: **25 backend checks passed** in 101.44s (operations and legacy
  run/approval API compatibility), **65 frontend checks passed** in 18805.3258ms,
  Ruff/lint/typecheck/production build and diff checks passed. Browser verified
  the new run/approval page scope explanation and successful API requests with
  `offset=0&limit=26`. Logs: `.phase97-fix-api.log`,
  `.phase97-fix-web-{smoke,lint,typecheck,build}.log`, `.phase97-fix-api-server.log`.
  Implementation CI `35169468174` completed successfully before the fix push:
  **873 API tests passed** in 570.33s, 63 frontend checks, fresh migrations,
  Ruff/lint/typecheck/build, Compose and both clean dependency audits. All three
  independent check-runs confirmed success. Fix push/review and completion gates
  are still outstanding.

- Delivery: fix `f73d4a1ac5fbd1ed6a8a11a05f0defc0ef653084` pushed to `main`.
  [Fix CI 35170222011](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35170222011)
  passed all API, Web and Docker Compose jobs; all three independent commit
  check-runs confirmed success. **874 API tests passed**, 1 warning, 590.02s;
  all 65 frontend checks, fresh migrations, Ruff/lint/typecheck/build and both
  clean dependency audits passed.
- Follow-up review: verified optional pagination preserves existing callers,
  applies tenant filtering before limits, bounds input/run lookup fanout, and
  keeps single-flight polling and forced refresh intent across transitions.
  Rechecked metadata-only metrics, worker expiry, terminal polling, permission
  changes, retained form state and migration compatibility. No unresolved
  blocking findings. Phase 97 is complete; Phase 98 may begin after this
  completion record is pushed and all required CI checks pass.
- Limitations: list search/counts describe the displayed page; offset pagination
  can shift while new records arrive. Tenant worker presence shows only workers
  associated with retained tenant jobs, and historical claims without the new
  observation are excluded from queue-wait samples. Fleet metrics require trusted
  infrastructure database access. No production deployment or throughput claim.

### Phase 98 — Deterministic Throughput Benchmark

- Authorized range: 66–105. Dependency 97 is complete. Completion record
  `d2b46667fd1476008697e55d698c0da38bbdd32e` was pushed; CI `35171054414`
  passed all three independent check-runs, 874 API tests in 565.56s, 65 frontend
  checks, fresh migrations, lint/typecheck/build, Compose and both clean audits.
- Inspected acceptance/idempotency, queue workers, parallel scheduling, exact
  tool approvals, HTTP destination policy, migrations and PostgreSQL fixtures.
- Plan: add an opt-in benchmark CLI with fixed-seed bounded condition, parallel
  and governed loopback HTTP workloads, synthetic persisted admin membership,
  normal approval decisions and no LLM/provider calls. Create fresh uniquely
  owned migrated schemas per concurrency stage; retain data and evidence.
  Accept at least 10,000 workflows across capacities 1, 4 and 16, in bounded
  batches, deliberately replay start requests, and drain using real workers.
- Evidence: record source fingerprints/base commit, environment, workload,
  duration, resource observations, latency percentiles, throughput and retries.
  Save machine-readable per-run/job/effect reconciliation and a readable report.
  Assert complete accepted-ID coverage and exact intended sink identities;
  report failures and preserve partial evidence instead of excluding them.
- Acceptance: deterministic small real-PostgreSQL CLI sample in CI, malformed
  bounds and reconciliation failure checks, Ruff, documented full benchmark,
  local diff review, phase commit/push, all CI and post-push review. No schema
  migration or application/UI behavior change is planned. Measurements exclude
  HTTP/OIDC ingress and human decision latency; they include real service-level
  permission checks, persisted decisions and controlled HTTP dispatch.

- Implemented the opt-in CLI, isolated migrated schemas, three bounded workloads,
  membership-backed synthetic approver, real worker controller and independent
  loopback sink. Added per-ID reconciliation, hashed JSONL archives, portable
  resource observations, source fingerprints and an offline verifier. No runtime
  service, schema, dependency or UI behavior changes. Instructions and limits:
  [BENCHMARK.md](BENCHMARK.md).
- Local validation: initial real CLI sample completed all 12 workflows at
  capacities 1/4 and observed all four intended effects. Focused tests passed
  **2/2 in 56.49s**; after tightening receipt/job/attempt/version/output checks,
  final **2/2 passed in 87.07s**, including corruption/missing-record rejection.
  Ruff passed. Logs: `.phase98-small-initial.log`, `.phase98-focused.log`,
  `.phase98-accepted.log`. No unrelated frontend suite was required locally.
- Full experiment started 2026-09-17 at approximately 02:05 UTC with the documented
  10,000-count command, capacities 1/4/16 and batches of 100. The measured Python
  sources are fixed for this run. Environment and periodic PostgreSQL resources
  are retained in `docs/evidence/phase98-environment.json` and
  `docs/evidence/phase98-resources.jsonl`; stage artifacts will be written under
  `docs/evidence/phase98-full`. Completion, full reconciliation, phase delivery,
  all CI and post-push review remain outstanding. No full-run result is claimed.

- Full-run outcome (2026-09-17 02:05:02–03:10:45 UTC): **10,000 accepted and
  completed workflows**, **33,333 completed jobs**, **26,666 completed attempts**,
  and **3,333 intended sink effects**, all reconciled. No failed/cancelled/active
  runs, missing jobs, extra/unknown effects, worker/controller errors, step/tool
  retries or lease recoveries. **1,000 duplicate starts were prevented**; the sink
  received no duplicate requests. Command and resource sampler both exited 0.
- Measured capacities 1 / 4 / 16 completed 3,334 / 3,333 / 3,333 workflows in
  2,467.594 / 786.141 / 588.250 seconds: **1.351 / 4.240 / 5.666 workflows/s**.
  End-to-end p95 was 73.695 / 20.898 / 14.398 seconds. Input was at most 130 bytes.
  These are single-process local observations with immediate synthetic approvals,
  fresh schemas per stage and a shared Windows/Docker host, not production targets.
- Independent verification: `python -m src.benchmarks.verify` passed for all
  10,000 IDs and 3,333 sink identities. A separate check matched all **220 source
  fingerprints** and all fixed-seed workloads; final Ruff passed. Evidence logs:
  `.phase98-full.log`, `.phase98-offline-verification.log`,
  `.phase98-source-verification.log`. [Measured results](BENCHMARK_RESULTS.md)
  link the manifest, 30 hashed raw archives, environment, 124 database resource
  samples and generated report. All three owned schemas remain available.
- Local review: checked fresh-schema ownership, current membership/approval paths,
  immutable version inputs, bounded producer/worker/sink work, persisted start/job/
  attempt/effect identity accounting, failure visibility, reproducible seeds,
  percentile definitions and resource/provenance limits. Corruption tests reject
  missing records and duplicate effects. No unresolved local findings. The phase
  exceeds the preferred 300–700 lines because the independently usable CLI includes
  typed workload graphs, sink/controller, cross-platform observations, raw-data
  verification and documentation; roughly 7 MB of compressed full-run evidence is
  retained to make the 10,000-run claim inspectable. Commit/push, all CI and
  post-push review are still required before Phase 98 is complete.

- Delivery: implementation **`450c8c4e114bf0767311a75023178705125878de`**
  was pushed to `main`. [CI 35177537976](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35177537976)
  completed successfully: **876 API tests in 429.03s**, Ruff, fresh PostgreSQL
  migration, API dependency audit; **65 web smoke tests**, lint/typecheck/build,
  web dependency audit; Compose configuration. Both audits reported no known
  vulnerabilities. The commit check-runs endpoint independently confirmed all
  three jobs completed successfully.
- Post-push review checked the committed workload graphs, isolated schema and
  output ownership, bounded worker/controller behavior, exact receipt/job/attempt/
  effect accounting, immutable version/input checks, archive hashes, failed-run
  visibility, and measurement provenance. No blocking findings or fix commit.
  The CLI is opt-in and does not change application runtime behavior or schema.
- Phase 98 is complete. Its documented limits remain: one shared local host,
  sequential concurrency stages, immediate synthetic approvals, and no real
  provider, HTTP/OIDC ingress or hosted capacity claim. Phase 99 becomes eligible
  after this completion record is committed, pushed and its CI passes.

- Completion record **`ee13c8cc0c0ff7201b76623bfdfaa2829edcd2e7`** was pushed.
  [CI 35178145081](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35178145081)
  passed all three jobs: **876 API tests in 439.16s**, 65 web smoke tests,
  migration/lint/typecheck/build/Compose checks and both dependency audits.
  All commit check runs independently confirmed success. Phase 99 is eligible.

### Phase 99 — Crash and Concurrency Reliability Experiments

- Plan (2026-09-17 UTC, authorized Phases 66–105): inspected queue admissions,
  leases/fencing, worker shutdown, effect receipts, approval/cancel transitions,
  parallel joins, scheduler arbitration and linked recovery. Reuse existing
  deterministic graph and governed HTTP fixtures, preserving runtime behavior.
- Add explicit process-kill boundaries, expired ownership/duplicate delivery,
  timeout after a sink write with and without provider idempotency, recorded
  reconciliation, approval/cancel and scheduler races, dead-letter recovery,
  graceful overlapping worker replacement and a real PostgreSQL service outage.
  The outage owns a newly created, labeled Docker container; existing preview
  and benchmark databases are not outage targets.
- Capture admitted IDs, timestamps, persisted jobs/attempts/events/effects and
  sink observations before/after faults. Reconcile every accepted execution and
  queued-job admission against terminal history, including explicitly expected
  failures and unknown remote outcomes. Measure recovery intervals and actual
  duplicate prevention. Publish hashed raw evidence and a failure analysis.
- Acceptance: focused real-PostgreSQL fault tests, three full local repetitions,
  independent evidence verification, Ruff, relevant adjacent regressions if a
  runtime defect needs fixing, phase-scoped commit/push, all CI and post-push
  review. No migration, UI or paid/external provider work is planned. Cross-platform
  graceful worker replacement exercises the worker stop event; operating-system
  SIGTERM/container rollout validation remains in Phases 100–102.

- Implemented 15 real fault/race scenarios, a cross-platform worker subprocess
  fixture, controlled timeout-after-write sink, exclusively owned outage container,
  independent job/effect reconciliation and a repeated-run/offline-verification
  command. Existing HTTP test fixtures gained only an optional timeout argument,
  preserving their prior default. No application runtime, migration or UI changes.
  Method and commands: [RELIABILITY_EXPERIMENTS.md](RELIABILITY_EXPERIMENTS.md).
- Initial focused run: **14 passed**, with the outage case failing on a fixture
  model lookup before its fault. Corrected that lookup and a metadata keyword
  collision. A subsequent outage reached service restart but failed host
  readiness; the fixture now specifies a stable loopback port across restart.
  The corrected real outage test passed **1/1 in 24.07s**, with its container
  removed afterward. These were harness findings, not application runtime fixes.
  Logs: `.phase99-focused.log`, `.phase99-outage.log`,
  `.phase99-outage-recheck.log`, `.phase99-outage-stable-endpoint.log`.
- Ruff passed. The full command is running three repetitions with fixed measured
  Python sources under `docs/evidence/phase99-full`; no full-run outcome is
  claimed yet. All CI, post-push review and delivery records remain outstanding.

- Full experiment completed **2026-09-17 03:51:05–03:59:27 UTC**, exit 0:
  **45/45 scenarios passed**, no skips, in three repetitions of 15 cases
  (164.92s / 163.92s / 166.87s). Reconciliation accounted for **72 accepted
  workflows**, **279 terminal jobs**, **234 attempts**, and **12 intended effects**.
  There were **54 completed, 9 expected failed and 9 expected cancelled runs**;
  **3 deliberately unresolved outcomes remained unknown**. No lost jobs/effects
  or duplicate effects; 18 sink requests included six prevented duplicate writes.
- The separate offline check recomputed all results, matched **220 runtime/
  migration/lock hashes plus 96 test-source hashes**, and confirmed each timeout
  case's actual adapter/operator/unknown outcome. Final Ruff passed; all owned
  outage containers were removed. Logs: `.phase99-full.log`,
  `.phase99-offline-verification.log`. [Measured report](RELIABILITY_RESULTS.md)
  links the approximately 330 KB manifest, 45 hashed raw archives and per-run
  pytest/JUnit evidence. No unrelated frontend checks were required locally.
- Local review checked subprocess ownership/cleanup, isolated outage scope,
  accepted-ID and queued-event reconciliation, explicit expected failures,
  immutable source history, stable effect identities, unresolved-outcome policy,
  bounded race fixtures and honest timer/auth/deployment limits. No blocking
  runtime findings. The phase exceeds the preferred line count because it adds
  independent process/HTTP/database fixtures, 15 scenarios, archive verification
  and reproducible analysis rather than only test-count claims. Phase commit,
  push, all CI and post-push review remain required before completion.

- Implementation **`8d4582845201cb27f01bbffcfbd48a3ea3d7cef0`** was pushed
  to `main`. [CI 35180407041](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35180407041)
  passed Web and Compose but failed the API suite: **890 passed, 1 failed in
  626.74s**. On the faster Linux host, PostgreSQL restarted before the fixture's
  half-second lease expired; renewal was correctly allowed. The test had assumed
  restart necessarily outlasted that lease. This is a fixture timing defect,
  not an application fencing failure; Phase 99 remains incomplete.
- Fix: wait for the persisted PostgreSQL lease deadline before asserting stale
  renewal rejection and recovery. Rerun all 15 fault scenarios with separate raw
  evidence in `docs/evidence/phase99-fix`. Post-push review also found that the
  shared environment helper supplied a Phase 98 single-process scope label;
  correct that descriptive label for the actual multiple-process fault suite,
  preserving original source fingerprints and raw measurement archives.

- Fix validation: all **15/15 scenarios passed in 182.08s** on
  2026-09-17 04:15:19–04:18:24 UTC, command exit 0. Separate raw evidence
  reconciles 24 accepted runs, 93 jobs, 78 attempts and four effects, with no
  loss/duplication and one deliberately unknown outcome. All 316 source hashes
  matched after measurement. Logs: `.phase99-fix-validation.log` and
  `.phase99-fix-verification.log`. The subsequent descriptive scope correction
  preserves both manifests' raw archives and measured source hashes, and records
  the previous label/reason explicitly. Fix commit/push and passing CI remain due.

- Fix **`bfe6c73c6ceadffde8aae5b9c10d4e32d8364754`** was pushed to `main`.
  [CI 35181619634](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35181619634)
  passed all three jobs: **891 API tests in 859.35s**, including the real Linux
  database outage, Ruff, fresh migration and API audit; **65 web smoke tests**,
  lint/typecheck/build and web audit; Compose configuration. Both audits found
  no known vulnerabilities. The commit check-runs endpoint independently
  confirmed every job completed successfully.
- Post-fix review confirmed the fixture observes PostgreSQL's actual deadline,
  respects valid leases and verifies expired ownership before reclamation.
  The corrected scope label is explicit, with prior metadata retained and no
  raw measurement changes. No unresolved blocking findings; no application
  runtime, migration or UI changes were required by this phase.
- Phase 99 is complete. Limits remain documented: controlled local effects,
  development identity fixtures, small fault samples, explicit worker restart
  after database loss, and stop-event rather than OS/container rollout testing.
  Phase 100 is eligible after this completion record is committed, pushed and
  all of its CI checks pass.

### Phase 100 — production container packaging

- Phase 99 completion record `894f3429153c867fd9dc1e21fc99d0bbfd07dbf4`
  was pushed. [CI 35182643896](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35182643896)
  passed all three jobs, independently confirmed through commit check-runs:
  **891 API tests in 632.32s**, 65 web smoke tests, lint/typecheck/build,
  fresh migration, Compose and both dependency audits (no known vulnerabilities).
- Plan: preserve development Compose, existing authentication/session/RBAC,
  workflow semantics and all retained databases. Add separate non-root production
  images, standalone web output, secret-file loading, production configuration
  guards, bounded resources/logging, dependency readiness and worker health.
  Add one-shot migrations and explicit local verification with ephemeral TLS/OIDC
  credentials, a disposable persistent PostgreSQL volume and deterministic graph.
- Acceptance: build/start actual images; verify signed authentication and web/API
  routing; publish/start/approve/complete a workflow; reject unauthenticated access;
  observe readiness failure/recovery, persistence after restart and real container
  SIGTERM drain or fenced recovery. Inspect image/configuration for secrets and
  root privileges. Record commands, image IDs, actual outcomes and limitations.
- Rollout: no schema change planned. Migrate once before starting compatible API
  and worker images; stop claims and allow active work to drain within termination
  grace. Provider keys and external destinations remain empty in validation.
  Kubernetes and hosted deployment remain scoped to Phases 101–102.

- Initial validation: production API/web images built successfully, and the
  isolated database migrated through `f097_worker_presence`. The owned production
  stack startup command exited 0. These results do not yet prove authenticated
  workflow, restart, readiness-failure or SIGTERM acceptance; the verifier has
  not run. Ruff and frontend typecheck passed. Focused backend run: **41 passed,
  one setup error in 562.18s**, caused by a PostgreSQL statement timeout while
  creating a fixture table; requires investigation/rerun. The first test command
  named a nonexistent worker test file and collected no tests; corrected command
  used `test_production.py`, `test_identity.py`, `test_durable_queue.py` and
  `test_worker_leases.py`. Frontend lint rejected CommonJS `require` in the new
  launcher; changed the launcher to ESM imports. Lint recheck and image rebuild
  remain required. Logs: `.phase100-build.log`, `.phase100-migrate.log`,
  `.phase100-focused-recheck.log`, `.phase100-web-lint.log`.
- Automatic approval review rejected a subsequent database/startup inspection
  because account usage was exhausted. Existing process results were collected
  and local code corrections preserved. No Phase 100 commit/push or CI run has
  occurred; Phase 100 remains incomplete and Phases 101–105 have not started.
- The ESM launcher correction is present in the worktree. Its sandboxed lint
  recheck could not start Node because access to the user installation was denied
  (`EPERM`); it did not pass. `git diff --check` passed. Static review strengthened
  the pending shutdown verifier to require outstanding work before SIGTERM,
  zero running jobs after clean exit and unchanged claim counts while stopped.
- Account status subsequently reported available usage and approval review
  accepted validation commands again. The corrected frontend passed lint and
  **65 smoke tests**; all **42 focused backend tests passed in 300.11s** on rerun.
  The earlier DDL timeout did not recur. Ruff passed across runtime, tests,
  secret entrypoint and deployment scripts.
- Actual deployment inspection found Caddy's bundled file capability conflicted
  with dropped container capabilities. Added a non-root gateway image that removes
  the unused low-port capability and an explicit health probe. Fixed scratch
  directory ownership. A negative host test exposed Caddy directive reordering;
  explicit `route` order now checks hosts before proxying. Preserved failed
  verification manifests, including a subsequent HTTPX client-lifecycle fixture
  error; corrected that fixture. Signed OIDC login and host rejection then passed.
  Complete workflow/restart/shutdown acceptance is still running, not yet claimed.
- Acceptance found a startup-signal/readiness race: an early SIGTERM could arrive
  before Python installed its handler, while hostname-based health matched a
  previous process heartbeat. Added container init, an entrypoint-generated worker
  instance identity and exact-instance readiness, with a regression rejecting a
  previous live heartbeat. The affected **33 tests passed in 207.35s**.
- Final main deployment check passed on **2026-09-17 05:59:09–06:01:47 UTC**:
  **9 accepted/completed workflows and 203 completed jobs**. Verified signed OIDC
  and secure cookies, 401/421 negative checks, version/approval output, exact
  approval/session persistence after restart, API/web 503 on database loss,
  liveness 200, clean SIGTERM, stable stopped claim count and backlog completion.
  [Manifest](evidence/phase100-final/summary.json) and hashed gzip archive retain
  accepted IDs, job records, source fingerprints and measured image IDs.
- Independent review matched **195 recorded source hashes**, rechecked archive
  and job/run invariants, verified the published definition in authenticated
  server-rendered HTML, and inspected actual non-root/read-only/init/resource/
  capability/logging configuration. No generated secrets in image metadata or
  environment/private-key files in application images; external tools/providers
  remained disabled. Both Compose profiles, Ruff, typecheck, frontend lint,
  65 smoke tests and whitespace checks passed.
- The principal SIGTERM observation had queued work, so a separate bounded
  disposable-database checkpoint lock proved active ownership drain. It observed
  a claimed job and draining heartbeat, released the checkpoint, required exit 0
  and zero recovery for the original job, then completed its continuation.
  Both the initial check and the final CLI repeat passed: **two additional runs
  and four jobs**, all completed. [Results and limits](PRODUCTION_CONTAINER_RESULTS.md)
  link successful and preserved failed evidence; [runbook](PRODUCTION_CONTAINERS.md)
  includes reproducible commands and migration/rollout order.
- Pre-commit review checked signal forwarding, process-specific readiness,
  authenticated proxy routing, secret boundaries, scratch permissions, resource
  limits, immutable evidence and preservation of existing databases. No unresolved
  blocking local findings. The phase exceeds the preferred line count because
  separate runtime profiles, TLS/OIDC fixtures, fault verification and lossless
  evidence are required for an actual deployment gate. Implementation commit,
  push, all CI and post-push review remain required; Phase 101 has not started.
- Implementation **`d7d172cf58c3ecb8c7a0df2da5d0b08039e0bcdb`** was pushed
  directly to `main` (40 files, 2,066 insertions and 20 deletions, including
  retained evidence). [CI 35188845395](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35188845395)
  passed all three jobs: **896 API tests in 635.28s**, Ruff, fresh migration and
  API audit; **65 web smoke tests**, lint/typecheck/build and web audit on Node 24;
  development/production/verification Compose validation. Both dependency audits
  found no known vulnerabilities. Commit check-runs independently confirmed all
  three jobs completed successfully.
- Post-push review checked all Phase 100 acceptance clauses against code and
  measured evidence, including actual active-lease drain rather than relying on
  a queued-only shutdown sample. Existing workflow semantics and migrations are
  preserved; signal/readiness changes have focused regression and container
  evidence. No unresolved blocking findings or post-push fix commit was needed.
  Phase 100 is complete. Hosted/Kubernetes operations remain unperformed in this
  phase; fixture identity, database-role and image-audit limits are documented.
  Phase 101 is eligible after this completion record is committed, pushed and
  all of its CI checks pass.

### Phase 101 — Kubernetes deployment manifests

- Phase 100 completion record **`753daaace23675032af348263deeeacbbe074a2d`**
  was pushed. [CI 35189765309](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35189765309)
  passed all three jobs: **896 API tests in 630.84s**, 65 web smoke tests,
  lint/typecheck/build, fresh migration, all Compose profiles and both audits
  with no known vulnerabilities. Independent commit check-runs confirmed success.
- Plan: reuse the measured production runtime/authentication and deterministic
  fixture. Add Kustomize base/local/hosted profiles, services and TLS ingress,
  configuration/secret references, one-shot migration Job, persistent local
  PostgreSQL and operator worker-metrics export. App service accounts have no
  Kubernetes API token; the ingress controller gets only required discovery RBAC.
  Configure resources, startup/readiness/liveness behavior, rollout and termination.
- Use an owned kind cluster, pinned node image and workspace-local verified CLI
  binaries. Always pass the owned kubeconfig; preserve the user's default context,
  existing preview/benchmark database and Phase 100 named volume. Stop only the
  owned Phase 100 services when needed to free their loopback port/resources.
- Acceptance: render/schema-check both profiles; deploy local infrastructure,
  run migration to completion before app workloads, authenticate through real
  ingress, publish/approve/complete a deterministic graph, inspect worker metrics
  and verify run/approval persistence after pod replacement. Record actual cluster,
  image, source and result evidence. Hosted deployment is configuration-only unless
  a target/access is supplied; do not claim it ran.
- No schema migration is planned. Ensure image-level signal forwarding works in
  Pods independently of Compose's `init` option. Rolling updates, replica scaling,
  fault/effect reconciliation, backup/restore and rollback remain Phase 102 scope.
- Implemented base/local/hosted Kustomize profiles, separate ingress RBAC and
  TLS routing, persistent local PostgreSQL, referenced Secrets, migration Job,
  resource/probe/termination settings and operator metrics CronJob. Added verified
  local CLIs, ownership-checked ordered deployment and authenticated acceptance
  helpers, runbook and retained evidence. CI now renders both profiles and lints
  deployment scripts. API/fixture images use `tini`; web API routing recognizes
  Kubernetes without Docker's marker file, with a behavioral regression test.
- Local acceptance passed **2026-09-17 07:29:11–07:30:17 UTC** on kind v0.33.0 /
  Kubernetes v1.37.0 / containerd 2.3.4. Fresh migration reached f097 before app
  Pods; authenticated TLS ingress, published version, idempotent start, approval,
  output 42, SSR and tenant/operator metrics passed. **1 run, 3 jobs, 2 attempts**
  completed; zero stale/recovered/abandoned claims. Database/API/worker Pod UIDs
  changed while the PVC, session, version, approval and output persisted.
- Validation: both rendered profiles passed actual server schema dry-run;
  production runtime **5 tests passed in 99.21s**; web **66 tests passed**,
  typecheck/lint, deployment Ruff, production builds, documentation links/fences
  and diff whitespace passed. Independent inspection matched **33 source hashes**,
  archive SHA, run/approval/version and actual Pod security/resources. Live RBAC
  denied runtime Secret listing and ingress access to application Secrets.
- Corrected before commit: wrong initial API build context; kubectl multi-object
  JSON parsing; web readiness failure from Docker-only container detection. The
  web rollout failed its gate, was fixed/tested/rebuilt under a new tag, and then
  passed full acceptance. Failed-attempt logs remain in the evidence archive.
- Evidence: [Kubernetes results](KUBERNETES_RESULTS.md),
  [manifest](evidence/phase101/summary.json),
  [independent review](evidence/phase101/independent-review.json),
  [cluster archive](evidence/phase101/cluster-evidence.json.gz) and
  [validation logs](evidence/phase101/validation-logs.json.gz).
- Scope is larger than the usual commit range because complete app/ingress/local/
  hosted resources, safe deployment/verification helpers and measured evidence
  are required together. No future-phase recovery experiment is included.
  Hosted deployment is **not performed**; configuration/schema validation is
  separate from local deployment.
- Implementation `918db617eed8b749db3573f5d26a49339652e6fa` was committed and pushed
  to main. [CI 35195207152](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35195207152)
  passed all three jobs: **896 API tests in 635.71s**, **66 web tests**,
  lint/typecheck/build, fresh migration, both Kubernetes renders and all Compose
  profiles. Both dependency audits found no known vulnerabilities. Independent
  commit check-runs confirmed all checks completed successfully.
- Post-push review covered phase scope, migration ordering, retained data,
  authentication/routing, secret handling, runtime/ingress RBAC, probes/resources,
  shutdown behavior, helper reruns, error gates and compatibility. No blocking
  findings remain; no post-push fix commit was required. The retained
  cluster has all five application Deployments and PostgreSQL ready, its original
  PVC bound, and no controller errors in the inspected ingress log.
- **Phase 101 complete.** Phase 102 is eligible after this completion record is
  committed, pushed and its CI passes. Hosted deployment remains unperformed;
  local acceptance is not evidence of hosted availability or production security.

### Phase 102 — Kubernetes operations and recovery verification

- Authorized range remains Phases 66–105. Phase 101 completion record
  `ca281b73363d3c7b8dc6624aa0731c2beba8d21a` was pushed;
  [CI 35196311434](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35196311434)
  passed **896 API tests in 634.39s**, 66 web tests and all other checks/audits.
  Independent commit check-runs confirmed success. The working tree was clean.
- Inspected the phase requirements, consolidated plan, context documents, deployed
  profiles, durable queue/lease fencing, tool contracts/effect ledger and existing
  HTTP/reliability fixtures. Reuse the owned Phase 101 cluster, synthetic identity,
  pinned images and persistent database; preserve all prior datasets/evidence.
- Plan: add a local-only persistent idempotent HTTP sink and operations harness.
  Generate approved deterministic tool workflows through authenticated ingress,
  retain every accepted run ID, and reconcile database effects with sink receipts.
  Scope its destination to the owned Service IP; keep paid providers disabled.
- Exercise a distinct compatible API/worker image release, replica scaling, active
  worker Pod loss, a paused owner that outlives its lease and resumes after recovery,
  and database dependency readiness failure. Record actual observations, probe/
  rollout states, image/cluster/source IDs, logs, metrics and recovered histories.
  The release may change packaging metadata only: disclose that this tests rollout
  and rollback mechanics at the same application/schema version.
- Back up a quiescent disposable dataset with binary-safe PostgreSQL tooling;
  restore into a fresh owned database and compare version, approval, attempt and
  effect identities/content. Retain the original database and backup. Roll back
  only compatible images; no destructive schema downgrade is authorized or needed.
- Acceptance requires all accepted work accounted for, zero duplicate effects in
  the controlled idempotent sink, stale ownership unable to mutate completed
  history, and restored version/approval/effect evidence matching the backup.
  Add focused sink correctness tests and a repeatable operations runbook. No
  production schema/API feature change is planned. Hosted access remains absent
  and optional; no hosted execution will be claimed.

- Implemented a separate operations Kustomize profile, durable SQLite HTTP sink,
  owned-cluster harness, binary-safe backup/restore and compatible image fixture.
  CI now renders the operations profile. No application/schema behavior changed.
- Full deployed suite passed **2026-09-17 08:30:38–08:36:58 UTC**: 21 accepted
  workflows completed, 21 distinct effects from 23 requests, zero lost/duplicate
  effects. Verified active rollout (19 HTTP pairs all 200/200), three-worker
  scaling, active Pod loss, resumed stale-owner fencing, health 200/readiness 503
  during DB outage, exact 11-table fresh-database restore, sink PVC retention and
  compatible image rollback. Release metadata changes only; code/schema unchanged.
- Preserved two failed harness attempts: successful reconciled effects initially
  omitted by an assertion; then synthetic five-minute session expiry at final
  reconciliation. Corrected the harness before commit, preserving auth semantics.
  Their 17 and 21 accepted runs all completed. Independent final-history hashes
  matched both prior post-failure records; no previous work was lost or changed.
- Across all attempts: 59 completed tool workflows, 59 effects, 64 requests. With
  Phase 101 retained: 60 completed runs, 180 completed jobs, 120 completed attempts,
  five failed abandoned attempts/recoveries and one running worker, no stale jobs.
- Validation: `uv run --directory apps/api pytest tests/test_operations_sink.py`
  **2 passed in 3.73s**; Ruff across src/tests/deploy passed; full operations CLI
  exited zero. Independent review verified 25 source hashes, raw archive SHA,
  all run/version/approval/effect relationships, live baseline-image readiness,
  backup bytes/hash and all 11 restored table content hashes. No hosted run.
- Evidence: [operations results](KUBERNETES_OPERATIONS_RESULTS.md),
  [runbook](KUBERNETES_OPERATIONS.md), [manifest](evidence/phase102-final/summary.json),
  [independent review](evidence/phase102-final/independent-review.json),
  [raw archive](evidence/phase102-final/operations-evidence.json.gz),
  [metrics](evidence/phase102-final/worker-metrics.txt) and
  [validation logs](evidence/phase102-final/validation-logs.json.gz).
- Scope exceeds the usual line target because the complete operations harness,
  persistent fixture, focused tests, reproducible runbook and all attempt evidence
  are one acceptance unit (23 files, 2,173 insertions and four deletions).
- Documentation validation checked 15 local links and balanced fences; staged
  `git diff --check` passed. Implementation
  `3c30652fbc6d8f8039ddb2d8b4b46c6571c9c8ed` was committed and pushed to main.
  [CI 35200997403](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35200997403)
  passed all three jobs: **898 API tests in 662.41s**, **66 web tests**, fresh
  migration, lint/typecheck/build, three Kubernetes renders and Compose profiles.
  Both dependency audits found no known vulnerabilities. Commit check-runs
  independently confirmed every check completed successfully.
- Post-push review checked the phase requirements, fixture durability/concurrency,
  accepted-work reconciliation, lease fencing, approval/version history, binary
  backup handling, fresh-database safety, source/image provenance, cleanup/reruns,
  error gates and compatibility. No blocking findings remain; no post-push fix
  commit was required. All original databases, volumes and failure evidence remain.
- **Phase 102 complete.** Phase 103 is eligible after this completion record is
  committed, pushed and its CI passes. Hosted operation remains unperformed;
  controlled sink idempotency and a metadata-only release limit the claims.

### Phase 103 — Platform README and architecture reconciliation

- Phase 102 completion record `096a088b5ed47dd9f460b48a0e6a3c1eb9b48645`
  was pushed; [CI 35202236737](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35202236737)
  passed all API, web and deployment jobs. Commit checks independently confirmed
  success. The working tree was clean before this phase.
- Inspected the context/plan, existing docs, executor registry, state/queue/models,
  permissions, business template projections, evaluation calculations and seeded
  records, deployment configuration and Phase 98–102 measurements. Found stale
  future-tense claims, old shared-key deployment guidance, an absent LLM judge,
  unsupported illustrative quality claims and five broken README image links.
- Plan: lead with the implemented durable platform, preserve business examples,
  and reconcile README, overview, specification, architecture, agents, observability,
  deployment, security, evaluation and backlog. Add R01–R14 code/test/evidence
  mapping; distinguish completed capabilities, seeded examples, measured local
  results and unperformed hosted/provider checks. Correct stale cross-references
  in earlier runtime docs without rewriting historical phase records.
- Acceptance: verify all local links/anchors, fenced examples, unique continuous
  phase numbering, complete requirement coverage, route/command/source references,
  diagrams and numeric claims. Documentation only: no application/schema change,
  data mutation, deployment or unrelated local test suite is required. CI still
  must finish before closure. Demo script and case study remain Phases 104–105.
- Reconciled the core documents and earlier runtime cross-references. Added the
  [R01–R14 index](PLATFORM_EVIDENCE.md), preserved business screenshots in a labeled
  [historical tour](BUSINESS_TOUR.md), and moved optional telemetry instructions to
  [their own page](TELEMETRY.md). Removed invented target-performance claims and
  explicitly retained the actual assigned baseline/multi-agent/showcase values.
- Clarified a source-review finding: builder publication requires runnable
  validation, while direct API publication can retain a recognized unavailable
  handler. Every start independently checks executable capability. No runtime
  behavior was changed to reconcile the prose.
- Added `scripts/check_documentation.py` and its CI configuration step. Initial
  validation passed 47 documents, 406 links/anchors, 105 ordered unique phase
  headings and both complete R01–R14 tables. Ruff passed for the checker; diff
  whitespace checks passed. No unrelated local application suite or deployment
  was rerun for documentation. [Semantic review](evidence/phase103/semantic-review.json)
  records source hashes, route/command checks, numeric provenance and limitations.
- The larger documentation scope removes obsolete duplicate specification and
  overview material across the requested documents while preserving historical
  phase records, screenshots and runtime behavior. This is one reconciliation
  phase, not several combined feature phases.
- Implementation `242c611610a1f1105d989b5ba2aa4cd7824a4995` was pushed to main.
  [CI 35205261374](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35205261374)
  passed API, Web and Docker Compose: **898 API tests in 626.04s**, **66 web
  tests**, migration, lint/typecheck/build, deployment renders and documentation
  validation. Both dependency audits found no known vulnerabilities; commit
  check-runs independently confirmed all checks completed successfully.
- Final local documentation validation passed **47 documents, 411 links**, all
  105 phase headings and both R01–R14 tables. All 24 normalized source hashes
  in the semantic review matched after push. Read-only browser review on a
  separate native preview verified the builder's eight primitives, saved draft,
  two retained published versions, capability/diff and manual-start controls.
  No saved data changed. The old preview had stale build assets; the separate
  preview served the current build without stopping existing services.
- Post-push review checked requirements, source/route/command fidelity, seeded
  versus measured values, permission and effect boundaries, state compatibility,
  documentation gate behavior and future phase scope. No blocking findings or
  separate fix commit were identified in that review. Phase 104 becomes
  eligible after this completion record is pushed and its CI passes. Hosted and
  paid-provider checks remain explicitly unperformed.
- Additional consistency review found the tracker’s separate Next Phase block
  still naming Phase 102, plus historical future-tense adapter and permission
  statements in the graph/identity references. Reopened Phase 103 to correct
  those descriptions in a separate fix; no runtime or schema changes. Final
  closure now depends on the fix CI and follow-up review.
- Fix validation: `uv run --directory apps/api python
  ../../scripts/check_documentation.py` passed 47 documents and 412 local links;
  `git diff --check` passed. Permission names were checked against
  `services/permissions.py`. The original semantic-review hashes describe the
  implementation commit; this follow-up intentionally changes its graph prose.
- Earlier completion record `0356b3508ffa41c37ae02d5082333c5f8a727433`
  passed [CI 35206695377](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35206695377):
  898 API tests in 512.59s, 66 web tests and all deployment/documentation checks.
- Fix `39b8f4f0cd22902bf33edbeec8de46b883e5901f` was pushed after that run
  finished. [CI 35207650946](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35207650946)
  passed all jobs: **898 API tests in 878.75s**, **66 web tests**, migration,
  lint/typecheck/build, deployment renders, documentation validation and both
  audits with no known vulnerabilities. Independent commit check-runs confirmed
  success. The slower API run was allowed to finish without cancellation.
- Follow-up review checked the exact three-file diff, current status consistency,
  implemented adapters and permission source. No blocking findings remain.
  **Phase 103 complete** after implementation and separate fix validation/push/
  review. This final record must pass CI before Phase 104 implementation begins.

### Phase 104 — Platform demo video script

- Phase 103 final record `4653f1b4f6bfa914333f95df2ae9372efc012401` was pushed;
  [CI 35209139612](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35209139612)
  passed all jobs. The repository was clean before this phase.
- Inspected the phase, builder/publication/debugger, generic and business approval
  APIs/UI, demo seeds, deterministic provider test fixtures, retry behavior,
  permissions and recorded benchmark/Kubernetes results. Existing demo walkthrough
  used an obsolete button label and did not cover the generic platform.
- Plan: write a five-minute script and update reproducible setup/scene instructions.
  Add a development-only example fixture in a fresh explicitly named loopback
  database: assigned business comparisons, synthetic sales provider responses,
  and a condition/approval/local HTTP-read graph with one deliberate retry.
  Walk through publication, manual admission, generic API approval, attempts,
  sales edit/reapproval/output and comparison screens against the actual app.
- Acceptance: exact visible controls/routes, real retained transitions with
  synthetic model responses labeled, correct timing/links/numbers, measured
  reliability/deployment evidence separate from assigned evaluation values,
  and tenant-permission claims tied to recorded authenticated checks. No video
  generation, paid/provider calls, new production features, schema migration or
  deployment. Existing databases, services and completed evidence stay intact.
- Added the [five-minute script](DEMO_SCRIPT.md), replaced stale setup in the
  [walkthrough](demo-walkthrough.md), and linked both from README/R14 evidence.
  The optional `examples.demo_fixture` helper guards loopback development/demo
  databases, uses three synthetic model response schemas without network fallback,
  and exposes only a read-only loopback fixture. CI lint now covers examples.
- Actual fresh database `phase104_demo_20260917` migrated to existing head and
  seeded **32 cases, 65 historical runs/results, 99 AgentSteps**. A separate sales
  run paused for real approval. Native API/web/fixture ports 8008/3109/8144 were
  unused before startup; original resources and databases remain intact.
- Browser rehearsal validated/published the draft, started both condition paths,
  inspected a waiting generic gate, and followed the documented API decision.
  The tool retained failed `tool_unavailable` and completed attempts with a
  **5.134355s** gap. The false branch skipped approval/tool execution. Sales
  **Save Edits** created a replacement approval; **Approve** released the writer,
  and the final report contains the exact edited recommendation. All three
  executions completed. Comparison, evaluation, costs, account and operations
  scenes were inspected; no correction/provider action was invoked.
- Precommit rehearsal corrections: normalize graph defaults before saving so the
  builder does not show a spurious missing-role warning; use the actual **Publish
  saved draft** label; explain that one worker drain may complete both retry
  attempts. The owned draft was normalized before publication; no old version
  or prior acceptance dataset was rewritten.
- Validation: `uv run --directory apps/api pytest tests/test_demo_walkthrough.py
  -q` passed **5 tests in 2.19s**; Ruff passed examples and the focused test. Live
  negative seed checks rejected existing manifests/runs with counts unchanged
  at 66 business runs and three executions. All eight narration windows fit
  140 words/minute: **563 spoken words**, approximately 241 seconds plus 59
  seconds of holds. This is an editorial timing estimate, not a recorded video.
- [Rehearsal evidence](evidence/phase104/summary.json) links source hashes and
  compressed retained API records. No application/schema feature, live provider,
  hosted deployment or new reliability experiment is claimed. The change includes
  setup, safe fixture code/tests and reviewable evidence because the script must
  be reproducible against actual UI. Implementation push/CI/review remain pending.
- Implementation `677c6bbbbc22cec810a5bae51fe05389feb24f95` was pushed to main;
  [CI 35212338200](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35212338200)
  is being allowed to finish before any fix push. Post-push archive/source/timing
  checks matched all four recorded hashes, three completed execution IDs and
  all eight scene windows.
- Post-push review found that SQLAlchemy URL query options can override the host
  or database inspected by the example guard. A no-connection dialect check
  demonstrated both overrides. The separate fix rejects all URL query options,
  documents the simple connection form and adds regression cases for host and
  database overrides. This changes only the optional fixture guard, not runtime
  execution or existing records. Original rehearsal evidence remains unchanged.
- Fix validation: **7 focused tests passed in 5.35s**; Ruff passed; documentation
  validation passed 48 documents/444 links. The implementation and fix must both
  finish CI and review before this phase is marked complete.
  [Separate fix evidence](evidence/phase104/fix-review.json) records the revised
  source hashes and confirms that the normal simple demo URL remains accepted.
- Implementation CI passed all jobs: **903 API tests in 625.24s**, **66 web
  tests**, migrations, lint/typecheck/build, deployment/documentation checks and
  dependency audits with no known vulnerabilities. Query-override fix
  `91335923e454e6c93bf2ce2c37a8afee10c3e22a` was then pushed; its CI must finish
  before the next fix push.
- Follow-up inspection identified a second example-only gap: tenant-scoped ORM
  preflight could miss another organization's work even though workers claim
  globally. The next separate fix requires a single local organization before
  seeding or draining, and documents exclusive use of the disposable database.
  A real PostgreSQL test added a second tenant in a fresh isolated schema and
  verified both seed and drain reject it before any worker starts.
- Second fix validation: **8 tests passed in 17.65s**, including that PostgreSQL
  test; Ruff and 48-document/445-link validation passed. Existing application
  tables, browser fixture records and original rehearsal archives are preserved.
  [Additional fixture review](evidence/phase104/tenant-guard-review.json) records
  this finding and its revised source fingerprints. Completion still awaits
  all fix CI and follow-up review.


- Query-override fix `91335923e454e6c93bf2ce2c37a8afee10c3e22a` passed
  [CI 35213352297](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35213352297):
  **905 API tests in 632.51s**, **66 web tests**, and all other jobs/audits.
- Single-organization fix `705566430be1bd8a3cfa3c70744b735a9a557494` was then
  pushed and passed
  [CI 35214506317](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35214506317):
  **906 API tests in 527.93s**, **66 web tests**, migrations, lint/typecheck/build,
  deployment/documentation checks and both audits with no known vulnerabilities.
  Independent commit check-runs also reported all three jobs successful.
- Final review matched all ten recorded source hashes against their respective
  implementation/fix commits and the unchanged original archive SHA-256. Reviewed
  the organization query, pre-worker guard placement, real PostgreSQL regression
  and exclusive-database instructions. No blocking findings remain. Final local
  documentation validation covers 48 documents and 446 links.
- **Phase 104 complete.** The 861-line implementation addition includes the
  reproducible fixture, regression tests and evidence alongside the script;
  this exceeds the suggested size to keep the phase independently reproducible.
  Both follow-up fixes are separate commits. No paid-provider execution, generated
  video, hosted acceptance or production runtime/schema change is claimed.
  Phase 105 begins only after this completion record is pushed and its CI passes.


### Phase 105 — Final workflow platform case study

- Phase 104 completion record `a6e51114f1da1140e2da82a81ce9cbc0588633f3`
  was pushed; [CI 35215466462](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35215466462)
  passed all jobs. Repository main was clean and matched origin before this phase.
- Inspected the required context, final phase scope, architecture/security/tool
  contracts, evaluation source constants, benchmark/fault/deployment reports,
  actual demo rehearsal, evidence manifests and per-phase delivery records.
- Plan: add a recruiter-readable final case study covering the problem, goal,
  architecture, three business examples, evaluation method/results, measured
  reliability/deployment, tradeoffs, lessons and future work. Link it from README
  and the R14 evidence row; retain an explicit R01–R14 completion checklist.
  Reconcile historical planning language without changing scope or phase IDs.
- Acceptance: trace every capability/number to source or retained evidence;
  separate assigned scores, local measurements and unperformed external checks;
  review diagram/setup links and all completed-phase commit/CI evidence. Run
  documentation validation and inspect the pushed diff; await every CI job.
- Migration/rollout: documentation and evidence only. No application behavior,
  schema, deployment, provider traffic, credentials or existing dataset changes.
  The autonomous run is closed only after implementation CI and final review.


- Added the [final case study](CASE_STUDY.md): architecture diagram, design
  tradeoffs, business-agent paths, exact assigned comparison tables, measured load,
  fault/deployment results, actual lessons and a complete R01–R14 checklist.
  README and the evidence index link it. Historical plan wording now distinguishes
  original planning from current delivery; all Phase 1–65 definitions are unchanged.
- Validation: `uv run --directory apps/api python
  ../../scripts/check_documentation.py --output
  ../../docs/evidence/phase105/documentation-check.json` passed **49 documents,
  533 local links, 105 ordered phase headings and both 14-requirement tables**.
  The case-study checklist separately contains each requirement once. Diagram,
  setup references and numeric claims were reviewed against source/results.
- [Final evidence review](evidence/phase105/review.json) checked **94 retained
  gzip archives** for SHA-256/JSON integrity and recorded 15 normalized source
  hashes. It verified **92 linked CI runs** (89 successful; three historical
  failures followed by recorded fixes/passing runs), **101 pushed commit IDs**
  and validation/review fields for all 39 completed expansion phases before 105.
  Numeric assertions matched load, fault and Kubernetes manifests. This is a
  read-only evidence review, not a rerun of provider/deployment experiments.
- No new runtime tests were added for this documentation-only phase. Required
  full application/build/deployment CI will run on the pushed implementation.
  Original archives and existing resources remain unchanged. Implementation
  push, completed CI and post-push review are required before final closure.


- Implementation `348309ed13592f832a79dd63c9019d659630e046` was pushed to main;
  [CI 35217099419](https://github.com/christiankfoury/agentops-workflow-platform/actions/runs/35217099419)
  is running. All 15 source hashes in the review artifact match that pushed commit.
- Post-push review found ambiguous graph wording: quality revision does not permit
  cyclic edges. A separate documentation fix now says edges remain acyclic while
  a bounded policy repeats a declared region with logical iteration identity.
  Checked `graph_validation.py`, `WORKFLOW_GRAPH.md` and `LLM_EXECUTION.md` against
  the claim. No runtime change or new test is needed; documentation/diff checks
  cover the change. [Fix review](evidence/phase105/fix-review.json) preserves its
  source fingerprint separately from the original implementation evidence.
  Fix validation passed 49 documents/536 links, ordered phase/requirement coverage
  and `git diff --check`. The implementation CI must finish before this fix is pushed.

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
