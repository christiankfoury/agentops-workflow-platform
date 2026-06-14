# Enterprise Multi-Agent Workflow Platform - Project Specification

## 1. Project Overview

The Enterprise Multi-Agent Workflow Platform is a full-stack AI application that transforms business inputs into high-quality business outputs using measurable, stateful, multi-agent workflows.

Instead of using a single prompt to generate a final answer, the system routes work through specialized agents that analyze the input, review the analysis, retry when quality is low, pause for human approval when needed, and generate a final polished business document.

The project is designed to demonstrate that multi-agent workflows can improve factual accuracy, reduce unsupported claims, and provide better observability compared to a single-agent baseline.

## 2. Product Goal

The goal of this project is to build an enterprise-style AI workflow system that can:

* Accept business inputs such as sales reports, customer feedback, and incident logs.
* Process those inputs through specialized AI agents.
* Track each agent step, output, cost, latency, retry, and status.
* Use reviewer agents to detect unsupported or low-quality outputs.
* Use retry logic to improve low-quality agent responses.
* Include a human approval step before final output generation.
* Compare multi-agent workflow quality against a single-agent baseline.
* Show measurable improvement through an evaluation dashboard.

The final product should feel like a production AI workflow platform, not a toy agent demo.

## 3. Portfolio Positioning

This project is intended to demonstrate practical AI engineering skills that are valuable in enterprise environments.

The project should show experience with:

* Multi-agent orchestration
* Stateful multi-agent workflow orchestration
* Human-in-the-loop AI systems
* Agent evaluation
* Cost tracking
* Prompt versioning
* Observability
* Workflow state management
* Structured LLM outputs
* Baseline comparison
* Full-stack product development

The main portfolio message is:

> I built an enterprise-style multi-agent workflow platform that improves factual accuracy and reduces unsupported claims compared to a single-agent baseline.

## 4. Core Problem

Single-prompt AI workflows often produce outputs that are:

* Hard to inspect
* Hard to evaluate
* Prone to hallucinations
* Missing quality checks
* Missing human approval controls
* Difficult to compare against baselines
* Difficult to debug
* Difficult to trust in business settings

This project addresses those weaknesses by treating AI generation as a controlled workflow.

## 5. Core Solution

The system uses a multi-step workflow:

```text
Input
↓
Router Agent
↓
Specialized Analyst Agent
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
Evaluation + Observability
```

Each step is stored, scored, and displayed to the user.

The system does not only generate an answer. It explains how the answer was produced, how much it cost, how long it took, whether it required retries, and how it compares to a baseline.

## 6. Supported Use Cases

The platform will support three primary business workflows.

## 6.1 Sales Report to Executive Summary

### User Input

A sales report containing information such as:

* Revenue changes
* Regional performance
* Product performance
* Customer churn
* Sales pipeline updates
* Risks and opportunities

### User Request

Generate an executive summary for leadership.

### Workflow

```text
Sales Report
↓
Sales Analyst Agent
↓
Reviewer Agent
↓
Retry Logic
↓
Human Approval
↓
Executive Writer Agent
↓
Final Executive Summary
```

### Final Output

A polished executive summary containing:

* Business performance overview
* Key findings
* Risks
* Opportunities
* Recommended actions
* Supporting evidence

### Example Success Claim

> The multi-agent workflow reduced unsupported claims in sales summaries compared to a single-agent baseline.

## 6.2 Customer Feedback to Product Insights Report

### User Input

Customer feedback from sources such as:

* Reviews
* Support tickets
* NPS comments
* Feature requests
* Bug reports
* Survey responses

### User Request

Analyze customer feedback and create a product insights report.

### Workflow

```text
Customer Feedback
↓
Classifier Agent
↓
Insight Agent
↓
Reviewer Agent
↓
Retry Logic
↓
Human Approval
↓
Product Report Writer Agent
↓
Final Product Insights Report
```

### Final Output

A structured product insights report containing:

* Top customer pain points
* Common feedback themes
* Feature requests
* Bug patterns
* Customer sentiment
* Product recommendations
* Supporting examples

### Example Success Claim

> The reviewer agent reduced unsupported product insights by checking whether recommendations were backed by actual customer feedback examples.

## 6.3 Incident Log to Post-Incident Report

