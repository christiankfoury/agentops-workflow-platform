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
uv run python -m src.run_evaluations --workflow-type sales_report --mode baseline
uv run python -m src.run_evaluations --workflow-type sales_report --mode multi_agent
```

Seed deterministic demo evaluation results:

```bash
cd apps/api
uv run python -m src.seed_demo_dataset
```

## Dashboards and Exports

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
