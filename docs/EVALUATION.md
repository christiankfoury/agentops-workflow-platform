# Evaluation

The evaluation system measures whether multi-agent workflows improve output
quality compared with a single-agent baseline.

## Dataset

Evaluation cases are seeded from `services/evaluation_cases.py`.

The current dataset contains:

- 10 sales report cases.
- 10 customer feedback cases.
- 10 incident log cases.

Each case stores:

- `workflow_type`
- `title`
- `input_text`
- `expected_facts_json`
- `expected_risks_json`
- `expected_recommendations_json`
- `expected_themes_json` for customer feedback
- `expected_timeline_json` for incidents
- `expected_output_notes`

## Result Model

`evaluation_results` stores one scored run:

- Evaluation case ID.
- Workflow run ID.
- Run mode: `baseline` or `multi_agent`.
- Prompt version summary.
- Factual accuracy.
- Unsupported claim rate.
- Completeness score.
- Router detected type, confidence, and correctness.
- Human approval fields.
- Retry count.
- Cost.
- Latency.
- Judge notes.
- Error message.

## Metrics

The aggregate metrics service is `services/evaluation_metrics.py`.

Tracked metrics:

- Factual accuracy.
- Unsupported claim rate.
- Completeness.
- Router accuracy.
- Average router confidence.
- Human approval rate.
- Average cost.
- Average latency.
- Average retries.

## Deterministic Checks

Deterministic checks increase credibility by verifying objective expectations
without relying only on an LLM judge.

Current checks include:

- Expected numeric facts.
- Expected customer feedback themes.
- Expected incident timeline timestamps and events.
- Unsupported generated numbers.

The runner writes deterministic notes into `judge_notes` so dashboards and exports
can show why a score changed.

## Running Evaluations

Seed evaluation cases:

```bash
cd apps/api
uv run python -m src.seed_evaluation_cases
```

Run evaluations:

```bash
cd apps/api
uv run python -m src.run_evaluations --mode baseline
uv run python -m src.run_evaluations --mode multi_agent
```

Seed deterministic demo evaluation results:

```bash
cd apps/api
uv run python -m src.seed_demo_dataset
```

## Dashboards and Exports

### Durable execution and approval policy

These CLI commands run all seeded workflow types in local development mode.
Identity-enabled deployments use authenticated administrator API actions.
With the default business-template flags enabled, the CLI, comparison promotion
and correction actions accept pending results and enqueue durable work. Run
`uv run python -m src.worker` against the same database to execute it. Provider
credentials belong on workers; a queued API request needs no provider key.
Acceptance persists the result, run and job atomically. Terminal checkpoints score
the committed final output with the existing deterministic checks. Cancelled or
failed runs produce failed results. Historical completed results remain readable.

Evaluation execution requires administrator permission. Multi-agent evaluations
preserve the existing automatic approval policy: the initiating administrator is
recorded, and a worker rechecks their current membership before each decision.
Approval feedback explicitly states that no individual human review occurred.
If permission is revoked, the evaluation pauses for an authorized manual decision;
restoring membership does not silently retry a blocked approval. Approval policy
and run/case bindings are immutable. Do not interpret `human_approved=true` alone
as evidence of an individual review; consult approval feedback and judge notes.

Where an active router prompt exists, its diagnostic step is pinned in the
evaluation graph. Its returned usage is included in observed costs and latency.
This corrects the legacy runner's untracked router cost; comparisons across the
migration should account for that change. Without a configured router prompt,
router metrics remain absent. No additional provider call is made to score results.

Baseline and multi-agent evaluations reuse the same stored source. Promotion
queues a counterpart against the original input; repeated concurrent promotion
reuses its pending result. Promotion from a baseline derives expected items from
the completed counterpart's approved structured output and then rescores the
baseline. Corrected runs retain case input text and add reviewer guidance clearly
marked as guidance rather than source facts. Pending action responses link to run
progress; completed comparisons remain on the existing comparison dashboard.

Migration `f085_durable_evaluations` adds requester and approval-policy metadata
without rewriting historical results. Downgrade refuses pending automatic
evaluations; drain or cancel them first. Business-template feature flags select
the retained legacy runner for future evaluations during backout. Keep workers
running for accepted durable jobs. Demo seeds install templates but retain their
explicitly synthetic historical results; they are not live execution evidence.

Evaluation results are exposed through:

- `/evaluation-results`
- `/evaluation-results/summary`
- `/evaluation-results/comparisons`
- `/evaluation-results/export/json`
- `/evaluation-results/export/csv`
- `/evaluation-results/export/markdown`

Frontend routes:

- `/evaluation`
- `/workflow-comparison`
- `/failures`
- `/improvements`

## Interpreting Results

The expected story is not that multi-agent workflows are cheaper or faster.
The expected story is that they trade cost and latency for better factual
accuracy, fewer unsupported claims, stronger completeness, and better auditability.