### User Input

An incident log containing timestamped operational events.

Example:

```text
10:02 AM - API latency increased
10:08 AM - Error rate exceeded threshold
10:15 AM - Database connection pool saturated
10:25 AM - Workers restarted
10:40 AM - Latency returned to normal
```

### User Request

Generate a post-incident report for leadership and engineering.

### Workflow

```text
Incident Log
↓
Timeline Agent
↓
Root Cause Agent
↓
Reviewer Agent
↓
Retry Logic
↓
Human Approval
↓
Incident Report Writer Agent
↓
Final Post-Incident Report
```

### Final Output

A post-incident report containing:

* Summary
* Timeline
* Impact
* Confirmed facts
* Inferred causes
* Root cause analysis
* Follow-up actions
* Prevention recommendations

### Example Success Claim

> The workflow improved incident report quality by separating confirmed facts from inferred root-cause claims.

## 7. Agent Roles

## 7.1 Router Agent

The Router Agent detects the workflow type from the input.

It should classify input as one of:

* Sales report
* Customer feedback
* Incident log

Example output:

```json
{
  "workflow_type": "incident_report",
  "confidence": 0.91,
  "reasoning_summary": "The input contains timestamped operational events and recovery notes."
}
```

Router behavior:

* If confidence is high, auto-select the workflow.
* If confidence is medium, suggest the workflow and ask for confirmation.
* If confidence is low, require manual workflow selection.

The Router Agent is an optional advanced feature, but it should be included in the final project.

## 7.2 Sales Analyst Agent

The Sales Analyst Agent extracts structured findings from sales reports.

Responsibilities:

* Identify key business findings
* Extract important numbers
* Identify risks
* Identify opportunities
* Recommend actions
* Include supporting evidence

Expected output:

```json
{
  "key_findings": [],
  "risks": [],
  "opportunities": [],
  "recommendations": [],
  "supporting_evidence": []
}
```

## 7.3 Customer Feedback Classifier Agent

The Classifier Agent groups customer feedback into themes.

Responsibilities:

* Categorize feedback
* Count repeated themes
* Identify sentiment patterns
* Extract representative examples

Expected categories may include:

* Pricing
* Bugs
* Feature requests
* Performance
* Usability
* Support experience

Expected output:

```json
{
  "themes": [
    {
      "name": "performance",
      "count": 14,
      "sentiment": "negative",
      "examples": []
    }
  ]
}
```

## 7.4 Customer Feedback Insight Agent

The Insight Agent turns classified customer feedback into product insights.

Responsibilities:

* Identify top pain points
* Detect recurring feature requests
* Summarize customer needs
* Recommend product actions
* Link recommendations to supporting examples

Expected output:

```json
{
  "top_insights": [],
  "customer_pain_points": [],
  "feature_requests": [],
  "risks": [],
  "recommendations": [],
  "supporting_examples": []
}
```

## 7.5 Timeline Agent

The Timeline Agent extracts chronological events from incident logs.

Responsibilities:

* Parse timestamps
* Extract event descriptions
* Preserve source evidence
* Order events chronologically
* Identify missing or ambiguous timestamps

Expected output:

```json
{
  "timeline": [
    {
      "time": "10:02 AM",
      "event": "API latency increased",
      "source_evidence": "10:02 AM - API latency increased"
    }
  ]
}
```

## 7.6 Root Cause Agent

The Root Cause Agent analyzes incident timelines.

Responsibilities:

* Identify confirmed facts
* Identify possible causes
* Separate confirmed claims from inferred claims
* Estimate impact
* Recommend follow-up actions

Expected output:

```json
{
  "confirmed_facts": [],
  "likely_causes": [],
  "unknowns": [],
  "impact": [],
  "follow_up_actions": []
}
```

## 7.7 Reviewer Agent

The Reviewer Agent evaluates another agent's output against the original input.

Responsibilities:

* Check factual accuracy
* Identify unsupported claims
* Verify numbers
* Verify whether recommendations are supported
* Assign a quality score
* Recommend approval, retry, or human review

Expected output:

```json
{
  "approved": false,
  "quality_score": 0.78,
  "issues": [
    {
      "claim": "Enterprise churn doubled",
      "problem": "The source only says churn increased, not doubled.",
      "severity": "high"
    }
  ],
  "retry_recommended": true
}
```

