# Prompts

Prompt versioning makes agent behavior inspectable and measurable. Prompt
templates are stored in `prompt_versions` and can be activated through the API or
UI.

## Data Model

`prompt_versions` fields:

- `id`
- `agent_type`
- `name`
- `version`
- `template`
- `is_active`
- `notes`
- `created_by_user_id`
- `created_at`

Agent steps can reference `prompt_version_id`, and evaluation results can store a
`prompt_version_summary_json` snapshot.

## Default Seeding

Default prompts are seeded by:

```bash
cd apps/api
uv run python -m src.seed_prompts
```

The seed service is `services/prompt_versions.py`.

## Runtime Resolution

At runtime, agents resolve prompt/model configuration through
`services/agent_settings.py`.

Resolution order:

1. Agent setting with explicit active prompt version.
2. Active prompt version for the agent type.
3. Default seeded prompt for the agent type.

Settings can also override model, temperature, max tokens, timeout, and retry
limits.

## Management UI

Prompt versions can be managed at:

- `/prompt-versions`
- `/prompt-versions/:id`

Agent settings can be managed at:

- `/settings`

## Prompt Comparison

Prompt-version performance is summarized by
`services/prompt_version_comparison.py`. It groups evaluation results by run mode
and prompt summary so changes can be compared against metrics like accuracy,
unsupported claim rate, completeness, cost, and latency.

## Prompt Design Rules

Prompts should:

- Require structured JSON when downstream agents depend on fields.
- Tell agents to use only source-supported claims.
- Preserve numbers exactly.
- Separate facts, risks, recommendations, and inferred claims.
- Include enough evidence for reviewer agents to validate outputs.
- Avoid asking writer agents to introduce new analysis.

## Adding a New Prompt

1. Create a prompt version through `/prompt-versions`.
2. Activate it directly or assign it through `/settings`.
3. Run evaluation cases for the affected workflow.
4. Compare prompt-version metrics before making the prompt the default.
