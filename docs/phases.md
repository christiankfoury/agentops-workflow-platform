This is the scoped phase plan for AgentOps, including the completed multi-agent
application and the generic workflow platform expansion.

The goal is that each phase is small enough to implement in one focused PR, but meaningful enough that the app keeps improving after every merge.

# Project: AgentOps Workflow Platform

## Final outcome

Phases 1–65 are the completed historical implementation. Phases 66–105 form the
authorized expansion sequence in the platform section below. Current delivery,
validation and CI status are maintained in [phase progress](phase-progress.md);
these phase definitions describe scope rather than current status.
[The consolidated plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md) maps all
features from the original two lists to these phases without duplicate scope.

The following outcome describes the historical multi-agent application; the new
target also includes generic definitions, durable workers, tools, triggers,
tenant-aware permissions, a builder/debugger, benchmarks, and Kubernetes.

You will build a full-stack app where users can run business workflows through a measurable multi-agent pipeline:

```text
Input
↓
Router Agent
↓
Analyst / Specialized Agent
↓
Reviewer Agent
↓
Retry Logic
↓
Human Approval
↓
Writer Agent
↓
Final Output
↓
Evaluation + Cost + Observability Dashboard
```

The finished project should support:

```text
Sales Report -> Executive Summary
Customer Feedback -> Product Insights Report
Incident Log -> Post-Incident Report
```

And demonstrate:

```text
Single-agent baseline vs multi-agent workflow improvement
Factual accuracy improvement
Unsupported claim reduction
Cost tracking
Latency tracking
Human approval rate
Retry effectiveness
Prompt versioning
Agent state tracking
Observability
```

---

# Phase 1: Project Definition and Architecture

Define the complete product scope before writing code. Document the core workflows, agents, data flow, evaluation metrics, and dashboard requirements.

Deliverables should include a `PROJECT_SPEC.md` with the product goal, supported use cases, agent roles, success metrics, and final portfolio claims you want to prove.

---

# Phase 2: Repository Setup and Monorepo Structure

Create the initial project structure.

Recommended structure:

```text
multi-agent-workflow/
  apps/
    api/
    web/
  packages/
    shared/
  docs/
  scripts/
  docker/
```

Set up:

```text
FastAPI backend
Next.js frontend
TypeScript
Python formatting
Linting
Environment files
Basic README
```

This PR should not implement agents yet. It should only establish the foundation.

---

# Phase 3: Local Development Infrastructure

Add local infrastructure for development.

Include:

```text
Docker Compose
PostgreSQL
Backend container
Frontend container
Environment variable loading
Health checks
Basic Makefile or task scripts
```

The goal is that someone can clone the repo and run:

```bash
docker compose up
```

Then access both the API and frontend locally.

---

# Phase 4: Database Schema Foundation

Create the initial database models and migrations.

Add tables for:

```text
workflow_runs
agent_steps
uploaded_inputs
human_approvals
cost_events
prompt_versions
```

At this point, you are not building full behavior yet. You are preparing the schema that will allow agent state tracking, cost tracking, and workflow observability later.

---

# Phase 5: Backend API Foundation

Create the basic FastAPI API structure.

Add endpoints like:

```text
GET /health
GET /ready
GET /workflow-runs
GET /workflow-runs/{id}
POST /workflow-runs
```

For now, `POST /workflow-runs` can create a placeholder workflow run without executing agents.

This phase proves the backend and database are connected correctly.

---

# Phase 6: Frontend Dashboard Foundation

Create the initial Next.js dashboard.

Pages:

```text
Home
Workflow Runs
Workflow Run Detail
New Workflow
```

The frontend should fetch real data from the backend, even if the data is simple.

The goal is to have a working full-stack loop:

```text
Frontend -> API -> Database -> Frontend
```

---

# Phase 7: Workflow Run State Machine

Implement the core workflow state model.

Define statuses like:

```text
created
running
analyst_running
reviewer_running
waiting_for_human
writer_running
completed
failed
cancelled
```

Add backend logic to transition workflow runs safely from one state to another.

This is important because your project should feel like a real workflow platform, not a script that just calls an LLM.

---

# Phase 8: LLM Provider Abstraction

Add a clean abstraction around LLM calls.

Create a service that supports:

```text
chat completion
structured JSON output
model selection
token usage tracking
error handling
timeouts
retries
```

Do not deeply couple your agents to OpenAI directly. Build an interface like:

```python
LLMClient.generate_structured(...)
LLMClient.generate_text(...)
```

This makes the project easier to extend and more professional.

---

# Phase 9: Prompt Versioning Foundation

Implement prompt version storage.

Add the ability to define prompt templates for:

```text
Analyst Agent
Reviewer Agent
Writer Agent
Router Agent
Timeline Agent
Root Cause Agent
Classifier Agent
Insight Agent
```

Each prompt version should have:

```text
name
agent_type
version
template
is_active
created_at
```

Even if prompts are still seeded manually, this phase gives you a strong recruiter-facing feature: prompt versioning.

---

# Phase 10: Sales Report Input Flow

Build the first real workflow input screen.

Allow users to paste or upload a simple sales report. Store the input in the database.

The new workflow form should include:

```text
workflow type
input title
raw input text
optional notes
```

For now, only support:

```text
Sales Report -> Executive Summary
```

The goal is to prepare real user input for the first agent pipeline.

---

# Phase 11: Analyst Agent for Sales Reports

Implement the first real agent: the Sales Analyst Agent.

The agent should extract structured analysis from the sales report.

Example output:

```json
{
  "key_findings": [],
  "risks": [],
  "recommendations": [],
  "supporting_evidence": []
}
```

Store the full agent input, output, latency, model, token usage, and status in `agent_steps`.

This is the first phase where the app becomes visibly agentic.

---

# Phase 12: Agent Step Timeline UI

Update the workflow detail page to show the agent execution timeline.

Display:

```text
Step name
Status
Started time
Completed time
Latency
Model
Token usage
Cost
Output preview
```

This makes the project much more impressive because users can inspect what each agent did.

The dashboard should now show a workflow trace, not just a final answer.

---

# Phase 13: Reviewer Agent for Sales Reports

Implement the Reviewer Agent.

The Reviewer Agent should evaluate the Sales Analyst Agent output against the source input.

It should return structured output like:

```json
{
  "approved": false,
  "quality_score": 0.78,
  "issues": [
    {
      "claim": "Enterprise churn doubled",
      "problem": "Source only says churn increased",
      "severity": "high"
    }
  ],
  "retry_recommended": true
}
```

Store reviewer results in the database and display them in the workflow detail page.

---

# Phase 14: Score-Based Retry Logic

Add automatic retry logic.

Example rules:

```text
If quality_score >= 0.85:
  continue

If quality_score >= 0.70 and no high severity issues:
  require human approval

If quality_score < 0.70:
  retry Analyst Agent with reviewer feedback

If retry_count > 2:
  require human approval
```

This phase turns the project from a simple chain into a real agent workflow.

Track retry count, retry reason, and reviewer feedback used in the next analyst call.

---

# Phase 15: Human Approval Backend

Implement the backend approval system.

Add API endpoints like:

```text
GET /human-approvals
GET /human-approvals/{id}
POST /human-approvals/{id}/approve
POST /human-approvals/{id}/request-retry
POST /human-approvals/{id}/reject
POST /human-approvals/{id}/edit
```

Human approval records should store:

```text
workflow_run_id
reviewer_score
issues_json
status
human_feedback
resolved_at
```

This phase adds enterprise-grade human-in-the-loop control.

---

# Phase 16: Human Approval UI

Create the approval screen.

The user should see:

```text
Workflow type
Original input
Analyst output
Reviewer score
Reviewer issues
Recommended action
```

Actions:

```text
Approve
Request Retry
Edit Analysis
Reject Workflow
```

This is one of the most important portfolio screens. It shows that you understand real AI systems need review and control.

---

# Phase 17: Writer Agent for Executive Summaries

Implement the Writer Agent.

