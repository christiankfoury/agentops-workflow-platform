# LLM execution and quality revisions

Phase 82 adds the `llm` primitive to durable workers. Legacy business endpoints
remain available; their template migration follows in Phases 83–85.

## Configuration and publication

Each LLM node references an immutable published prompt version and declares its
model, token limit, optional temperature and node timeout. Publication already
snapshots prompt text and graph schemas. Start acceptance saves an immutable
`WorkflowExecution.runtime_config` snapshot before enqueueing work. Workers,
retries and resumed approvals never resolve mutable settings again.

`config.use_agent_settings` defaults to false. When enabled, acceptance resolves
the existing runtime settings for the referenced prompt's agent type, including
model, temperature, token limit and reviewer threshold. The explicitly referenced
prompt remains pinned even if the agent's active-prompt pointer changes. The
effective request timeout cannot exceed the node timeout. Settings outside the
generic graph's bounds reject acceptance. New settings affect later starts;
new prompt references require a new workflow publication.
The settings snapshot also preserves absent settings: a concurrently created
setting cannot change later nodes in the same acceptance transaction.

Known model pricing rates are copied from the existing estimate table at start.
Unknown models retain `null` estimated cost rather than borrowing another model's
price. These are configured estimates, not provider billing reconciliation.

## Execution, retries and accounting

The executor uses the existing `LLMClient` structured-output abstraction. Input
is JSON containing `input` and `revision_context`; the published prompt supplies
the system instruction. It validates returned data against the pinned schema.
`config.max_schema_repairs` defaults to one and is bounded from zero to two.
Repairs share the same attempt deadline and preserve every returned response's
usage. Invalid JSON and invalid reviewer fields can enter this bounded repair
path. Explicit refusal or truncation ends with a typed failure.

SDK retries are disabled (`max_retries=0`); transient failures retry only through
the node's durable `retry` policy. Configure retryable error codes such as
`provider_connection`, `provider_rate_limit`, `provider_unavailable` and
`attempt_timeout` deliberately. Permanent provider rejection, refusal, incomplete
output, invalid usage and schema failures cannot be made retryable by a graph.
The SDK's retry and timeout options are documented in the
[official Python SDK reference](https://developers.openai.com/api/reference/python#retries).

Attempts and execution events retain prompt/model identity, each response's
tokens, schema repair count, total observed tokens, latency and estimated cost.
`provider_requests` counts attempted requests; `usage_complete=false` identifies
requests whose usage was not returned. Costs sum observed usage only. Abrupt
worker death or cancellation before a live result commits can leave unknown
remote usage; retained abandoned/cancelled attempts do not invent token counts.

Cancellation closes the attempt's dedicated client where supported and checks
the abort signal before requests, between repairs and after I/O. The queue's live
claim/attempt fence still rejects late results. Closing a client does not undo a
request the provider has already accepted.

## Bounded quality policy

`quality_revision` declares `entry_node`, `review_node`, `nodes`, `max_revisions`
(one to five) and `approval_node`. The declared region is a closed entry-to-review
subgraph ending in an LLM reviewer. Its computation may include code, transforms,
conditions and parallel regions. Waits, approvals and external effects stay
outside the repeated region. The reviewer must lead to its human approval
directly or through one routing condition with an explicit edge to that approval.
The quality approval cannot also accept an unrelated route that bypasses its review.

Reviewer output includes `approved`, `quality_score`, structured `issues` and
`retry_recommended`. Acceptance requires approval, the pinned score threshold and
no high/critical issue. A failed review with a retry recommendation advances the
quality iteration within its bound. Each repeated node gets a new logical step;
infrastructure attempt numbers restart for that step. Prefix and independent
sibling outputs/waits remain intact. Prior steps, attempts and review feedback
remain immutable history. Downstream routing is reevaluated for the new iteration.

When revisions are exhausted or the reviewer requests human intervention, the
declared approval is selected even if an inconsistent reviewer `approved` flag
would otherwise bypass it. Human retry requests use the remaining quality budget
and the approval's separate human-retry limit. They preserve reviewer feedback,
human feedback and the edited candidate. Superseded approval IDs cannot authorize
a later iteration. High-severity override permissions remain enforced.

Writer nodes bind to the approval's output to consume human edits. An automatic
approved path may use an explicit coalescing binding to the reviewed analysis.
Quality policies require durable workers; arbitrary graph cycles remain forbidden.

## Rollout and evidence

Stop old workers, apply `f082_execution_config`, then restart upgraded workers.
Existing deterministic executions keep empty configuration snapshots. ORM and
PostgreSQL guards prevent changing a saved snapshot; downgrade refuses to discard
LLM history. No destructive legacy backfill is performed.

Tests use provider fixtures and disposable PostgreSQL: schema/JSON repair and
accounting, SDK retry coordination, typed failures, cancellation/timeouts,
paused-run prompt/settings publication, immutable migration history, bounded
revisions, human edits, separate attempt/iteration budgets and parallel sibling
preservation. These checks make no paid provider calls and are not live provider
or hosted deployment evidence.