The Reviewer Agent is one of the most important parts of the project because it creates measurable quality control.

## 7.8 Writer Agent

The Writer Agent creates the final polished business document.

Responsibilities:

* Use only approved or human-edited analysis
* Write clearly for the target audience
* Avoid adding unsupported new claims
* Preserve important numbers
* Include risks and recommendations
* Produce a professional final report

The Writer Agent should only run after:

* Reviewer approval, or
* Human approval, or
* Human-edited analysis is submitted

## 7.9 Evaluator Agent

The Evaluator Agent scores generated outputs during evaluation runs.

Responsibilities:

* Compare generated outputs against expected facts
* Score factual accuracy
* Score completeness
* Identify unsupported claims
* Score clarity and usefulness
* Produce evaluation metadata

The Evaluator Agent should support evaluation, but the system should also include deterministic checks where possible.

## 8. Core Workflow States

Each workflow run should move through explicit states.

Required states:

```text
created
running
routing
analyst_running
reviewer_running
retrying
waiting_for_human
writer_running
completed
failed
cancelled
```

State transitions should be stored and displayed in the UI.

## 9. Retry Logic

The system should include score-based retry logic.

Initial rules:

```text
If reviewer_score >= 0.85:
  continue to Writer Agent

If reviewer_score >= 0.70 and no high-severity issues:
  require human approval

If reviewer_score < 0.70:
  retry the Analyst Agent with reviewer feedback

If high-severity issues exist:
  require retry or human approval

If retry_count > 2:
  stop automatic retries and require human approval
```

Retries should store:

* Retry count
* Retry reason
* Reviewer feedback used
* Previous failed output
* New output
* Whether quality improved

## 10. Human Approval

The system must include a human approval step.

A human reviewer should be able to:

* Approve the analysis
* Reject the workflow
* Request a retry
* Edit the structured analysis before final writing
* Add reviewer notes

Approval records should store:

* Workflow run ID
* Reviewer score
* Reviewer issues
* Human decision
* Human feedback
* Edited analysis, if any
* User who approved
* Resolution timestamp

## 11. Baseline Workflow

The project must include a single-agent baseline.

Baseline workflow:

```text
Input
↓
Single LLM Prompt
↓
Final Output
```

The baseline should not use:

* Reviewer Agent
* Retry logic
* Human approval
* Specialized intermediate agents

The purpose of the baseline is to compare output quality, cost, and latency against the multi-agent workflow.

## 12. Evaluation Framework

The system should include a repeatable evaluation framework.

Evaluation should compare:

```text
Single-agent baseline
vs
Multi-agent workflow
```

The same input should be run through both modes.

Each evaluation case should include:

* Workflow type
* Input text
* Expected facts
* Expected risks
* Expected recommendations
* Expected timeline events, if applicable
* Expected themes, if applicable
* Notes for evaluation

## 13. Evaluation Metrics

The system should track the following metrics.

## 13.1 Factual Accuracy

Measures how many generated claims are correct.

Formula:

```text
correct claims / total generated claims
```

## 13.2 Unsupported Claim Rate

Measures how many generated claims are not supported by the source input.

Formula:

```text
unsupported claims / total generated claims
```

This is one of the most important metrics for the project.

## 13.3 Completeness

Measures how many expected facts were captured.

Formula:

```text
captured expected facts / total expected facts
```

## 13.4 Human Approval Rate

Measures how often outputs pass human review.

Formula:

```text
approved workflows / workflows requiring approval
```

## 13.5 Retry Improvement Rate

Measures whether retry logic improves reviewer scores.

Formula:

```text
retries that improved score / total retries
```

## 13.6 Cost Per Workflow

Measures the estimated LLM cost for each workflow.

Track:

* Input tokens
* Output tokens
* Total tokens
* Cost per agent
* Cost per retry
* Total workflow cost

## 13.7 Latency

Measures how long the workflow takes.

Track:

* Latency per agent
* Total workflow latency
* Queue time, if background jobs are added
* Time waiting for human approval

## 13.8 Agent Failure Rate

Measures how often agent steps fail.

Track:

* LLM failures
* Timeout failures
* Invalid JSON
* Schema validation failures
* Retry exhaustion

## 14. Target Portfolio Metrics

The exact numbers will come from real evaluation results, but the project should aim to prove improvements like:

```text
Factual accuracy improved from 74% to 90%
Unsupported claim rate decreased from 21% to 6%
Completeness improved from 68% to 84%
Human approval rate improved from 61% to 87%
Average cost increased from $0.04 to $0.12 per workflow
Average latency increased from 13s to 41s
```

The important story is not that multi-agent workflows are always cheaper or faster.

The important story is:

> Multi-agent workflows cost more and take longer, but they produce safer, more accurate, and more trustworthy business outputs.

## 15. Dashboard Requirements

The app should include the following dashboard pages.

## 15.1 Home Dashboard

Shows a high-level summary:

* Total workflow runs
* Completed runs
* Failed runs
* Pending approvals
* Average quality score
* Average cost
* Average latency
* Recent activity

## 15.2 New Workflow Page

Allows the user to:

* Paste input text
* Upload supported files
* Select workflow type manually
* Use auto-detection with Router Agent
* Add optional instructions
* Start workflow

## 15.3 Workflow Runs Page

Shows all workflow runs.

Columns:

* Workflow title
* Workflow type
* Status
* Quality score
* Cost
* Latency
* Retry count
* Created date
* Created by

Run IDs should remain available in URLs, API responses, and debugging traces,
but the recruiter-facing table should prioritize workflow titles and readable
business context instead of raw UUIDs.

## 15.4 Workflow Run Detail Page

Shows a complete workflow trace.

Required sections:

* Original input
* Current status
* Final output
* Quality score
* Total cost
* Total latency
* Agent timeline
* Reviewer results
* Retry history
* Human approval history
* Workflow events

## 15.5 Agent Step Timeline

Shows each agent step:

* Agent name
* Status
* Started time
* Completed time
* Latency
* Model
* Prompt version
* Input tokens
* Output tokens
* Estimated cost
* Output preview
* Error message, if failed

## 15.6 Human Approval Page

Shows workflows waiting for review.

The reviewer should see:

* Original input
* Agent analysis
* Reviewer score
* Reviewer issues
* Retry recommendation
* Actions

Available actions:

* Approve
* Request retry
* Edit analysis
* Reject

## 15.7 Final Output Page

Shows:

* Final generated business document
* Workflow summary
* Quality score
* Approval status
* Cost
* Latency
* Trace summary
* Export options

## 15.8 Evaluation Dashboard

Compares baseline vs multi-agent results.

Required metrics:

* Factual accuracy
* Unsupported claim rate
* Completeness
* Human approval rate
* Average retries
* Average cost
* Average latency

The dashboard should include a table like:

| Metric             | Baseline | Multi-Agent |
| ------------------ | -------: | ----------: |
| Factual Accuracy   |      74% |         90% |
| Unsupported Claims |      21% |          6% |
| Completeness       |      68% |         84% |
| Avg Cost           |    $0.04 |       $0.12 |
| Avg Latency        |      13s |         41s |

## 15.9 Cost Dashboard

Shows:

* Total cost
* Average cost per workflow
* Cost by workflow type
* Cost by agent
* Token usage by agent
* Most expensive workflow runs
* Cost caused by retries

## 15.10 Prompt Control Center

Shows:

* Shared Governance prompts for Router, Reviewer, and Writer.
* Workflow-specific prompts grouped by Sales, Customer Feedback, and Incident.
* Product-facing agent labels instead of raw enum values.
* Active prompt name, version, usage, and template preview.
* Prompt history with active/inactive status.
* Prompt detail pages that explain operational impact and future-run scope.
* Ability to create and activate prompt versions.

Prompt pages should make clear that prompt changes affect future agent runs only
and do not mutate completed workflow outputs.

## 15.11 Agent Performance Dashboard

Shows metrics per agent:

* Average score
* Average cost
* Average latency
* Failure rate
* Retry rate
* Schema validation failure rate

## 15.12 Failure Case Explorer

Shows:

* Lowest scoring runs
* Failed workflows
* Most common reviewer issues
* Most common schema failures
* Human-rejected outputs
* Regression cases

## 16. Observability Requirements