The Writer Agent should only run after:

```text
Reviewer approval
```

or:

```text
Human approval
```

It should turn the structured analysis into a polished executive summary.

Store the final output in the workflow run.

The workflow can now complete end-to-end:

```text
Sales Report
↓
Analyst
↓
Reviewer
↓
Retry or Human Approval
↓
Writer
↓
Final Executive Summary
```

---

# Phase 18: Final Output Page

Add a polished final output view.

Show:

```text
Final executive summary
Workflow status
Quality score
Total cost
Total latency
Number of retries
Human approval status
```

Also show a side-by-side expandable trace:

```text
Original input
Analyst output
Reviewer feedback
Human feedback
Writer output
```

This page should be clean and portfolio-ready.

---

# Phase 19: Cost Tracking

Implement detailed cost tracking.

Track:

```text
input tokens
output tokens
total tokens
estimated cost
cost per agent
cost per workflow
cost per retry
```

Add a `cost_events` table or enrich `agent_steps`.

This phase is important because cost awareness is a very enterprise-oriented feature.

---

# Phase 20: Cost Dashboard

Create a cost dashboard.

Show:

```text
Total spend
Average cost per workflow
Cost by workflow type
Cost by agent
Most expensive runs
Average retry cost
```

Useful charts:

```text
Cost over time
Cost per agent
Cost per workflow type
Tokens by agent
```

This helps prove that you are thinking beyond "it works" and into "can this run in production?"

---

# Phase 21: Observability Logs

Add structured observability logging.

Log important events:

```text
workflow_started
agent_started
agent_completed
agent_failed
reviewer_rejected_output
retry_triggered
human_approval_required
human_approved
workflow_completed
workflow_failed
```

Each event should include:

```text
workflow_run_id
agent_step_id
timestamp
event_type
metadata
```

You can store these in a table like:

```text
workflow_events
```

This gives you a real audit trail.

---

# Phase 22: Observability Timeline UI

Display workflow events visually.

On the run detail page, show a timeline like:

```text
10:01:03 - Workflow started
10:01:09 - Analyst Agent completed
10:01:16 - Reviewer found 2 issues
10:01:17 - Retry triggered
10:01:29 - Analyst Agent completed retry
10:01:35 - Human approval required
10:02:10 - Human approved
10:02:22 - Writer Agent completed
```

This makes the system feel mature and debuggable.

---

# Phase 23: Baseline Single-Agent Workflow

Implement the baseline workflow.

The baseline should do this:

```text
Sales Report
↓
Single LLM prompt
↓
Final executive summary
```

No reviewer. No retry. No human approval.

Store baseline runs separately or mark them with:

```text
run_mode = baseline
```

This is essential because you need something to compare your multi-agent workflow against.

---

# Phase 24: Evaluation Dataset Foundation

Create the evaluation dataset structure.

Add tables for:

```text
evaluation_cases
evaluation_expected_facts
evaluation_results
```

Each evaluation case should include:

```text
workflow_type
input_text
expected_facts
expected_risks
expected_recommendations
expected_output_notes
```

Seed the database with the first 5-10 sales report evaluation cases.

This gives you a repeatable test set.

---

# Phase 25: Evaluation Runner for Sales Reports

Build a script or backend endpoint that runs evaluation cases.

It should be able to run:

```text
baseline mode
multi-agent mode
```

Against the same test cases.

Store results in `evaluation_results`.

At first, evaluation can be semi-automated using an evaluator LLM.

Later, you can add more deterministic checks.

---

# Phase 26: Evaluation Metrics

Implement the first evaluation metrics.

Track:

```text
factual accuracy
unsupported claim rate
completeness
human approval rate
average cost
average latency
average retries
```

Example result:

```json
{
  "mode": "multi_agent",
  "factual_accuracy": 0.89,
  "unsupported_claim_rate": 0.07,
  "completeness": 0.84,
  "avg_cost": 0.12,
  "avg_latency_ms": 41000
}
```

This is where the project starts producing recruiter-friendly numbers.

---

# Phase 27: Evaluation Dashboard

Create the evaluation dashboard.

Show a comparison table:

| Metric             | Baseline | Multi-Agent |
| ------------------ | -------: | ----------: |
| Factual Accuracy   |      74% |         90% |
| Unsupported Claims |      21% |          6% |
| Completeness       |      68% |         84% |
| Avg Cost           |    $0.04 |       $0.12 |
| Avg Latency        |      13s |         41s |

This is arguably the most important page in the entire app.

This is what lets you say:

> "My multi-agent workflow improved factual accuracy and reduced hallucinations compared to a single-agent baseline."

---

# Phase 28: Prompt Version Comparison

Extend evaluation results to include prompt versions.

You should be able to compare:

```text
Reviewer prompt v1
Reviewer prompt v2
Analyst prompt v1
Analyst prompt v2
```

Track whether prompt changes improved or worsened results.

This turns prompt engineering into measurable engineering.

---

# Phase 29: Prompt Management UI

Create a UI for prompt versions.

Pages:

```text
Prompt Versions
Prompt Detail
Create Prompt Version
Activate Prompt Version
```

Each prompt should show:

```text
agent type
version
active status
template
created date
evaluation performance
```

This is optional in many projects, but you said you want all optional features, so include it.

---

# Phase 30: Customer Feedback Workflow Schema

Add support for the second workflow type:

```text
Customer Feedback -> Product Insights Report
```

Update the system to support multiple workflow types.

Add the necessary schemas for:

```text
feedback themes
sentiment patterns
feature requests
bug reports
recommendations
supporting examples
```

This phase prepares the project for the second real workflow without building all agents yet.

---

# Phase 31: Customer Feedback Classifier Agent

Implement the Classifier Agent.

It should categorize feedback into groups like:

```text
pricing
bugs
feature requests
performance
support experience
usability
```

Output should be structured JSON.

Example:

```json
{
  "themes": [
    {
      "name": "performance",
      "count": 14,
      "examples": []
    }
  ]
}
```

Store all outputs as `agent_steps`.

---

# Phase 32: Customer Feedback Insight Agent

Implement the Insight Agent.

It should turn categorized feedback into product insights:

```text
top customer pain points
recurring feature requests
risk areas
recommended product actions
```

This creates the equivalent of the Analyst Agent for customer feedback.

---

# Phase 33: Reviewer and Writer for Customer Feedback

Extend the Reviewer Agent and Writer Agent to support customer feedback workflows.

The Reviewer should check whether insights are supported by actual feedback examples.

The Writer should generate a polished product insights report.

By the end of this phase, the second workflow should run end-to-end.

---

# Phase 34: Customer Feedback Evaluation Cases

Add evaluation cases for customer feedback.

Seed 10 cases with:

```text
input feedback
expected themes
expected insights
expected recommendations
```

Then update the evaluation runner to support this workflow type.

Now your evaluation dashboard should show metrics by workflow type.

---

# Phase 35: Incident Report Workflow Schema

Add support for the third workflow type:

```text
Incident Log -> Post-Incident Report
```

Define structured outputs for:

```text
timeline events
impact
suspected root cause
confirmed facts
inferred claims
follow-up actions
```

This phase prepares the app for incident-report-specific agents.

---

# Phase 36: Timeline Agent

Implement the Timeline Agent.

It should extract a chronological sequence from raw incident logs.

Example output:

```json
{
  "timeline": [
    {
      "time": "10:02",
      "event": "API latency increased",
      "source_evidence": "10:02 AM - API latency increased"
    }
  ]
}
```

This agent should be precise because timeline accuracy is one of the key evaluation metrics.

---

# Phase 37: Root Cause Agent

Implement the Root Cause Agent.

It should identify:

```text
confirmed causes
likely causes
unknowns
impact
follow-up actions
```

Important: it should separate confirmed facts from inferred conclusions.

That distinction is very recruiter-impressive because it shows you care about hallucination control.

---

# Phase 38: Reviewer and Writer for Incident Reports

Extend the Reviewer and Writer Agent to support incident workflows.

