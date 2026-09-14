# Agentic Engineering Protocol

This repository is built phase by phase from:

- `docs/overview.md`
- `docs/PROJECT_SPEC.md`
- `docs/phases.md`
- `docs/phase-progress.md`
- `WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md`

The goal is to let an engineering agent continue implementation autonomously while keeping each change reviewable, tested, and scoped.

## Autonomous Run Status

No autonomous phase run is currently active.

The previous autonomous target range is complete:

```text
Phase 46 through Phase 65
```

The current implementation is post-Phase 65. A documentation-only platform
expansion plan defines Phases 66–105; all remain planned, not started. The former
Phase 66 demo script and Phase 67 case study are now Phases 104 and 105.
Do not implement Phase 66 or later unless the user explicitly asks for an
autonomous phase run or asks to implement a specific phase. Editing the plan
does not authorize implementation, commits, pushes, or deployment of those phases.

Current user-directed focus areas include:

- Revising workflow algorithms and agent handoffs.
- Improving prompt/settings clarity.
- Polishing workflow run, approval, comparison, cost, and demo UI.
- Tightening recruiter-facing product storytelling.
- Improving CSS, responsive behavior, empty states, and visual hierarchy.

## Operating Loop

For each phase:

1. Read the context docs, consolidated feature plan, current phase, and dependencies.
2. Inspect the existing implementation before making assumptions.
3. Record the implementation plan, acceptance cases, and migration/rollout impact in `docs/phase-progress.md`.
4. Implement only the current phase scope and add focused tests where needed.
5. Run relevant validation and inspect the local diff before committing.
6. Update phase progress with changes and validation; stage only phase-owned files.
7. Commit the phase implementation to `main` with a detailed commit message.
8. Push the implementation commit to `main` during the authorized implementation run.
9. Review the pushed change for correctness, reliability, maintainability, edge cases, and compatibility; check relevant CI results.
10. Fix actionable review findings in a separate fix commit, run affected checks, and push.
11. Review the fix and repeat as needed until no blocking findings remain.
12. Record implementation/fix commit IDs, push/CI status, validation, review outcome, and limitations in phase progress; commit/push any final documentation record.
13. Continue only after the phase is implemented, validated, committed, pushed, and reviewed with no unresolved blocking findings.

For Phases 66–105, also apply the shared delivery gate in `docs/phases.md`.
Documentation-only planning work uses link, numbering, coverage, and consistency
checks; it does not activate this implementation loop.

## Scope Rules

- Keep each phase PR-sized.
- Do not implement future phases early.
- Prefer existing project patterns over new abstractions.
- Avoid unrelated refactors.
- Preserve existing user changes.
- Add migrations only when schema changes require them.
- Add frontend UI only when the current phase calls for UI.
- Keep tests focused on workflow-critical behavior.

## Validation Expectations

Run the narrowest meaningful checks first, then broaden when shared code changes.

Common commands:

```powershell
uv run --directory apps/api pytest
uv run --directory apps/api ruff check src tests
pnpm --dir apps/web typecheck
pnpm --dir apps/web test:smoke
```

If the bare full API test command hangs, run explicit API test files and report that clearly.

## Review Checklist

For every phase review, check:

- Correctness against the phase text.
- Safe workflow state transitions.
- Data persistence and schema compatibility.
- Error handling and missing-resource behavior.
- Retry/idempotency/concurrency risks where relevant.
- Whether tests cover the intended behavior and edge cases.
- Whether the next phase can build on the implementation cleanly.

## Commit Guidance

Use clear commit subjects:

```text
feat(api): add writer agent backend
feat(web): add final output view
fix(api): harden approval transitions
```

Commit bodies should mention:

- What changed.
- Why it changed.
- Tests or validation run.

For autonomous phase execution:

- Use one implementation commit per phase.
- Use one separate fixes commit per phase when review finds actionable issues.
- Push each commit directly to `main`.
- Keep phase implementation commits roughly 300-700 changed lines when feasible.
- If a phase cannot fit that size without becoming incomplete or unsafe, keep the commit scoped to the phase and explain the size in the final summary.
- Do not combine unrelated phases in one commit.
- Do not continue to the next phase until the current phase commit and any fix commit have been pushed.

Recommended implementation commit shape:

```text
feat(api): add sales writer agent

Implement Phase 17 writer agent support for sales report workflows.

- Adds writer execution service and endpoint
- Persists writer output as an agent step
- Stores final workflow output and completes the run
- Adds focused backend coverage

Validation:
- python -m pytest ...
- ruff check ...
```

Recommended fix commit shape:

```text
fix(api): harden writer input selection

Address Phase 17 review findings.

- Prefer human-edited analysis when present
- Reject writer runs without approved human approval
- Add regression coverage

Validation:
- python -m pytest ...
```

## Stop Conditions

Pause and ask for input if:

- Credentials, secrets, or external account access are needed.
- Requirements conflict with existing architecture.
- A destructive operation is required.
- Tests fail for reasons that cannot be resolved safely.
- The next phase requires a product decision not present in the docs.
