# Agentic Engineering Protocol

This repository is built phase by phase from:

- `docs/overview.md`
- `docs/PROJECT_SPEC.md`
- `docs/phases.md`
- `docs/phase-progress.md`

The goal is to let an engineering agent continue implementation autonomously while keeping each change reviewable, tested, and scoped.

## Active Autonomous Run

Target range:

```text
Phase 21 through Phase 30
```

The agent should execute phases continuously in order from the current next phase until Phase 30 is completed, unless a stop condition is reached.

## Operating Loop

For each phase:

1. Read the project context docs.
2. Read the current phase in `docs/phases.md`.
3. Inspect the existing implementation before making assumptions.
4. Implement only the current phase scope.
5. Add or update focused backend/frontend tests.
6. Run relevant validation commands.
7. Review the implementation for correctness, reliability, maintainability, edge cases, and next-phase compatibility.
8. Fix actionable review findings in a separate change when applicable.
9. Update `docs/phase-progress.md`.
10. Commit the phase implementation to `main` with a detailed commit message.
11. Push the implementation commit to `main`.
12. If review finds issues, fix them in a separate commit.
13. Push the fix commit to `main`.
14. Continue to the next phase only after the phase is implemented, validated, committed, pushed, and reviewed.

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
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe -m pytest
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe -m ruff check S:\github-repos\agentops-workflow-platform\apps\api\src S:\github-repos\agentops-workflow-platform\apps\api\tests
pnpm --dir S:\github-repos\agentops-workflow-platform\apps\web typecheck
pnpm --dir S:\github-repos\agentops-workflow-platform\apps\web test:smoke
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
