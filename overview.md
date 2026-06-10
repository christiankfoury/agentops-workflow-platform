# Multi-Agent Workflow Platform

A multi-agent workflow platform that takes business documents, routes work through specialized agents, tracks every decision, evaluates output quality, controls cost, and supports human approval before final delivery.

---

# Use Cases

## Use Case 1: Sales Report Analysis

### Input

```text
Q1 Sales Report
Revenue by region
Top products
Underperforming segments
Customer churn notes
Pipeline updates
```

### Request

```text
Analyze this sales report and create an executive summary for leadership.
```

### Agent flow

```text
Input
↓
Analyst Agent
↓
Reviewer Agent
↓
Human Approval
↓
Writer Agent
↓
Final Executive Summary
```

### Agent outputs

**Analyst Agent** extracts key facts:

```json
{
  "revenue_change": "+12%",
  "best_region": "North America",
  "worst_region": "EMEA",
  "top_risk": "Enterprise churn increased",
  "recommended_action": "Prioritize retention for enterprise accounts"
}
```

**Reviewer Agent** checks:

```text
Are the claims supported by the source document?
Are numbers copied correctly?
Are there hallucinated claims?
Are risks and recommendations reasonable?
```

**Writer Agent** creates the final output:

```text
Executive Summary:
Revenue grew 12% quarter-over-quarter, primarily driven by North America...
```

---

## Use Case 2: Customer Feedback Analysis

### Input

A CSV or text file containing customer feedback:

```text
Customer reviews
Support tickets
NPS comments
Feature requests
Bug complaints
```

### Request

```text
Analyze this customer feedback and create a product insights report.
```

### Agent flow

```text
Input
↓
Classifier Agent
↓
Insight Analyst Agent
↓
Reviewer Agent
↓
Human Approval
↓
Writer Agent
```

### Agent outputs

**Classifier Agent** groups feedback into categories:

```json
{
  "pricing": 18,
  "bugs": 24,
  "feature_requests": 31,
  "support_experience": 12,
  "performance": 15
}
```

**Insight Analyst Agent** identifies patterns:

```text
The most common issue is performance on mobile devices.
Many users requested bulk export functionality.
Pricing complaints are concentrated among small businesses.
```

**Reviewer Agent** checks whether the insights are backed by the feedback data.

**Writer Agent** creates a structured product report.

### Final output

```text
Product Insights Report

Top Themes:
1. Mobile performance complaints
2. Bulk export feature requests
3. Pricing concerns from SMB users

Recommended Actions:
1. Prioritize mobile optimization
2. Add bulk export to roadmap
3. Test SMB pricing package
```

---

## Use Case 3: Incident Report Generator

### Input

An incident log:

```text
10:02 AM - API latency increased
10:08 AM - Error rate exceeded threshold
10:15 AM - Database connection pool saturated
10:25 AM - Engineering restarted workers
10:40 AM - Latency returned to normal
```

### Request

```text
Generate a post-incident report for leadership and engineering.
```

### Agent flow

```text
Input
↓
Timeline Agent
↓
Root Cause Agent
↓
Reviewer Agent
↓
Human Approval
↓
Writer Agent
```

### Agent outputs

**Timeline Agent** extracts the event sequence.

**Root Cause Agent** proposes likely causes and impact.

**Reviewer Agent** checks whether the root cause is explicitly supported or only inferred.

**Writer Agent** creates the final incident report.

### Final output

```text
Incident Report

Summary:
On March 14, the API experienced elevated latency for 38 minutes...

Timeline:
10:02 - Latency increased
10:08 - Error rate exceeded threshold
10:15 - DB connection pool saturated
10:25 - Workers restarted
10:40 - Service recovered

Impact:
Customers experienced slower API responses.

Root Cause:
Likely database connection pool exhaustion.

Follow-up Actions:
1. Increase connection pool monitoring
2. Add autoscaling alert
3. Run load test before next release
```

---

# Agents

## 1. Analyst Agent

Extracts facts, identifies patterns, and produces structured analysis. Always outputs JSON so the Reviewer Agent can evaluate it.

