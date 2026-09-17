# Evaluation

The evaluation system compares final outputs against stored expectations and
exposes baseline/multi-agent quality, cost and latency tradeoffs. It does not
assume that adding agents improves quality. No comparative live-provider quality
gain is established by the recorded platform delivery.

## Dataset

Evaluation cases are seeded from `services/evaluation_cases.py`.

The current dataset contains:

- 10 sales report cases.
- 10 customer feedback cases.
- 10 incident log cases.

Demo seeding adds two sales showcases: reviewer issue correction and remediation
impact. The full seed creates **32 cases, 65 runs/results and 99 AgentStep records**,
as checked by [demo tests](../apps/api/tests/test_demo_dataset.py). These are
synthetic historical records, not 65 observed provider executions.

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

The [scorer](../apps/api/src/services/evaluation_metrics.py) uses normalized phrase
and keyword overlap plus numeric checks. Its `factual_accuracy` field measures
captured expected facts divided by expected facts, not a semantic precision audit
of every generated claim. Completeness covers the combined expected items;
unsupported-claim rate uses heuristic support for split output claims. These
proxies can miss paraphrases or accept coincidental overlap. Empty denominators
use the service's defined zero behavior, not proof of correctness. There is no
additional LLM judge call in the current scoring path.

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

Compare the same input, pinned configuration and scoring method. Report failed,
pending and missing-usage records separately; aggregates use completed results
and available values. Inspect outputs and reviewer notes alongside the metrics.
More calls can add cost/latency without improving a deterministic score.

### Assigned demo values — not measured provider results

The [seed source](../apps/api/src/services/demo_dataset.py) assigns these values
to the 30 base-case pairs. They are not recomputed live quality measurements and
must not be presented as an observed uplift or provider bill.

| Assigned field | Baseline | Multi-agent |
| --- | ---: | ---: |
| Factual accuracy | 0.70 | 0.92 |
| Unsupported claim rate | 0.22 | 0.05 |
| Completeness | 0.64 | 0.88 |
| Cost, USD | 0.035 | 0.128 |
| Latency, seconds | 4.2 | 18.4 |

The separate **Remediation impact showcase** deliberately has mixed results:

| Assigned field | Baseline | Previous multi-agent | Corrected multi-agent |
| --- | ---: | ---: | ---: |
| Factual accuracy | 0.94 | 1.00 | 0.94 |
| Unsupported claim rate | 0.00 | 0.00 | 0.33 |
| Completeness | 0.91 | 1.00 | 0.96 |
| Cost, USD | 0.00034 | 0.00205 | 0.00198 |
| Latency, seconds | 2.42 | 10.23 | 7.93 |

Its corrected output removes a reviewer issue while the assigned unsupported
score worsens. Reviewer approval and deterministic coverage answer different
questions. These case-specific rows must not be mixed with base-case constants
or called overall dataset averages.

### Measured runtime evidence is a separate experiment

The [10,000-run benchmark](BENCHMARK_RESULTS.md),
[fault experiments](RELIABILITY_RESULTS.md) and
[Kubernetes operations](KUBERNETES_OPERATIONS_RESULTS.md) measure execution and
recovery using deterministic fixtures. They do not measure LLM output quality,
provider pricing or human review time. A live paired evaluation requires authorized
worker credentials, retained outputs/settings, declared sample selection and
scoring limitations; that experiment was not performed in this delivery.