The Reviewer should check:

```text
Is the timeline accurate?
Are root-cause claims supported?
Are inferred claims clearly labeled?
Are follow-up actions reasonable?
```

The Writer should generate a final post-incident report.

By the end of this phase, all three main workflows run end-to-end.

---

# Phase 39: Incident Evaluation Cases

Add 10 incident report evaluation cases.

Expected outputs should include:

```text
expected timeline events
expected impact
expected root cause
unsupported claim checks
expected follow-up actions
```

Update the evaluation dashboard to include incident-specific metrics.

---

# Phase 40: Router Agent

Add the optional Router Agent.

The Router Agent should inspect input and decide the workflow type:

```json
{
  "workflow_type": "incident_report",
  "confidence": 0.91,
  "reasoning_summary": "Input contains timestamped operational events and recovery notes."
}
```

The user can still manually choose a workflow type, but now you can offer:

```text
Auto-detect workflow type
```

This makes the platform feel more intelligent.

---

# Phase 41: Router Confidence and Fallback Logic

Add fallback logic for low-confidence routing.

Example:

```text
If router confidence >= 0.85:
  auto-select workflow

If router confidence between 0.60 and 0.85:
  suggest workflow and ask user to confirm

If router confidence < 0.60:
  require manual selection
```

Track router accuracy in evaluations.

This phase makes the optional Router Agent production-like instead of gimmicky.

---

# Phase 42: Error Handling and Failure Recovery

Improve system reliability.

Handle:

```text
LLM timeout
invalid JSON
schema validation failure
database error
agent failure
reviewer failure
writer failure
workflow cancellation
```

Add graceful failure states and useful error messages in the UI.

This is a very important engineering phase.

---

# Phase 43: Schema Validation and Guardrails

Add strict validation for all agent outputs.

Use Pydantic models for:

```text
SalesAnalysisOutput
ReviewerOutput
WriterInput
CustomerFeedbackOutput
IncidentTimelineOutput
RouterOutput
```

If an agent returns invalid JSON, retry with a repair prompt or fail safely.

This phase shows strong backend engineering.

---

# Phase 44: Model Configuration and Agent Settings

Add configurable model settings.

Allow each agent to have:

```text
model
temperature
max tokens
timeout
max retries
active prompt version
```

You can expose this in an admin/settings page later.

For now, store settings in code or database.

---

# Phase 45: Admin Settings UI

Create a settings page for agent configuration.

Allow users to configure:

```text
model per agent
temperature
retry limit
reviewer approval threshold
human approval threshold
active prompt version
```

This makes the app feel more like a real platform.

---

# Phase 46: Advanced Human Review Editing

Improve human approval.

Instead of only approving or rejecting, allow the user to edit structured analysis before the Writer Agent runs.

For example, the user can edit:

```text
key findings
risks
recommendations
reviewer notes
```

Then the Writer Agent uses the human-edited version.

This is a strong enterprise feature.

---

# Phase 47: Human Feedback Loop

Store human feedback and use it for future analysis.

Track:

```text
what the reviewer flagged
what the human changed
whether the human approved
which claims were edited
```

Add a dashboard section showing:

```text
most common reviewer issues
most common human edits
approval rate over time
```

This gives you the basis for an improvement story.

---

# Phase 48: Agent Performance Dashboard

Create a dedicated agent performance page.

Show metrics by agent:

```text
average latency
average cost
failure rate
retry rate
average reviewer score
schema validation failure rate
```

Example table:

| Agent         | Avg Score | Avg Cost | Avg Latency | Failure Rate |
| ------------- | --------: | -------: | ----------: | -----------: |
| Sales Analyst |       86% |    $0.04 |         14s |           2% |
| Reviewer      |       91% |    $0.03 |          9s |           1% |
| Writer        |       88% |    $0.04 |         12s |           1% |

This is a very good portfolio screen.

---

# Phase 49: Workflow Comparison View

Create a side-by-side comparison page for baseline vs multi-agent outputs.

For the same input, show:

```text
Baseline output
Multi-agent output
Reviewer issues
Evaluation scores
Cost difference
Latency difference
```

This makes the improvement obvious to recruiters.

The user should be able to see not only numbers, but actual output quality differences.

---

# Phase 50: Evaluation Report Export

Add the ability to export evaluation results.

Support:

```text
CSV export
JSON export
Markdown report export
```

The Markdown report should include:

```text
evaluation date
number of cases
baseline metrics
multi-agent metrics
improvement percentages
cost tradeoff
notable failure cases
```

This gives you material for your README and portfolio case study.

---

# Phase 51: File Upload Support

Add real file upload support.

Support:

```text
.txt
.md
.csv
.pdf optional
```

Start with text and CSV. PDF can be added if you want, but for this project it is less important than workflow quality.

Store uploaded files and extracted text in the database.

---

# Phase 52: CSV Parsing for Customer Feedback

Improve customer feedback input handling.

Allow the user to upload a CSV with columns like:

```text
customer_id
date
rating
feedback
source
```

Parse the CSV and show a preview before running the workflow.

This makes the customer feedback workflow much more realistic.

---

# Phase 53: Incident Log Parser

Improve incident log input handling.

Support timestamped logs and normalize them into structured events.

Example input:

```text
10:02 AM - API latency increased
10:08 AM - Error rate exceeded threshold
```

The parser should extract:

```text
timestamp
event text
raw line
```

Then the Timeline Agent can work with cleaner input.

---

# Phase 54: Advanced Evaluation: Deterministic Checks

Add non-LLM evaluation checks where possible.

Examples:

```text
Did the output include expected numeric facts?
Did the incident timeline include all required timestamps?
Did the feedback report mention the top expected themes?
Did the writer include unsupported numbers?
```

This makes your evaluation system more credible than using only an LLM judge.

---

# Phase 55: Failure Case Explorer

Create a dashboard for failed or low-quality runs.

Show:

```text
lowest scoring workflows
most common failure types
agent outputs with schema failures
reviewer false positives
human rejected workflows
```

This is a great feature because it shows you analyze system weaknesses, not just successes.

---

# Phase 56: Improvement Tracking Over Time

Track whether the system improves across prompt versions and agent settings.

Show charts like:

```text
Factual accuracy over time
Unsupported claim rate over time
Cost over time
Latency over time
Human approval rate over time
```

This directly supports your recruiter story:

> "I improved the workflow through measured iterations."

---

# Phase 57: Seed Demo Dataset

Create a polished demo dataset.

Include:

```text
10 sales reports
10 customer feedback datasets
10 incident logs
gold-standard expected outputs
baseline outputs
multi-agent outputs
evaluation results
```

This is important because recruiters should be able to run the app and immediately see impressive data.

---

# Phase 58: Demo Mode

Add a demo mode.

The user can click:

```text
Run Demo Sales Workflow
Run Demo Feedback Workflow
Run Demo Incident Workflow
Run Full Evaluation
```

This makes the app easy to show in interviews and portfolio videos.

---

# Phase 59: README Case Study

Write a serious README.

Include:

```text
project overview
architecture diagram
workflow diagram
screenshots
features
tech stack
evaluation methodology
baseline vs multi-agent results
cost tradeoff
lessons learned
setup instructions
```

This phase is not optional. The README is how recruiters understand the value quickly.

---

# Phase 60: Architecture Documentation

Add technical docs.

Create:

```text
docs/ARCHITECTURE.md
docs/AGENTS.md
docs/EVALUATION.md
docs/PROMPTS.md
docs/OBSERVABILITY.md
docs/DEPLOYMENT.md
```

This turns the project into a professional portfolio artifact.

---

# Phase 61: Testing Foundation

Add automated tests.

Start with:

```text
backend unit tests
schema validation tests
agent output parsing tests
API endpoint tests
frontend smoke tests
```

Do not try to test everything at once. Focus on the workflow-critical parts first.

---

# Phase 62: Workflow Integration Tests

Add integration tests for workflow execution.

Test:

```text
sales workflow success path
reviewer rejects low-quality analysis
retry is triggered
human approval pauses workflow
writer only runs after approval
workflow completes after approval
```

These tests show strong engineering discipline.

---

# Phase 63: Evaluation Tests

Add tests for evaluation logic.

Test:

```text
accuracy calculation
unsupported claim rate calculation
completeness calculation
baseline vs multi-agent comparison
evaluation result storage
```

This protects the most important part of the project: the improvement metrics.

---

# Phase 64: Security and Input Safety

Add basic safety and security controls.

Include:

```text
file size limits
input length limits
allowed file types
rate limiting
auth checks
role checks
safe error messages
environment secret handling
```

This makes the app feel closer to production.

---

# Phase 65: Portfolio Polish

Polish the UI and user experience.

Focus on the pages recruiters will see:

```text
landing page
workflow run detail
evaluation dashboard
baseline comparison
agent trace
cost dashboard
human approval page
```

Add empty states, loading states, error states, and better visual hierarchy.

---

# Platform Expansion: Planned Phases 66–105

These phases consolidate both source lists in
[the implementation plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md). They are
the authorized 66–105 implementation sequence as of 2026-09-15; consult
`phase-progress.md` for each phase's status. Phases 1–65 remain complete, while the
former demo-script/case-study Phases 66–67 move to 104–105. Their original scope is
preserved in those entries. The old references to undefined Phases 68–80 are
replaced by the concrete sequence below.

## Shared phase delivery gate

Apply this gate to **every Phase 66–105**, including documentation phases:

1. **Plan:** Read the context docs and phase dependencies, inspect current code,
   identify existing behavior to preserve, and record a short implementation plan
   with acceptance cases and migration/rollout implications in phase progress.
2. **Implement:** Deliver only this phase. Prefer existing patterns and roughly
   300–700 changed lines where practical. If the phase requires more, document
   the scoped reason; split the plan before implementation if needed.
3. **Validate:** Run focused meaningful checks and review the local diff for
   obvious errors before committing. Broaden checks when shared code changes.
4. **Record and commit:** Update phase progress with changes and validation,
   then commit the implementation on `main` with a clear subject and body.
   During an explicitly authorized implementation run, push that commit to `main`.
5. **Review after push:** Review the pushed implementation against acceptance,
   correctness, state transitions, persistence, permissions, retries/idempotency,
   concurrency, failure handling, and compatibility. Check relevant CI status.
6. **Fix findings:** Make actionable fixes in a separate fix commit, rerun affected
   checks, push, and review the fix. Repeat until no blocking findings remain.
7. **Close the phase:** Record implementation/fix commit IDs, push/CI status,
   validation evidence, review outcome, and limitations in phase progress.
   If the final record needs a documentation commit, push that too. Mark complete
   and advance only after implementation, validation, push, and review are complete.

Preserve unrelated working-tree changes and stage only phase-owned files. A failed
push/CI check or unresolved blocking review finding prevents advancement. Missing
credentials or a required product decision follows `AGENTS.md` stop conditions;
unperformed live checks must be labeled rather than reported as passing.

### Validation by change type

- Backend: focused `uv run --directory apps/api pytest <test files>`, then
  `uv run --directory apps/api ruff check src tests`.
- Shared backend/lifecycle/security changes: broaden affected workflow regression
  tests. If the bare full API command hangs, run explicit files and report it.
- Database/concurrency/worker changes: use real disposable PostgreSQL, independent
  sessions, and worker processes where needed; in-memory substitutes do not prove
  locking, uniqueness, restart, or lease behavior.
- Frontend: `pnpm --dir apps/web typecheck`,
  `pnpm --dir apps/web test:smoke`, and relevant interaction checks.
- Containers/Kubernetes: configuration validation plus actual disposable runtime
  deployment and recovery checks specified by the phase.
- Documentation only: inspect diff, links/anchors, numbering, source coverage,
  and factual consistency. Do not run unrelated app suites just for prose.
- Keep automatic tests deterministic and credential-free. Real provider, paid
  traffic, or hosted-cluster checks require available authorized access and have
  separate recorded evidence.

The exact test filenames and infrastructure commands are established as their
implementation phases add the harnesses; do not claim future commands already exist.

---

# Phase 66: State Transition Invariants

**Dependencies:** Completed Phases 1–65. **Requirements:** R03.

**Implementation scope**

- Audit every runtime status assignment, including agent services, approvals, recovery, status PATCH, and evaluation paths.
- Route live changes through one transition authority with transaction ownership, consistent events/timestamps, and stale-write protection. Keep existing business states during this repair.
- Treat demo/import fixture construction explicitly; do not force fake historical transitions into seeded data.
- Document existing versus enforced invariants in architecture docs.

**Acceptance and validation**

- Existing success, quality-retry, approval, rejection, failure, and cancellation paths still work for all three workflows and baselines.
- Illegal terminal transitions and cancellation-versus-completion races cannot overwrite a committed terminal result.
- Focused state/agent/approval/recovery tests pass; review direct-write search results and justify fixture-only exceptions.

---

# Phase 67: User Identity and Organization Membership

**Dependencies:** Phase 66. **Requirements:** R09.

**Implementation scope**

- Add users, organizations, memberships, and scoped service-principal records with migrations.
- Introduce verified OIDC-compatible token/session validation (issuer, audience, expiry, signature) and server-derived identity; use local identity fixtures for tests.
- Resolve organization membership from authenticated identity; caller-selected role/actor values grant no authority.
- Add sign-in/session and organization-selection UI; keep incomplete identity rollout disabled for public deployment until Phases 68–69.

**Acceptance and validation**

- Valid users and service principals resolve correctly; forged/expired tokens, untrusted role headers, disabled memberships, and unauthenticated requests fail.
- Migration upgrade and fresh database initialization work; secrets/tokens do not appear in logs.
- Backend auth tests and frontend session/organization smoke checks pass; document required live provider configuration without claiming fixture tests prove it.

---

# Phase 68: Tenant Ownership and Isolation

**Dependencies:** Phase 67. **Requirements:** R09.

**Implementation scope**

- Backfill existing data into an explicit default organization, verify counts, and enforce ownership constraints with a reversible migration plan.
- Scope runs, inputs, agent steps, events, approvals, prompts/settings, evaluation cases/results, costs, exports, and aggregates through shared tenant-aware access patterns.
- Classify demo fixtures as scoped copies or explicitly read-only shared templates; keep private data out of shared seeds.
- Apply scope to nested lookups and mutation paths as well as list endpoints; every later resource must adopt this contract.

**Acceptance and validation**

- Two-organization tests attempt cross-tenant list/detail/nested reads, exports, aggregates, updates, and foreign-key references.
- Caller-provided IDs cannot attach another organization's input/prompt/evaluation to a run.
- Legacy data survives migration and remains visible only to the assigned organization; broaden API validation because access patterns change globally.

---

# Phase 69: Role Permissions and Approval Audit

**Dependencies:** Phase 68. **Requirements:** R09.

**Implementation scope**

- Enforce viewer/operator/reviewer/admin permissions from membership in API dependencies and services.
- Permit reviewer/admin approval decisions; require admin for production publication/configuration, membership, credentials, and high-severity overrides.
- Derive approval actors from identity, recheck membership at decision time, and persist audit records for starts, decisions/edits, settings/prompts, exports, and membership changes.
- Reflect permitted actions in UI while retaining server enforcement; replace prototype role behavior in protected operation.

**Acceptance and validation**

- Exercise the role matrix, forged actor IDs, revoked membership, unauthorized edits/retries/rejections, and cross-tenant approvals.
- Every accepted sensitive action has one correct actor/organization audit record; failed transactions do not leave misleading success records.
- Approval and security API tests plus permission-aware UI checks pass; document the public-deployment security gate.

---

# Phase 70: Typed Workflow Graph Schema

**Dependencies:** Phase 69. **Requirements:** R01, R02.

**Implementation scope**