The system should log workflow events.

Important event types:

```text
workflow_started
workflow_completed
workflow_failed
router_started
router_completed
agent_started
agent_completed
agent_failed
reviewer_started
reviewer_completed
reviewer_rejected_output
retry_triggered
human_approval_required
human_approved
human_rejected
human_requested_retry
writer_started
writer_completed
evaluation_started
evaluation_completed
```

Each event should include:

* Workflow run ID
* Agent step ID, if applicable
* Event type
* Timestamp
* Metadata
* Error message, if applicable

## 17. Prompt Versioning Requirements

Prompts should be versioned.

Each prompt version should include:

* Prompt name
* Agent type
* Version number
* Template text
* Active status
* Created date
* Created by
* Notes

Prompt versions should support evaluation comparisons.

Example:

```text
Sales Analyst Prompt v1 vs Sales Analyst Prompt v2
Reviewer Prompt v1 vs Reviewer Prompt v2
```

The system should track which prompt version was used for each agent step.

## 18. Cost Tracking Requirements

The system should track cost at the agent level and workflow level.

Each agent step should store:

* Model
* Input tokens
* Output tokens
* Total tokens
* Estimated input cost
* Estimated output cost
* Total estimated cost

Each workflow run should store:

* Total tokens
* Total cost
* Cost by agent
* Cost by retry
* Cost by workflow type

## 19. Data Model Overview

The main database entities should include:

```text
users
organizations
organization_members
uploaded_inputs
workflow_runs
agent_steps
workflow_events
human_approvals
prompt_versions
cost_events
evaluation_cases
evaluation_results
audit_logs
notifications
```

## 20. Main Database Tables

## 20.1 workflow_runs

Stores one workflow execution.

Fields:

```text
id
organization_id
created_by_user_id
workflow_type
run_mode
status
input_id
final_output
quality_score
total_cost
total_tokens
latency_ms
retry_count
created_at
completed_at
```

`run_mode` should support:

```text
baseline
multi_agent
```

## 20.2 agent_steps

Stores each agent execution.

Fields:

```text
id
workflow_run_id
agent_name
agent_type
step_order
status
input_json
output_json
model
prompt_version_id
tokens_input
tokens_output
total_tokens
cost
latency_ms
retry_count
error_message
created_at
completed_at
```

## 20.3 uploaded_inputs

Stores input text and file metadata.

Fields:

```text
id
organization_id
created_by_user_id
title
input_type
raw_text
file_name
file_type
file_size
created_at
```

## 20.4 human_approvals

Stores human review decisions.

Fields:

```text
id
workflow_run_id
reviewer_score
issues_json
status
human_feedback
edited_analysis_json
approved_by_user_id
created_at
resolved_at
```

## 20.5 prompt_versions

Stores prompt templates.

Fields:

```text
id
agent_type
name
version
template
is_active
notes
created_by_user_id
created_at
```

## 20.6 workflow_events

Stores observability events.

Fields:

```text
id
workflow_run_id
agent_step_id
event_type
message
metadata_json
created_at
```

## 20.7 evaluation_cases

Stores test cases.

Fields:

```text
id
workflow_type
title
input_text
expected_facts_json
expected_risks_json
expected_recommendations_json
expected_themes_json
expected_timeline_json
notes
created_at
```

## 20.8 evaluation_results

Stores evaluation results.

Fields:

```text
id
evaluation_case_id
workflow_run_id
run_mode
prompt_version_summary_json
factual_accuracy
unsupported_claim_rate
completeness_score
human_approval_required
human_approved
retry_count
cost
latency_ms
judge_notes
created_at
```

## 20.9 audit_logs

Stores important user actions.

Fields:

```text
id
organization_id
user_id
action
resource_type
resource_id
metadata_json
created_at
```

## 21. Recommended Tech Stack