Output format:

```json
{
  "key_findings": [],
  "risks": [],
  "recommendations": [],
  "supporting_evidence": []
}
```

---

## 2. Reviewer Agent

Evaluates the Analyst Agent's output.

Checks:

```text
Are claims supported by the source?
Are numbers accurate?
Are recommendations reasonable?
Is anything missing?
Are there hallucinations?
```

Output format:

```json
{
  "approved": false,
  "quality_score": 0.74,
  "issues": [
    {
      "claim": "Enterprise churn doubled",
      "problem": "Source only says churn increased, not doubled",
      "severity": "high"
    }
  ],
  "retry_recommended": true
}
```

---

## 3. Writer Agent

Turns approved analysis into a polished business document. Only runs after:

- Reviewer Agent approves, or
- Human approves despite warnings

---

## 4. Optional: Router Agent

Detects the input type and routes to the correct workflow.

Output format:

```json
{
  "workflow_type": "sales_report_analysis",
  "confidence": 0.92
}
```

Routes to:

```text
Sales Report Workflow
Customer Feedback Workflow
Incident Report Workflow
```

---

# Human Approval Step

```text
Reviewer Results

Quality Score: 82%

Issues Found:
1. Claim not fully supported
2. Recommendation is too vague

Options:
[Approve]
[Request Retry]
[Edit Analysis]
[Reject Workflow]
```

---

# Retry Logic

```text
If reviewer_score >= 0.85:
    continue to Writer Agent

If reviewer_score >= 0.70 and high_severity_issues == 0:
    ask for human approval

If reviewer_score < 0.70:
    retry Analyst Agent with reviewer feedback

If retries > 2:
    stop and require human intervention
```

---

# Agent State Tracking

A workflow run:

```json
{
  "run_id": "run_024",
  "workflow_type": "sales_report",
  "status": "completed",
  "current_step": "writer_agent",
  "started_at": "2026-06-09T14:00:00",
  "completed_at": "2026-06-09T14:02:31",
  "total_cost": 0.18,
  "total_tokens": 18422,
  "quality_score": 0.89
}
```

An agent step:

```json
{
  "step_id": "step_003",
  "agent_name": "Reviewer Agent",
  "status": "completed",
  "input": "...",
  "output": "...",
  "tokens_used": 4200,
  "cost": 0.04,
  "latency_ms": 8200,
  "retry_count": 1,
  "quality_score": 0.89
}
```

---

# Evaluation Framework

Test dataset: 10 samples per use case (30 total).

Each test case:

```json
{
  "input_file": "sales_report_001.txt",
  "expected_facts": [
    "Revenue increased 12%",
    "North America was the strongest region",
    "Enterprise churn increased"
  ],
  "expected_risks": [
    "Churn risk among enterprise customers"
  ],
  "expected_recommendations": [
    "Prioritize enterprise retention"
  ]
}
```

---

# Metrics

## 1. Factual accuracy

```text
Correct claims / total claims
```

## 2. Unsupported claim rate

```text
Unsupported claims / total claims
```

## 3. Completeness

```text
Captured expected facts / total expected facts
```

## 4. Human edit distance

```text
Percentage of final answer changed by human
```

## 5. Cost per workflow

```text
Total tokens
Total cost
Cost per agent
Cost per successful workflow
```

## 6. Latency

```text
Analyst Agent: 14.2s
Reviewer Agent: 8.7s
Writer Agent: 11.4s
Total workflow: 38.1s
```

---

# Baseline Comparison

Single-agent baseline:

```text
Input → Single LLM → Final report
```

Multi-agent workflow:

```text
Input → Analyst → Reviewer → Retry → Human Approval → Writer → Final report
```

| Metric                 | Single-Agent Baseline | Multi-Agent Workflow |
| ---------------------- | --------------------: | -------------------: |
| Factual accuracy       |                   74% |                  90% |
| Unsupported claim rate |                   21% |                   6% |
| Completeness           |                   68% |                  84% |
| Human approval rate    |                   61% |                  87% |
| Avg cost               |                 $0.04 |                $0.12 |
| Avg latency            |                   13s |                  41s |