- Define a versioned graph schema with stable node IDs, edges, entry/output bindings, input/output schemas, and all eight canonical step types.
- Define constrained condition/transform expressions, branch defaults, parallel regions/joins, delay/approval configuration, and retry/timeout policy shapes.
- Validate uniqueness, dangling references, reachability, type compatibility, unsupported expressions, join ambiguity, size limits, and cycles.
- Reserve explicit bounded quality-revision policy metadata; arbitrary graph cycles remain rejected. Runtime support is advertised separately from schema recognition.

**Acceptance and validation**

- Round-trip valid fixtures covering all primitives; reject malformed graphs with node/field-specific errors.
- Both branches and missing/null input behavior have explicit validation expectations.
- Published execution will reject primitives whose executors are not yet available; schema acceptance must not imply runnable support.

---

# Phase 71: Workflow Definitions and Immutable Versions

**Dependencies:** Phase 70. **Requirements:** R01.

**Implementation scope**

- Persist tenant-owned definitions, editable drafts, immutable versions, node/edge snapshots, and a published-version pointer.
- Add create/read/update-draft/validate/publish/archive APIs with optimistic draft revisions and admin-only publication.
- Pin prompt/configuration references where known; retain immutable referenced versions used by runs. Defer runtime resolution rules to Phase 82.
- Prevent deletion or in-place edits of published content needed by history; expose version diffs/metadata for later UI.

**Acceptance and validation**

- Concurrent draft edits conflict safely; competing publishes cannot produce duplicate version numbers.
- Publication creates an immutable snapshot, archival preserves referenced history, and cross-tenant access fails.
- Schema migrations and API authorization tests pass; verify published versions with unsupported runtime primitives cannot be started yet.

---

# Phase 72: Generic Step Runs and Attempts

**Dependencies:** Phase 71. **Requirements:** R02, R03.

**Implementation scope**

- Add version-bound generic runs plus StepRun and StepAttempt records with node, branch/iteration identity, I/O, timestamps, status, errors, and idempotency fields.
- Define generic run/step/attempt lifecycle transitions using Phase 66's authority; AI metadata is optional.
- Add read schemas and compatibility access for historical AgentStep records; preserve legacy business/run-mode labels for existing reports.
- Enforce unique logical node execution and attempt numbering; distinguish a logical step from a retried attempt.

**Acceptance and validation**

- Non-LLM steps persist without model/agent fields; distinct branch/iteration invocations do not collide.
- Illegal/stale transitions and duplicate attempts fail safely; migration preserves old traces, costs, and evaluation links.
- Focused persistence/lifecycle/API tests cover both generic and historical reads.

---

# Phase 73: Idempotent Generic Run Starts

**Dependencies:** Phase 72. **Requirements:** R07, R10.

**Implementation scope**

- Add manual/API starts referencing a published version and validated input, storing tenant, actor, resolved version, start key, and canonical request fingerprint atomically.
- Use database uniqueness to return the same run for identical retries and a conflict for changed input under the same scoped key.
- Define key scope/retention and archive behavior; resolve the current published version once for the first accepted start.
- Initially create persisted pending runs behind the runtime rollout gate; Phase 75 adds atomic enqueue and asynchronous acceptance.

**Acceptance and validation**

- Concurrent identical starts yield one run; different organizations can use the same key without collision.
- Changed payload/version under a reused key conflicts; retry after publication changes still returns the original accepted run.
- Invalid input, unexecutable versions, unauthorized starts, and rollback leave no partial run or key reservation.

---

# Phase 74: Deterministic Graph Interpreter

**Dependencies:** Phase 73. **Requirements:** R01, R02.

**Implementation scope**

- Dispatch through a step-executor registry and compute ready nodes from persisted graph/state, without business-type branches.
- Implement sequential code, transform, and condition steps using registered versioned handlers and constrained expressions.
- Persist inputs/outputs and selected/skipped edges; resolve run outputs deterministically and handle missing data explicitly.
- Define the checkpoint/continuation interface for workers and the bounded revision-policy hook; do not execute unsupported wait/parallel/LLM/tool primitives yet.

**Acceptance and validation**

- A new deterministic graph runs by data configuration alone; both condition routes and final-output bindings work.
- Restarting from a checkpoint does not rerun a completed logical step; malformed bindings and handler failures produce typed errors.
- Tests reject arbitrary code/eval, dependency cycles, unsupported executors, and ambiguous completion.

---

# Phase 75: Transactional Durable Job Queue

**Dependencies:** Phase 74. **Requirements:** R04.

**Implementation scope**

- Add PostgreSQL-backed durable jobs and a worker entry point; create a run and its initial job in one transaction.
- Return accepted run ID/status promptly from generic start APIs; persist jobs for next-ready nodes rather than executing in request handlers.
- Claim due jobs with database concurrency control and bounded worker capacity; persist completion plus downstream jobs atomically.
- Add a local worker service/configuration and graceful stop behavior; expose basic queued/running/failed job state.

**Acceptance and validation**

- API acceptance does not wait for executor work; rollback cannot leave a run without its initial job or a job without its run.
- Multiple workers and duplicate deliveries cannot claim/complete the same logical work twice.
- Real-PostgreSQL integration tests cover concurrent claims, transaction failure, and worker process restart with queued work.

---

# Phase 76: Leases Heartbeats and Crash Recovery

**Dependencies:** Phase 75. **Requirements:** R03, R04.

**Implementation scope**

- Persist worker identity, lease expiry, fencing token, heartbeat time, and checkpoint ownership.
- Renew active leases and reclaim expired jobs; stale workers cannot commit results, events, totals, or downstream jobs after reassignment.
- Recover crashes between claim, execution, and completion; bound recovery and record abandoned attempts.
- Apply the transition/transaction authority to job ownership and worker completion paths.

**Acceptance and validation**

- Kill a worker before execution and after a checkpoint, then verify another worker resumes the work.
- Competing reclaimers yield one owner; a delayed old worker's result is rejected.
- Real-database/process tests show completed nodes and downstream jobs remain unique; document at-least-once handler invocation.

---

# Phase 77: Durable Retries Backoff and Deadlines

**Dependencies:** Phase 76. **Requirements:** R06.

**Implementation scope**

- Persist retry policy, attempt count, retryable/permanent error classification, next_attempt_at, per-attempt timeout, and run deadline.
- Implement bounded exponential backoff/jitter and due-job requeue without sleeping workers.
- End exhausted work in explicit failed/dead-letter state; preserve every attempt and reason.
- Define provider-versus-engine retry ownership and separate quality revision counters; recovery retry policy cannot silently erase prior attempts.

**Acceptance and validation**

- Fake-clock tests check delay bounds, maximum attempts, deadlines, and permanent failures without busy waiting.
- Worker restarts preserve due times/counts; duplicate failure delivery creates one retry job.
- Timeout/exhaustion/cancellation races cannot create runnable jobs for terminal runs; test against real PostgreSQL for uniqueness.

---

# Phase 78: Durable Cancellation

**Dependencies:** Phase 77. **Requirements:** R05.

**Implementation scope**

- Persist cancel_requested intent and expose an idempotent authorized cancel operation.
- Stop claims and downstream scheduling, attempt supported I/O cancellation, and fence late worker results.
- Cancel queued/retry/wait work consistently; retain completed outputs and partial attempt history with clear terminal status.
- Define cancellation-versus-success ordering and uncertain external-effect status for later tool adapters.

**Acceptance and validation**

- Test cancellation while queued, running, backing off, and racing completion/recovery.
- Repeated cancellation is safe; late results cannot overwrite cancellation or enqueue children.
- Controllable I/O tests verify abort where supported; document that accepted remote effects cannot be undone.

---

# Phase 79: Durable Delay Steps

**Dependencies:** Phase 78. **Requirements:** R02.

**Implementation scope**

- Implement delay durations or explicit wake times with persisted UTC due times and validation limits.
- Release workers while waiting and enqueue one continuation when due.
- Integrate cancellation, run deadlines, expired leases, and duplicate wake events.
- Expose waiting reason/wake time in generic read APIs.

