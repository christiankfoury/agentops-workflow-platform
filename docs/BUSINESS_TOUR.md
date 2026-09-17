# Business workflow screenshots

These retained screenshots show the earlier business workflow interface and seeded
portfolio data. New durable business runs execute on workers and link to the
[generic debugger](WORKFLOW_DEBUGGER.md); old per-agent buttons are not their control
path. The screenshots are not evidence of a new live provider or Kubernetes run.


### Operations Dashboard

![AgentOps operations dashboard](screenshots/dashboard.png)

### Multi-Agent Workflow Walkthroughs

Each workflow follows the same controlled pattern: structured intake, specialized
analysis, reviewer validation, human approval, and final report generation.

<details open>
<summary><strong>Sales report workflow</strong></summary>

#### 1. Create the workflow

Configure the sales input, run mode, workflow type, and optional routing notes.

![Creating a sales report workflow](screenshots/workflows/sales/01-create-workflow.png)

#### 2. Run the Sales Analyst

Start the specialist agent that extracts sales performance, risks, and
evidence-backed recommendations.

![Running the Sales Analyst](screenshots/workflows/sales/02-run-analyst.png)

#### 3. Review and human approval

Inspect the completed analyst and reviewer steps before approving or editing the
analysis.

![Sales analysis ready for human approval](screenshots/workflows/sales/03-review-and-human-approval.png)

#### 4. Final writer output

The Writer converts the approved analysis into the final executive report.

![Final sales report](screenshots/workflows/sales/04-final-output.png)

</details>

<details open>
<summary><strong>Customer feedback workflow</strong></summary>

#### 1. Create the workflow

Provide customer reviews, tickets, survey comments, or an uploaded CSV file.

![Creating a customer feedback workflow](screenshots/workflows/customer-feedback/01-create-workflow.png)

#### 2. Run the Feedback Classifier

Start the classifier that organizes the source feedback into useful categories.

![Running the Feedback Classifier](screenshots/workflows/customer-feedback/02-run-classifier.png)

#### 3. Generate insights, review, and approve

Inspect the completed classifier, insight, and reviewer steps before human
approval.

![Customer feedback insights ready for human approval](screenshots/workflows/customer-feedback/03-insight-review-and-human-approval.png)

#### 4. Final writer output

The Writer turns the approved findings into a product insights report.

![Final customer feedback report](screenshots/workflows/customer-feedback/04-final-output.png)

</details>

<details open>
<summary><strong>Incident log workflow</strong></summary>

#### 1. Create the workflow

Provide timestamped operational events and any incident context.

![Creating an incident log workflow](screenshots/workflows/incident/01-create-workflow.png)

#### 2. Run the Timeline Agent

Start the specialist that reconstructs the incident sequence from the source log.

![Running the Timeline Agent](screenshots/workflows/incident/02-run-timeline.png)

#### 3. Analyze root cause, review, and approve

Inspect the completed timeline, root-cause, and reviewer steps before human
approval.

![Incident analysis ready for human approval](screenshots/workflows/incident/03-root-cause-review-and-human-approval.png)

#### 4. Final writer output

The Writer produces the approved post-incident report.

![Final incident report](screenshots/workflows/incident/04-final-output.png)

</details>

### Prompt and Agent Configuration

Prompt versions are managed independently from runtime settings, allowing each
agent to use a selected prompt, model, token budget, timeout, retry policy, and
review threshold. The interface also flags prompt names that appear inconsistent
with the assigned agent role so configuration drift is visible before future runs.

<details open>
<summary><strong>View prompt and agent configuration</strong></summary>

#### Prompt version library

![Prompt version library](screenshots/configuration/01-prompt-versions-overview.png)

#### Workflow-specific prompt assignments

![Workflow-specific prompt assignments](screenshots/configuration/02-prompt-version-details.png)

#### Workflow-grouped agent settings

![Workflow-grouped agent settings](screenshots/configuration/03-agent-settings.png)

</details>

### Baseline Comparison

The same source input can be processed as a single-agent baseline and compared
with the reviewed multi-agent workflow.

<details open>
<summary><strong>Run and compare a sales baseline</strong></summary>

#### 1. Create the baseline run

![Creating a sales baseline run](screenshots/New%20folder/01-create-sales-baseline.png)

#### 2. Run the baseline

![Running the sales baseline](screenshots/New%20folder/02-run-sales-baseline.png)

#### 3. Inspect its final output

![Final sales baseline output](screenshots/New%20folder/03-sales-baseline-final-output.png)

#### 4. Start a comparison

![Selecting Compare this run](screenshots/New%20folder/04-compare-this-run.png)

#### 5. Compare baseline and multi-agent results

Review output quality, factual support, cost, and latency side by side.

![Sales baseline compared with the multi-agent workflow](screenshots/New%20folder/05-baseline-vs-multi-agent.png)

</details>
