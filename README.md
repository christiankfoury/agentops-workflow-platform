# AgentOps Workflow Platform

[![CI](https://github.com/christiankfoury/agentops-workflow-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/christiankfoury/agentops-workflow-platform/actions/workflows/ci.yml)

An enterprise-style multi-agent workflow platform for turning business documents
into reviewed, measurable outputs. The project compares a single-agent baseline
against a multi-agent workflow with specialized agents, reviewer checks, retry
logic, human approval, deterministic evaluation, cost tracking, and observability.

The portfolio claim this repo is built to prove:

> Multi-agent workflows cost more and take longer than a single prompt, but they
> produce safer, more complete, and more trustworthy business outputs.

## What It Does

AgentOps supports three business workflows:

| Workflow | Input | Output |
| --- | --- | --- |
| Sales Report | Revenue, pipeline, churn, regional performance | Executive summary |
| Customer Feedback | CSV/text reviews, tickets, NPS comments | Product insights report |
| Incident Log | Timestamped operational events | Post-incident report |

For each workflow, the app stores the input, every agent step, reviewer findings,
human approval decisions, final output, evaluation scores, costs, latency, retries,
and workflow events.

## Current Demo Results

The seeded demo dataset contains 32 evaluation cases: 10 sales reports, 10 customer
feedback datasets, 10 incident logs, and 2 sales remediation showcase cases. Each
case includes expected facts, risks, recommendations, and workflow-specific
expectations such as feedback themes or incident timeline events.

| Metric | Single-Agent Baseline | Multi-Agent Workflow |
| --- | ---: | ---: |
| Factual accuracy | 70% | 92% |
| Unsupported claim rate | 22% | 5% |
| Completeness | 64% | 88% |
| Average cost | $0.035 | $0.128 |
| Average latency | 4.2s | 18.4s |

These are deterministic seeded demo values intended to make the portfolio demo
immediately explorable. Live LLM-backed runs can produce different results.

## Architecture

```mermaid
flowchart LR
    User["User"]
    Web["Next.js Web App"]
    API["FastAPI API"]
    DB["PostgreSQL"]
    LLM["LLM Provider"]

    User --> Web
    Web --> API
    API --> DB
    API --> LLM

    subgraph Dashboards
        Runs["Workflow Runs"]
        Eval["Evaluation"]
        Compare["Comparison"]
        Cost["Cost"]
        Agents["Agent Performance"]
        Failures["Failure Explorer"]
    end

    Web --> Dashboards
```

```mermaid
flowchart TD
    Input["Business Input"]
    Router["Router Agent"]
    Specialist["Specialized Agent"]
    Reviewer["Reviewer Agent"]
    Retry{"Retry Needed?"}
    Human["Human Approval"]
    Writer["Writer Agent"]
    Final["Final Output"]
    Eval["Evaluation + Observability"]

    Input --> Router
    Router --> Specialist
    Specialist --> Reviewer
    Reviewer --> Retry
    Retry -- Yes --> Specialist
    Retry -- No / Needs Review --> Human
    Human --> Writer
    Writer --> Final
    Final --> Eval
```

## Key Features

- Multi-workflow support for sales reports, customer feedback, and incident logs.
- Router confidence thresholds for auto-select, confirmation, and manual fallback.
- Specialized analyst/classifier/timeline/root-cause agents per workflow.
- Reviewer agents that flag unsupported claims and low-quality analysis.
- Score-based retry logic and safe workflow state transitions.
- Human approval with structured analysis editing before writer execution.
- Writer agents that produce final business-ready reports.
- Single-agent baseline runs for comparison.
- Evaluation cases and results across all three workflows.
- Deterministic checks for expected facts, themes, timeline events, and unsupported
  generated numbers.
- Cost, token, latency, retry, failure, and schema validation tracking.
- Prompt version management and prompt-version performance comparison.
- Failure case explorer and improvement tracking dashboards.
- Demo mode that seeds polished data for portfolio walkthroughs.

## Product Tour

### Operations Dashboard

![AgentOps operations dashboard](docs/screenshots/dashboard.png)

### Multi-Agent Workflow Walkthroughs

Each workflow follows the same controlled pattern: structured intake, specialized
analysis, reviewer validation, human approval, and final report generation.

<details>
<summary><strong>Sales report workflow</strong></summary>

#### 1. Create the workflow

Configure the sales input, run mode, workflow type, and optional routing notes.

![Creating a sales report workflow](docs/screenshots/workflows/sales/01-create-workflow.png)

#### 2. Run the Sales Analyst

Start the specialist agent that extracts sales performance, risks, and
evidence-backed recommendations.

![Running the Sales Analyst](docs/screenshots/workflows/sales/02-run-analyst.png)

#### 3. Review and human approval

Inspect the completed analyst and reviewer steps before approving or editing the
analysis.

![Sales analysis ready for human approval](docs/screenshots/workflows/sales/03-review-and-human-approval.png)

#### 4. Final writer output

The Writer converts the approved analysis into the final executive report.

![Final sales report](docs/screenshots/workflows/sales/04-final-output.png)

</details>

<details>
<summary><strong>Customer feedback workflow</strong></summary>

#### 1. Create the workflow

Provide customer reviews, tickets, survey comments, or an uploaded CSV file.

![Creating a customer feedback workflow](docs/screenshots/workflows/customer-feedback/01-create-workflow.png)

#### 2. Run the Feedback Classifier

Start the classifier that organizes the source feedback into useful categories.

![Running the Feedback Classifier](docs/screenshots/workflows/customer-feedback/02-run-classifier.png)

#### 3. Generate insights, review, and approve

Inspect the completed classifier, insight, and reviewer steps before human
approval.

![Customer feedback insights ready for human approval](docs/screenshots/workflows/customer-feedback/03-insight-review-and-human-approval.png)

#### 4. Final writer output

The Writer turns the approved findings into a product insights report.

![Final customer feedback report](docs/screenshots/workflows/customer-feedback/04-final-output.png)

</details>

<details>
<summary><strong>Incident log workflow</strong></summary>

#### 1. Create the workflow

Provide timestamped operational events and any incident context.

![Creating an incident log workflow](docs/screenshots/workflows/incident/01-create-workflow.png)

#### 2. Run the Timeline Agent

Start the specialist that reconstructs the incident sequence from the source log.

![Running the Timeline Agent](docs/screenshots/workflows/incident/02-run-timeline.png)

#### 3. Analyze root cause, review, and approve

Inspect the completed timeline, root-cause, and reviewer steps before human
approval.

![Incident analysis ready for human approval](docs/screenshots/workflows/incident/03-root-cause-review-and-human-approval.png)

#### 4. Final writer output

The Writer produces the approved post-incident report.

![Final incident report](docs/screenshots/workflows/incident/04-final-output.png)

</details>

### Prompt and Agent Configuration

Prompt versions are managed independently from runtime settings, allowing each
agent to use a selected prompt, model, token budget, timeout, retry policy, and
review threshold. The interface also flags prompt names that appear inconsistent
with the assigned agent role so configuration drift is visible before future runs.

<details>
<summary><strong>View prompt and agent configuration</strong></summary>

#### Prompt version library

![Prompt version library](docs/screenshots/configuration/01-prompt-versions-overview.png)

#### Workflow-specific prompt assignments

![Workflow-specific prompt assignments](docs/screenshots/configuration/02-prompt-version-details.png)

#### Workflow-grouped agent settings

![Workflow-grouped agent settings](docs/screenshots/configuration/03-agent-settings.png)

</details>

### Baseline Comparison

The same source input can be processed as a single-agent baseline and compared
with the reviewed multi-agent workflow.

<details>
<summary><strong>Run and compare a sales baseline</strong></summary>

#### 1. Create the baseline run

![Creating a sales baseline run](docs/screenshots/comparison/01-create-sales-baseline.png)

#### 2. Run the baseline

![Running the sales baseline](docs/screenshots/comparison/02-run-sales-baseline.png)

#### 3. Inspect its final output

![Final sales baseline output](docs/screenshots/comparison/03-sales-baseline-final-output.png)

#### 4. Start a comparison

![Selecting Compare this run](docs/screenshots/comparison/04-compare-this-run.png)

#### 5. Compare baseline and multi-agent results

Review output quality, factual support, cost, and latency side by side.

![Sales baseline compared with the multi-agent workflow](docs/screenshots/comparison/05-baseline-vs-multi-agent.png)

</details>

## Evaluation Methodology

Each evaluation case stores:

- Source input text.
- Expected facts.
- Expected risks.
- Expected recommendations.
- Expected feedback themes for customer feedback workflows.
- Expected timeline events for incident workflows.
- Notes that define unsupported-claim guardrails.

The evaluation system compares baseline and multi-agent outputs using:

- Factual accuracy.
- Unsupported claim rate.
- Completeness.
- Human approval rate.
- Average retries.
- Average cost.
- Average latency.
- Router accuracy and confidence.

Deterministic checks complement LLM judging by verifying expected numeric facts,
feedback themes, incident timeline timestamps/events, and unsupported generated
numbers.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL 16 |
| LLM integration | OpenAI client behind a local abstraction |
| JavaScript package manager | pnpm workspaces |
| Python package manager | uv |
| Validation | pytest, Ruff, TypeScript, Node smoke tests |

## Project Structure

```text
apps/
  api/          FastAPI backend, models, routers, services, tests
  web/          Next.js frontend, dashboard routes, API client
packages/
  shared/       Shared TypeScript package
docs/           Project specs, phase plan, progress tracker
docker/         Docker support
scripts/        Utility scripts
```

## Quick Start With Docker

> [!IMPORTANT]
> Docker Compose is configured for local development only. It binds services to
> loopback and uses local credentials. Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
> before exposing any service to the internet.

```bash
git clone https://github.com/christiankfoury/agentops-workflow-platform.git
cd agentops-workflow-platform
cp .env.example .env
make up
```

Services:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API health: `http://localhost:8000/health`

## Local Development

Install dependencies:

```bash
pnpm install
cd apps/api
uv sync
cd ../..
```

Start the API:

```bash
cd apps/api
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Start the web app:

```bash
pnpm --dir apps/web dev --hostname 127.0.0.1 --port 3000
```

If the web app runs outside Docker, set the API URL when needed:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 pnpm --dir apps/web dev
```

## Production AI Platform Telemetry

AgentOps can optionally send safe, best-effort LLM usage telemetry to the
Production AI Platform. Telemetry is disabled by default, and AgentOps workflows
continue normally if the platform is unavailable.

Local placeholder configuration:

```env
AGENTOPS_TELEMETRY_ENABLED=false
AGENTOPS_TELEMETRY_ENDPOINT=http://localhost:8000/v1/usage/llm-events
AGENTOPS_TELEMETRY_API_KEY=agentops-local-placeholder-key-not-a-secret
AGENTOPS_TELEMETRY_TIMEOUT_SECONDS=2
AGENTOPS_TELEMETRY_MAX_METADATA_BYTES=2048
AGENTOPS_TELEMETRY_REDACT_CONTENT=true
```

When AgentOps runs in Docker and Production AI Platform runs on the host, use:

```env
AGENTOPS_TELEMETRY_ENDPOINT=http://host.docker.internal:8000/v1/usage/llm-events
```

The telemetry client only sends operational metadata such as workflow IDs, agent
step IDs, agent name/type, token counts, latency, cost estimate, status, retry
count, and safe error categories. It does not send prompts, generated outputs,
workflow input/output JSON, tool arguments, tool results, provider payloads, API
keys, or OpenAI credentials.

Structured JSON model calls are represented as `agent_step` events with
`response_type=structured_json`; writer and baseline text calls use
`response_type=text`. Workflow summary events are aggregate-only terminal status
events. They intentionally omit token and cost fields so Production AI Platform
does not double-count spend already reported by per-step events.

Send one local smoke event after the Production AI Platform API is running and
seeded with the AgentOps placeholder key:

```powershell
cd apps/api
uv run python ../../scripts/send_platform_telemetry_smoke.py
```

For a browser proof in Production AI Platform, keep the platform dashboard on
`http://localhost:3000` and run AgentOps on non-conflicting ports such as
`API_PORT=8001` and `WEB_PORT=3001`. The safest repeatable demo path is the
platform-owned synthetic sender:

```powershell
cd /path/to/production-ai-platform
uv run python scripts/send_agentops_browser_demo_event.py
```

Then open `http://localhost:3000`, filter **Source App** to `agentops`, and
inspect the resulting `Agent Step` telemetry row. Use a real local AgentOps
workflow only when provider credentials and any OpenAI quota usage are
intentional.

## Demo Mode

Seed polished demo data from the UI:

1. Open `http://localhost:3000/demo`.
2. Run one workflow demo or the full evaluation demo.
3. Open `/workflow-comparison` or `/evaluation` to inspect results.

For a scripted reviewer/remediation demo path, follow
[`docs/demo-walkthrough.md`](docs/demo-walkthrough.md).

Seed from the API CLI:

```bash
cd apps/api
uv run python -m src.seed_demo_dataset
```

Demo seeding is idempotent. Re-running it refreshes the demo records instead of
duplicating demo runs and results.

## Validation

Backend tests:

```bash
cd apps/api
uv run pytest
```

Production AI Platform telemetry mocked receiver check:

```bash
cd apps/api
uv run python ../../scripts/test_phase45_mocked_platform_receiver.py
```

Docker Compose config check with placeholder env values:

```bash
docker compose --env-file .env.example config
```

Backend lint:

```bash
cd apps/api
uv run ruff check src tests
```

Frontend typecheck:

```bash
pnpm --dir apps/web typecheck
```

Frontend smoke tests:

```bash
pnpm --dir apps/web test:smoke
```

Dependency audits:

```bash
pnpm audit --audit-level moderate
cd apps/api
uv run pip-audit
```

## Security

Please report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
Never commit provider keys or production credentials. The included environment
examples contain local placeholders only.

## Why This Project Matters

The app is intentionally not a chatbot. It treats AI output as a stateful business
workflow that can be inspected, retried, approved, measured, and compared against
a baseline. That is the practical engineering story: better control and higher
trustworthiness in exchange for extra cost and latency.

## Lessons Learned

- Agent quality is easier to improve when every intermediate output is stored and
  reviewable.
- Reviewer agents are most useful when paired with deterministic checks for facts,
  numbers, themes, and timeline events.
- Human approval is not a fallback bolted onto the end; it needs structured edit
  support so the writer agent can use the corrected analysis.
- Baseline comparison keeps the project honest by showing both quality improvement
  and the cost/latency tradeoff.
- Demo data matters for portfolio work because dashboards need meaningful records
  before a reviewer or recruiter can understand the system.

## Roadmap

Phase 46 through Phase 65 is complete. Completed work includes human edit flows,
feedback-loop metrics, agent performance, workflow comparison, exports,
uploads/parsers, deterministic evaluation checks, failure exploration,
improvement tracking, demo dataset seeding, demo mode, testing, security/input
safety, and portfolio UI polish.

Current user-directed refinement focuses on:

- Reviewing whether each workflow algorithm and agent handoff still makes sense.
- Improving prompt/settings clarity and future-run impact messaging.
- Tightening demo storytelling for recruiter review.
- Polishing workflow run, approval, comparison, cost, and prompt UI.
- Improving CSS consistency, responsive behavior, empty states, and visual hierarchy.