**Acceptance and validation**

- Fake-clock and restart tests show no early continuation or worker sleeping for the delay duration.
- Multiple wake processors produce one continuation; cancellation/deadline expiration suppresses wakeup.
- Negative/invalid/excessive delay input fails with a clear validation error.

---

# Phase 80: Durable Approval Steps and Resume

**Dependencies:** Phase 79. **Requirements:** R02, R09.

**Implementation scope**

- Link approvals to exact version/node/iteration and reviewed payload hash; persist a wait that releases the worker.
- Support approve, edit, reject, and bounded request-retry using existing structured review contracts and authenticated actors.
- Commit a decision and its resume job atomically; make repeated identical decisions idempotent and conflicting decisions explicit.
- Bind approval to the action/input it authorizes, invalidate it when governed input changes, and enforce expiry/high-severity policy.

**Acceptance and validation**

- Concurrent approve/reject/edit/cancel attempts yield one valid decision and at most one resume.
- Worker/API restart while awaiting approval preserves the wait; a stale approval cannot authorize changed inputs.
- Role, membership revocation, tenant isolation, rejection, edited output, and quality retry exhaustion tests pass.

---

# Phase 81: Parallel Branches and Joins

**Dependencies:** Phase 80. **Requirements:** R02.

**Implementation scope**

- Implement persisted fork/join state with branch identities, bounded fan-out, and worker concurrency limits.
- Join all selected branches after success with deterministic output ordering; unselected conditional branches count as skipped.
- Specify failure propagation, branch cancellation, and run-deadline behavior; retain branch traces.
- Claim the join transition atomically so duplicate branch completion cannot enqueue it twice.

**Acceptance and validation**

- Test out-of-order completion, conditional skips, one failed branch, nested supported regions, waits inside branches, and cancellation.
- Crash/replay of a branch does not duplicate the join or overwrite sibling output.
- Reject malformed cross-branch bindings/joins and enforce configured fan-out limits.

---

# Phase 82: LLM Executor and Bounded Quality Revisions

**Dependencies:** Phase 81. **Requirements:** R01, R02, R06.

**Implementation scope**

- Add an LLM executor reusing structured output validation, prompt/settings resolution, provider abstraction, and cost/event tracking.
- Pin prompt version, model/settings, schemas, and handler versions at run start so queued/retried work cannot pick up later edits.
- Model reviewer-directed revisions as an explicit bounded policy over declared nodes, with distinct quality iteration and infrastructure attempt counters.
- Preserve reviewer feedback, schema repair accounting, approved/human-edited writer input, and human escalation after quality exhaustion.

**Acceptance and validation**

- Provider fixtures verify schema failures/repair, SDK retry coordination, timeout/cancellation, usage accounting, and immutable configuration.
- Quality retries revisit only the declared subgraph with bounded iterations and re-review; stale approvals cannot carry over.
- New prompt/settings publication during a paused run affects only later runs; no paid LLM calls are required for automated tests.

---

# Phase 83: Sales Workflow Template Migration

**Dependencies:** Phase 82. **Requirements:** R01.

**Implementation scope**

- Represent sales analysis, review, bounded revision, approval, and writing as a published template plus a one-step sales baseline.
- Reuse existing agent transformations/prompts inside executors while moving control flow to graph data.
- Route new sales starts through the worker engine; legacy execution endpoints adapt or reject duplicate control for migrated runs.
- Keep historical sales runs and baseline comparisons readable; document rollout/backout behavior.

**Acceptance and validation**

- Fixture-based parity tests cover approval, edit, rejection, retry exhaustion, baseline, final output, costs, and evaluation links.
- Sales-specific branching is absent from the generic interpreter.
- Existing sales pages and comparison/evaluation checks pass; rollout cannot execute both old and new paths for one run.

---

# Phase 84: Customer Feedback Template Migration

**Dependencies:** Phase 83. **Requirements:** R01.

**Implementation scope**

- Publish classifier → insight → reviewer → approval/revision → writer and feedback baseline templates.
- Preserve CSV normalization, supporting examples, retry context, and human-edited insight selection.
- Switch new feedback starts to generic execution and adapt existing UI/evaluation reads.
- Apply the same legacy compatibility and duplicate-control prevention rules as sales.

**Acceptance and validation**

- Compare old/new outputs and decisions under identical fixtures for success, rejection, quality retry, edit, and baseline.
- Classifier/insight dependencies survive restart and do not reuse stale prior-iteration output.
- Feedback parser, agent, approval, comparison, and evaluation regression checks pass.

---

# Phase 85: Incident Template and Evaluation Compatibility

**Dependencies:** Phase 84. **Requirements:** R01.

**Implementation scope**

- Publish timeline → root cause → reviewer → approval/revision → writer and incident baseline templates.
- Preserve timestamp normalization, confirmed versus inferred facts, human edits, and bounded revision behavior.
- Complete generic-run integration for all evaluation runners, demo seeding, comparison, cost, and trace readers; avoid double counting legacy adapters.
- Document legacy endpoint deprecation and keep historical runs accessible without fabricated workflow versions.

**Acceptance and validation**

- Incident parity covers success, missing/ambiguous timestamps, review, edits, rejection, retries, cancellation, and baseline.
- All three workflows retain same-input baseline comparisons and deterministic scoring under provider fixtures.
- Broaden backend and frontend regression validation after shared readers/runners change; verify historical and new datasets together.

---

# Phase 86: Tool Contracts Credentials and Effect Ledger

**Dependencies:** Phase 85. **Requirements:** R07, R08.

**Implementation scope**

- Persist tenant-owned versioned ToolDefinition and ToolExecution contracts, schema validation, timeout/retry policy, side_effecting flag, and credential references.
- Resolve credentials only within authorized workers; redact arguments/results/errors and audit use without storing secrets in graphs or traces.
- Add stable logical effect keys, request fingerprints, and a ledger with pending/succeeded/failed/unknown/reconciled outcomes.
- Define adapter contracts for provider idempotency or reconciliation; ambiguous effects without safe reconciliation require operator resolution rather than blind replay.

**Acceptance and validation**

- Duplicate attempts share an effect key/result; changed action input conflicts; independent iterations receive distinct intended action identities.
- Crash windows before/after provider acceptance produce recoverable or explicitly unknown outcomes.
- Contract tests cover malformed schemas, revoked/cross-tenant credentials, redaction, and concurrent claims against real PostgreSQL.

---

# Phase 87: HTTP REST Tool

**Dependencies:** Phase 86. **Requirements:** R08.

**Implementation scope**

- Implement schema-bound HTTP requests with method/host policy, bounded body/response size, timeout, redirects, and structured result/error mapping.
- Block unauthorized internal/metadata destinations, including redirect and DNS-resolution bypasses; allow only explicit configured destinations.
- Apply credential injection/redaction and effect-ledger/provider-idempotency policy for writes.
- Integrate governed-action approval and engine cancellation/deadlines without inventing successful effects after uncertain timeouts.

**Acceptance and validation**

- Local HTTP fixtures cover reads, writes, transient/permanent errors, rate limits, oversized payloads, timeout, redirects, and cancellation.
- Security tests exercise disallowed destinations, leaked headers, malformed responses, and cross-tenant credential use.
- Duplicate/recovered writes to an idempotent fixture yield one effect; non-idempotent ambiguity stays blocked for reconciliation.

---

# Phase 88: PostgreSQL Query Tool

**Dependencies:** Phase 87. **Requirements:** R08.

**Implementation scope**

- Implement a separate tenant-scoped data connection using restricted read-only credentials and registered/parameterized queries.
- Bound rows, statement time, result size, and connection use; validate output schemas and cancellation.
- Keep application/control-database credentials inaccessible to workflow authors and LLM tool input.
- Persist redacted execution metadata and map database failures into the shared retry taxonomy.

**Acceptance and validation**

