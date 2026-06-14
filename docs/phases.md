Below is a full **PR-sized phase plan** for the entire Multi-Agent Workflow project.

The goal is that each phase is small enough to implement in one focused PR, but meaningful enough that the app keeps improving after every merge.

# Project: Enterprise Multi-Agent Workflow Platform

## Final outcome

This file is the historical PR-sized implementation plan for the project. Phases
1 through 65 are complete according to `docs/phase-progress.md`; later phases
should only be implemented when explicitly requested.

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

# Phase 66: Demo Video Script

Create a short demo video script.

Recommended structure:

```text
1. Problem: single-agent business reports hallucinate
2. Solution: multi-agent workflow with review, retry, and approval
3. Demo: run a sales report workflow
4. Show reviewer catching a problem
5. Show human approval
6. Show final output
7. Show evaluation dashboard
8. Show improvement numbers
```

This is what makes the project easy to understand quickly.

---

# Phase 67: Final Recruiter Case Study

Write a final case study for your portfolio.

Structure:

```text
Problem
Goal
Architecture
Agent workflow
Evaluation methodology
Results
Tradeoffs
What I learned
Future improvements
```

Your final headline should be something like:

> Built an enterprise-style multi-agent workflow platform that reduced unsupported claims by X% and improved factual accuracy by Y% compared to a single-agent baseline across 30 business-document evaluation cases.

This is the final deliverable that turns the app into a job-search asset.

---

# Recommended build order

The phases above are complete, but here is the practical order I would follow.

## Milestone 1: Full-stack skeleton

```text
Phase 1-7
```

Goal:

```text
You can create and view workflow runs.
```

## Milestone 2: First real workflow

```text
Phase 8-18
```

Goal:

```text
Sales Report workflow works end-to-end with Analyst, Reviewer, Human Approval, and Writer.
```

## Milestone 3: Measurement

```text
Phase 19-29
```

Goal:

```text
You can prove multi-agent improvement over baseline.
```

## Milestone 4: More workflows

```text
Phase 30-39
```

Goal:

```text
Customer Feedback and Incident Report workflows work end-to-end.
```

## Milestone 5: Optional enterprise features

```text
Phase 40-59
```

Goal:

```text
Router Agent, permissions, audit trail, notifications, prompt management, and advanced human review.
```

## Milestone 6: Production readiness

```text
Phase 60-80
```

Goal:

```text
Background jobs, live updates, evaluation polish, testing, deployment, README, and portfolio case study.
```

---

# Best stopping points

Because the phase plan is long, here are the best points where the project becomes portfolio-usable.

## Strong MVP

Stop after:

```text
Phase 27
```

You will have:

```text
Sales workflow
Reviewer
Retry logic
Human approval
Writer
Cost tracking
Baseline comparison
Evaluation dashboard
```

This is already a very strong project.

## Very strong portfolio project

Stop after:

```text
Phase 49
```

You will have:

```text
Three workflows
Router Agent
Prompt versioning
Evaluation dashboard
Cost dashboard
Agent performance dashboard
Baseline comparison page
```

This is excellent.

## Enterprise-grade showcase

Complete through:

```text
Phase 80
```

This becomes a serious flagship project. It may be too much for a quick portfolio build, but if done well, it could be your strongest AI project.