## 21.1 Frontend

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Recharts
```

## 21.2 Backend

```text
FastAPI
Python
Pydantic
SQLAlchemy
Alembic
PostgreSQL
```

## 21.3 Agent Orchestration

```text
Service-based stateful workflow orchestration
```

The current implementation uses FastAPI services and database-backed workflow
state transitions. LangGraph-style orchestration remains a possible future
extension, but the implementation should be described according to the code that
exists today.

Stateful orchestration is needed because the project requires:

* Stateful workflows
* Conditional routing
* Retry logic
* Human approval pauses
* Multi-step execution
* Workflow state inspection

## 21.4 LLM Provider

Initial provider:

```text
OpenAI
```

The backend should use an LLM abstraction so the system is not tightly coupled to one provider.

## 21.5 Background Jobs

Recommended later:

```text
Celery
Redis
```

Simpler early option:

```text
FastAPI background tasks
```

## 21.6 Authentication

Recommended options:

```text
Clerk
Auth.js
Supabase Auth
```

For the first version, authentication can be added after the core workflow works.

## 21.7 Deployment

Recommended deployment options:

```text
Azure
Render
Railway
Fly.io
```

For a portfolio project, the priority is a stable live demo with seeded data and a clean README.

## 22. MVP Scope

The MVP should focus on one complete workflow first:

```text
Sales Report -> Executive Summary
```

MVP features:

* Create workflow run
* Paste sales report input
* Run Sales Analyst Agent
* Run Reviewer Agent
* Retry if reviewer score is low
* Pause for human approval if needed
* Run Writer Agent after approval
* Store agent steps
* Show workflow timeline
* Track cost and latency
* Run baseline single-agent workflow
* Compare baseline vs multi-agent results
* Show evaluation dashboard

The MVP is complete when the project can prove a measurable improvement over the baseline for sales reports.

## 23. Full Project Scope

The full project includes:

* Sales report workflow
* Customer feedback workflow
* Incident report workflow
* Router Agent
* Reviewer Agent
* Writer Agent
* Retry logic
* Human approval
* Prompt versioning
* Cost tracking
* Observability timeline
* Evaluation dashboard
* Baseline comparison
* Agent performance dashboard
* Failure case explorer
* Authentication
* Role-based permissions
* Audit trail
* Notifications
* Background jobs
* Live workflow updates
* Demo dataset
* Deployment
* Portfolio case study

## 24. Non-Goals

The project will not try to be:

* A general-purpose chatbot
* A generic AutoGPT clone
* A fully autonomous system with no human control
* A replacement for business analysts
* A production SaaS billing system
* A massive enterprise platform with every possible integration

The project is focused on measurable multi-agent workflow quality.

## 25. Success Criteria

The project is successful if it can demonstrate:

* A working multi-agent workflow from input to final output
* Clear agent state tracking
* Reviewer Agent catches low-quality or unsupported claims
* Retry logic improves outputs
* Human approval controls final generation
* Evaluation system compares baseline vs multi-agent workflow
* Dashboard shows quality, cost, latency, and retry metrics
* README clearly explains the architecture and results
* Recruiters can understand the value in under two minutes

## 26. Final Portfolio Claims to Prove

The project should aim to prove claims like:

> Built a full-stack enterprise multi-agent workflow platform using FastAPI, Next.js, PostgreSQL, and stateful service orchestration.

> Implemented stateful AI workflows with specialized Analyst, Reviewer, Writer, Router, and Evaluator agents.

> Added human-in-the-loop approval so low-confidence or high-risk outputs require review before final generation.

> Built score-based retry logic that automatically revises low-quality agent outputs using reviewer feedback.

> Created an evaluation framework comparing single-agent and multi-agent workflows across business document test cases.

> Improved factual accuracy from baseline to multi-agent workflow results.

> Reduced unsupported claims through reviewer-agent validation and retry logic.

> Tracked cost, latency, token usage, retries, and agent failure rates across workflow runs.

> Built observability dashboards for workflow traces, agent performance, evaluation results, cost tracking, and failure cases.

## 27. Example Final Case Study Headline

The final case study headline should be:

> Built an enterprise-style multi-agent workflow platform that improved factual accuracy and reduced unsupported claims compared to a single-agent baseline across business document workflows.

## 28. Phase 1 Completion Checklist

Phase 1 is complete when:

* This project specification exists in `docs/PROJECT_SPEC.md`
* Core use cases are defined
* Agent roles are defined
* Workflow states are defined
* Evaluation metrics are defined
* Dashboard requirements are defined
* Data model overview is defined
* MVP scope is clear
* Full project scope is clear
* Portfolio claims are clear