- A disposable fixture database proves allowed reads work and writes/DDL/unsafe multi-statements are denied.
- Tests cover parameter injection, statement timeout, row limits, schema mismatch, revoked credentials, and tenant separation.
- Retries cannot mutate data; connection cleanup and cancellation are verified.

---

# Phase 89: GitHub SaaS Tool

**Dependencies:** Phase 88. **Requirements:** R08.

**Implementation scope**

- Implement a configured-repository adapter for reading issues and creating an issue using scoped credential references.
- Validate organization/repository/operation allowlists, inputs, pagination, provider errors, and rate-limit backoff.
- Gate issue creation through permissions/approval and persist a stable correlation marker for reconciliation.
- On an ambiguous create, reconcile or require operator resolution; never assume the remote API enforces the local idempotency key.

**Acceptance and validation**

- Provider contract fixtures cover read, approved create, denied action, rate limit, expired credentials, and redaction.
- Simulate create accepted then response lost; recovery must not blindly create another issue.
- Document an optional live sandbox-repository check and its credential prerequisite; fixture success is not recorded as live integration evidence.

---

# Phase 90: Governed LLM Tool Calling

**Dependencies:** Phase 89. **Requirements:** R08.

**Implementation scope**

- Let LLM steps request only tools declared in the pinned workflow version and allowed to the current principal.
- Validate requested arguments, route through ToolExecution, persist call IDs/results/continuation state, and resume model reasoning after results.
- Enforce maximum calls, cost/time budgets, cancellation, and approvals bound to exact side-effecting arguments.
- Treat tool results as untrusted data; no returned text can expand the tool list, credential scope, or permissions.

**Acceptance and validation**

- Provider fixtures exercise multi-call reasoning, invalid/unknown tools, duplicate call IDs, budget exhaustion, and restart mid-conversation.
- Side effects wait for valid approval and preserve ledger keys across retries; rejection/cancellation prevents execution.
- Injection-like tool output and forged tenant/credential arguments cannot bypass policy; trace linkage and accounting remain complete.

---

# Phase 91: Webhook Triggers

**Dependencies:** Phase 90. **Requirements:** R10.

**Implementation scope**

- Persist tenant-owned trigger configuration bound to a definition/version selection policy and scoped service principal.
- Verify request signatures, freshness, payload limits, enablement, and event IDs before mapping input into the shared start contract.
- Atomically record receipt/deduplication, resolve a version, create the run, and enqueue; return prompt receipt status.
- Add trigger delivery history and secret rotation behavior; reject invalid/disabled/revoked triggers.

**Acceptance and validation**

- Concurrent replay of one signed event starts one run; changed event content under the same key conflicts.
- Forged signatures, stale timestamps, oversized bodies, disabled triggers, and cross-tenant references fail safely.
- Publication or principal revocation races have defined outcomes; accepted retries keep the original pinned version.

---

# Phase 92: Scheduled and Cron Triggers

**Dependencies:** Phase 91. **Requirements:** R10.

**Implementation scope**

- Persist schedule expression, IANA timezone, UTC next fire time, enablement, version policy, principal, and concurrency/missed-run policy.
- Implement durable scheduler claims and per-fire idempotency so multiple replicas cannot double-fire.
- Apply planned defaults: skip nonexistent DST times, use the earlier ambiguous instant once, coalesce missed ticks into one catch-up, one active run per schedule.
- Share run-start validation/authorization with manual/webhook starts; audit schedule edits and expose next/last fire status.

**Acceptance and validation**

- Fake-clock tests cover timezone/DST, downtime, pause/resume, invalid cron, active-run overlap, and deadline boundaries.
- Concurrent scheduler replicas and crashes between fire reservation/enqueue produce one run per intended fire.
- Version resolution, disabled membership, and changed schedule configuration cannot silently reuse unauthorized work.

---

# Phase 93: Generic Workflow Builder Editor

**Dependencies:** Phase 92. **Requirements:** R11.

**Implementation scope**

- Add definition listing, draft creation, graph canvas, node/edge editing, and typed configuration forms for all eight step types.
- Expose bindings, conditions, tool selection, retry/timeout policy, approval, delay, parallel joins, and bounded revision settings.
- Save/load drafts with conflict handling and schema errors attached to the relevant field/node.
- Provide accessible keyboard/form alternatives, responsive layouts, empty/loading/error states, and permission-aware edit controls.

**Acceptance and validation**

- Through UI, build and save a deterministic graph different from the three business templates without code changes.
- Reopen/edit the graph with equivalent semantics; invalid connections/configuration produce actionable validation.
- Typecheck and focused frontend interaction/smoke checks cover all node forms, stale drafts, and tenant/permission boundaries.

---

# Phase 94: Builder Validation Publication and Version History

**Dependencies:** Phase 93. **Requirements:** R11.

**Implementation scope**

- Add server-backed validation, runnable-capability feedback, version history/diffs, and admin-only publication.
- Provide manual run input and start controls tied to an explicit published version, retaining client idempotency keys across retries.
- Explain draft versus published state and show that running workflows retain their pinned versions.
- Expose trigger configuration forms and enablement/history for webhook and cron APIs, with secrets masked.

**Acceptance and validation**

- Publish two versions; a paused v1 run stays on v1 and a later start uses the selected/new published version.
- Invalid graphs, unsupported runtime configuration, unauthorized publication, and duplicate start clicks behave correctly.
- UI checks cover condition/tool/trigger configuration, save conflicts, publication errors, and masked secrets.

---

# Phase 95: Generic Graph Run Debugger

**Dependencies:** Phase 94. **Requirements:** R11.

**Implementation scope**

- Render the run's immutable graph with selected/skipped edges, branch/iteration state, and readable node status.
- Show node input/output, attempt history, tool calls, model/prompt, cost/tokens, latency, logs/errors, approval and wait details.
- Add paginated trace APIs/readers and historical AgentStep compatibility without duplicating usage totals.
- Handle large payloads with bounded previews, authorized detail access, redaction, and useful partial-failure states.

**Acceptance and validation**

- Debug deterministic, LLM, tool, approval, delay, parallel, failed, cancelled, and historical runs.
- Repeated nodes/branches map to the correct attempt/output; graph version never follows a later draft edit.
- API authorization/pagination tests and frontend typecheck/smoke/interaction checks pass, including empty and large traces.

---

# Phase 96: Safe Manual Retry and Recovery Controls

**Dependencies:** Phase 95. **Requirements:** R06, R11.

**Implementation scope**

- Add authorized cancel, retry, and dead-letter/reconciliation controls with explicit eligibility and audit history.
- Infrastructure retries within an active run use existing budgets; terminal-run retry creates a linked recovery run rather than reopening history.
- Recovery pins the original version/input and reuses completed outputs plus original logical effect keys where safe; changed inputs require a new start and fresh approval.
- Never automatically repeat an unknown side effect or reuse stale approval. Show why recovery is blocked and what must be resolved.

**Acceptance and validation**

- Double-clicks and concurrent operators create one recovery action; terminal histories remain immutable.
- Successful side effects do not repeat during recovery; uncertain effects require recorded reconciliation.
- Tests cover unauthorized recovery, changed inputs, expired approval, exhausted budgets, and cancellation races; UI presents accurate eligibility.

---

# Phase 97: Worker Observability and Live Updates

**Dependencies:** Phase 96. **Requirements:** R11.

**Implementation scope**

- Add tenant-scoped operations APIs/UI for queued/running/failed/retrying/dead-letter jobs, stale leases, worker availability, queue wait, and throughput.
- Export operational worker metrics without secrets or high-cardinality sensitive labels; distinguish global admin operations from tenant views.
- Poll run/debugger/approval/operations pages with bounded intervals, stop/backoff behavior, and reliable refresh after mutations.
- Extend existing event/cost observability and document incident diagnosis for stalled or repeatedly failing runs.

**Acceptance and validation**

