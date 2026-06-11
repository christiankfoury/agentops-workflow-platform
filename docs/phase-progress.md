# Phase Progress

Current next phase: Phase 20 - Cost Dashboard

Autonomous trial target: complete Phase 17 through Phase 20 in order.

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

## Next Phase

### Phase 20: Cost Dashboard

Expected scope:

- Create a cost dashboard.
- Show total spend, average cost per workflow, cost by workflow type, cost by agent, most expensive runs, and average retry cost.
- Include useful charts or tables for cost over time, cost per agent, cost per workflow type, and tokens by agent.
- Use the existing workflow and agent-step data; add backend read endpoints only if needed for the dashboard.

Do not implement customer feedback, incident workflows, evaluation dashboards, background jobs, auth, or deployment work in Phase 20.

## Last Known Validation Pattern

Recent phases used:

```powershell
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe -m pytest <focused API test files>
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe -m ruff check S:\github-repos\agentops-workflow-platform\apps\api\src S:\github-repos\agentops-workflow-platform\apps\api\tests
pnpm --dir S:\github-repos\agentops-workflow-platform\apps\web typecheck
pnpm --dir S:\github-repos\agentops-workflow-platform\apps\web test:smoke
```

Note: a bare `python -m pytest` timed out once, while the same explicit API test files passed quickly.