---

# Dashboard Pages

## 1. Workflow Runs

| Run | Type              |         Status | Score |  Cost | Retries | Created   |
| --- | ----------------- | -------------: | ----: | ----: | ------: | --------- |
| #24 | Sales Report      |       Complete |   91% | $0.14 |       1 | Today     |
| #23 | Incident Report   | Needs Approval |   76% | $0.09 |       2 | Today     |
| #22 | Feedback Analysis |       Complete |   88% | $0.17 |       0 | Yesterday |

---

## 2. Run Detail Page

```text
Run #24: Sales Report Analysis

Input: q1_sales_report.pdf
Status: Complete
Final Score: 91%
Total Cost: $0.14
Total Latency: 43s

Steps:
1. Analyst Agent
2. Reviewer Agent
3. Retry
4. Human Approval
5. Writer Agent
```

Per agent:

```text
Agent: Reviewer Agent
Score: 78%
Issues Found: 2
Decision: Retry Analyst Agent
```

---

## 3. Human Approval Page

```text
Pending Approval

Workflow: Sales Report Analysis
Reviewer Score: 78%

Issues:
- Unsupported claim about enterprise churn
- Recommendation is too vague

Actions:
[Approve Anyway]
[Request Retry]
[Edit Output]
[Reject]
```

---

## 4. Evaluation Dashboard

Baseline vs Multi-Agent Workflow comparison across:

```text
Accuracy
Unsupported claims
Completeness
Cost
Latency
Human approval rate
```

---

## 5. Cost Dashboard

```text
Total cost
Cost per workflow type
Cost per agent
Token usage by agent
Most expensive runs
```

| Agent    | Avg Tokens | Avg Cost | Avg Latency |
| -------- | ---------: | -------: | ----------: |
| Analyst  |      4,200 |    $0.04 |         14s |
| Reviewer |      2,800 |    $0.03 |          9s |
| Writer   |      3,600 |    $0.04 |         12s |

---

# Tech Stack

## Frontend

```text
Next.js
TypeScript
Tailwind
shadcn/ui
Recharts
```

## Backend

```text
FastAPI
Python
Pydantic
SQLAlchemy
PostgreSQL
```

## Agent Orchestration

```text
LangGraph
```

LangGraph fits because the system needs:

```text
stateful workflows
conditional routing
retries
human approval pauses
multi-step execution
```

## Observability

Start with:

```text
structured logs
database trace table
workflow timeline UI
```

Optionally add:

```text
LangSmith
OpenTelemetry
```

---

# Database Schema

## Tables

```text
workflow_runs
agent_steps
human_approvals
evaluation_cases
evaluation_results
prompt_versions
cost_events
uploaded_files
```

## workflow_runs

```text
id
workflow_type
status
input_file_id
final_output
quality_score
total_cost
total_tokens
latency_ms
created_at
completed_at
```

## agent_steps

```text
id
workflow_run_id
agent_name
step_order
status
input_json
output_json
model
prompt_version
tokens_input
tokens_output
cost
latency_ms
retry_count
error_message
created_at
```

## human_approvals

```text
id
workflow_run_id
status
reviewer_score
issues_json
human_feedback
approved_by
created_at
resolved_at
```

## evaluation_cases

```text
id
workflow_type
input_text
expected_facts_json
expected_risks_json
expected_recommendations_json
created_at
```

## evaluation_results

```text
id
evaluation_case_id
run_type
accuracy_score
unsupported_claim_rate
completeness_score
cost
latency_ms
created_at
```

---

# Build Order

Start with one workflow:

```text
Sales Report → Executive Summary
```

Steps:

```text
1. Upload or paste sales report
2. Analyst Agent extracts structured findings
3. Reviewer Agent checks findings
4. Retry if score is too low
5. Human approval screen
6. Writer Agent creates final executive summary
7. Store every step in PostgreSQL
8. Show run timeline in dashboard
9. Run baseline comparison
```

Then duplicate the pattern for:

```text
Customer Feedback Analysis
Incident Report Generator
```