- Verify metrics across claim, heartbeat loss, retry, wait, recovery, and completion; totals match persisted attempts.
- No tenant can read another tenant's jobs, aggregates, events, or worker-associated payloads.
- UI checks cover reconnect/offline states, terminal polling stop, long-running waits, and stale leases; load is bounded.

---

# Phase 98: Deterministic Throughput Benchmark

**Dependencies:** Phase 97. **Requirements:** R12.

**Implementation scope**

- Build a reproducible benchmark CLI/workload generator with fixed seed and no paid LLM calls.
- Run at least 10,000 accepted deterministic workflows, increasing worker concurrency with bounded input size; include conditions, parallelism, and controlled effect-sink actions.
- Measure accepted/completed/failed counts, queue/execution latency percentiles, throughput, duplicate starts, retries, and resources.
- Save machine-readable results plus a report identifying commit, environment, duration, workload, and observed limits.

**Acceptance and validation**

- Reconcile every accepted run to persisted status and every intended sink action to observed effect identity after drain.
- Assert no lost jobs or duplicate effects in the controlled sink; disclose expected failures rather than excluding them.
- Run a small CI-sized sample and the documented full benchmark; numeric speed claims come from results, not invented targets.

---

# Phase 99: Crash and Concurrency Reliability Experiments

**Dependencies:** Phase 98. **Requirements:** R12.

**Implementation scope**

- Add reproducible fault scenarios for worker death, expired leases, duplicate delivery, database outage, timeout-after-effect, and rolling worker restarts.
- Exercise approval/cancel races, parallel joins, scheduler replica races, and recovery/dead-letter controls.
- Measure recovery time, final counts, duplicates prevented, unknown remote outcomes, and any lost effects.
- Publish raw evidence and a failure analysis; fix findings before considering this phase complete.

**Acceptance and validation**

- After each controlled recovery, every accepted job is accounted for and the idempotent sink has zero lost/duplicate intended effects.
- Non-idempotent unknown outcomes remain explicitly unresolved until reconciliation; do not relabel them as exactly-once success.
- Repeat the failed scenario after a fix, verify adjacent affected invariants, and record limitations of the tested environment.

---

# Phase 100: Production Container Packaging

**Dependencies:** Phase 99. **Requirements:** R13.

**Implementation scope**

- Add production web/API/worker builds and a reproducible local production profile separate from development bind mounts.
- Configure verified auth, trusted origins, database connections, secret references, logging, bounded resources, health/readiness, and graceful shutdown.
- Add one-shot migration and deterministic demo/verification commands; document deployment order and backward-compatible rollout requirements.
- Keep provider credentials and external effect fixtures disabled by default in demo validation.

**Acceptance and validation**

- Build/start production images with a disposable database; run migrations and a deterministic end-to-end workflow.
- Readiness fails when required dependencies are unavailable, and shutdown drains or safely releases worker ownership.
- Validate image/configuration safety, no embedded secrets, frontend API routing, and restart persistence.

---

# Phase 101: Kubernetes Deployment Manifests

**Dependencies:** Phase 100. **Requirements:** R13.

**Implementation scope**

- Add reproducible Kubernetes resources for web, API, workers, services/ingress, configuration/secrets references, migration Job, and worker metrics.
- Provide a local cluster profile with persistent Postgres and a hosted profile using an explicitly configured managed database or persistent database deployment.
- Set readiness/liveness/startup behavior, resource requests/limits, least-privilege service accounts, rollout strategy, and graceful termination windows.
- Document cluster prerequisites, secret provisioning, database/TLS configuration, and scaled worker operation.

**Acceptance and validation**

- Validate rendered manifests and deploy to a disposable local cluster; migration runs in the correct order.
- Access the UI/API and complete an authenticated deterministic workflow; inspect worker metrics and persistence after pod restart.
- No real credentials are committed; hosted configuration is documented without claiming it was deployed.

---

# Phase 102: Kubernetes Operations and Recovery Verification

**Dependencies:** Phase 101. **Requirements:** R13.

**Implementation scope**

- Run the deployed system through rolling API/worker updates, worker replica scaling, pod loss, and readiness failure.
- Verify database backup/restore and a compatible rollback procedure using a disposable dataset.
- Record cluster/image/commit details, commands, observed metrics, workflow/effect reconciliation, and screenshots or logs in deployment evidence.
- Complete the local-cluster acceptance path; perform hosted deployment only when an authorized target/access is available and track that status separately.

**Acceptance and validation**

- Work remains accounted for across rollout/pod loss, stale workers cannot commit, and restored data retains version/approval/effect history.
- A clean environment can follow the runbook and repeat deployment plus deterministic verification.
- A failed required local check blocks completion; missing optional hosted access is disclosed and never represented as successful deployment.

---

# Phase 103: Platform README and Architecture Reconciliation

**Dependencies:** Phase 102. **Requirements:** R14.

**Implementation scope**

- Reframe README and product overview around the now-implemented durable workflow platform, using existing business flows as examples.
- Reconcile specification, architecture, agents, observability, deployment, security, evaluation, backlog, and progress with actual code.
- Explain graph/version pinning, generic state/attempts, queue ownership, retries/idempotency, tools, triggers, permissions, cancellation limits, and migration compatibility.
- Link measured benchmark/deployment/evaluation evidence; distinguish seeded fixtures, live checks, unsupported features, and remaining limits.

**Acceptance and validation**

- Every implemented-capability claim points to code or recorded acceptance evidence; all R01–R14 rows are accounted for.
- Documentation links, commands, diagrams, phase numbers, and status labels are consistent.
- Do not publish an exactly-once or production-security claim beyond tested guarantees; documentation review resolves contradictions.

---

# Phase 104: Platform Demo Video Script

**Dependencies:** Phase 103; replaces former Phase 66. **Requirements:** R14.

**Implementation scope**

- Write a short demo script covering the automation problem, builder/version publication, a tool/condition/approval path, and the generic debugger.
- Show durable retry or worker recovery, tenant-aware permissions, and the existing sales reviewer/human edit/final output flow.
- Include measured evaluation/cost tradeoffs, reliability results, and verified Kubernetes operation with clear demo-versus-live labels.
- Link each scene to reproducible data/setup and visible UI; this phase writes the script, not a generated video.

**Acceptance and validation**

- Walk through the script against the completed app and remove unavailable scenes or unsupported claims.
- Preserve the original problem/solution/sales/reviewer/approval/output/evaluation/improvement deliverables.
- Verify timing, links, seeded-versus-measured labels, and a concise recruiter-facing narrative.

---

# Phase 105: Final Workflow Platform Case Study

**Dependencies:** Phase 104; replaces former Phase 67. **Requirements:** R14.

**Implementation scope**

- Write the final case study: problem, goal, architecture, workflow/agent examples, evaluation methodology, reliability/deployment results, tradeoffs, lessons, and future work.
- Lead with the generic durable platform and support it with actual state/security/integration/operations evidence.
- Retain baseline-versus-multi-agent quality/cost/latency results without inventing improvement percentages.
- Complete the R01–R14 evidence checklist and record any limitations or explicitly unperformed hosted/provider checks.

**Acceptance and validation**

- All claims and numbers trace to recorded results; original case-study scope is preserved.
- Review setup reproducibility, links, diagrams, source coverage, and the complete phase ledger.
- Finish only after implementation/fix commits are pushed and final review has no unresolved blocking findings.

---

# Build order and stopping points

The historical build through Phase 65 is complete. The authorized expansion run
follows Phases 66–105 in numeric order. Dependency references are prerequisites,
not permission to skip intervening delivery gates. Consult the phase ledger for
the final completion decision; this catalog does not authorize additional work.

Milestone ranges and capability coverage are maintained in
[the implementation plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md#milestones-and-completion-gate);
execution status is maintained in [phase progress](phase-progress.md).

The expansion checkpoints are Phase 82 (generic durable runtime), Phase 85
(existing workflows migrated), Phase 97 (builder/debugger and automation), and
Phase 102 (reliability and deployment evidence). These are progress checkpoints;
the full requested scope, including final documentation, ends at Phase 105.
