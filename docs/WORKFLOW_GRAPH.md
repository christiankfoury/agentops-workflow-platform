# Workflow graph format

Phase 70 introduces `WorkflowGraph` schema version 1 and pure validation. Phase 71
adds definition/version persistence and APIs, described below. Existing business
workflows now use [published templates](BUSINESS_TEMPLATES.md) by default, with
retained legacy compatibility. Schema recognition covers
`llm`, `code`, `tool`, `condition`, `approval`, `transform`, `parallel` and `delay`;
`ensure_executable` rejects every type absent from the supplied executor registry.
Quality revision execution has its own capability gate.

## Structure and limits

Graphs have stable node IDs, one entry node, directed edges, input/output schemas,
node input bindings and graph output bindings. All nodes must be reachable. Cycles
are forbidden. A condition has ordered boolean cases and exactly one default
edge. Only conditions and parallel forks have labeled or multiple outgoing edges.
An ordinary node with multiple incoming edges declares `merge: exclusive`, and
its incoming routes must be mutually exclusive. Parallel forks name distinct
branch entries and a matching `all_selected` join; branches cannot overlap, end
early or accept external edges. Joins assemble explicitly named branch outputs;
the runtime returns deterministic sorted keys as described in [parallel execution](DURABLE_QUEUE.md).

Limits: 100 nodes, 300 edges, 256 routing paths per node, eight cases/branches,
100 fields per object, 16 path segments, eight nested expression operations,
32 payload nesting levels, and 256 KiB of JSON including serialized defaults.
Retries allow 1–10 attempts, bounded backoff/jitter and explicit error codes.
Attempt timeouts are at most one hour, overall deadlines at most 30 days,
delays at most seven days, and quality revisions at most five.

Quality revision metadata identifies a closed entry-to-review subgraph. Only its
entry may receive external edges and only its review node may exit. This reserves
a bounded revision contract without admitting cyclic edges. The
[LLM runtime](LLM_EXECUTION.md) executes those bounded revisions.

## Data and expressions

The closed JSON Schema subset supports object, array, string, integer, number,
boolean and null. One type may be unioned with null. Objects explicitly declare
properties/required fields and forbid extra fields; arrays require item schemas.
Runtime data validation never coerces strings or booleans to numbers. Integers
are compatible with number schemas; non-finite numbers are rejected.

Bindings map destination fields to literals, input references, preceding node
output references, or constrained operations. Supported operations are equality,
ordering, boolean logic, existence, add/subtract/multiply, concatenation and
coalesce. No source code, `eval`, dynamic imports or arbitrary function calls are
accepted. Code nodes identify registered handlers by name and version.

Missing and null are distinct. A missing field, array index or unselected producer
uses the reference's `on_missing` policy: `error` (default), `null`, or an explicit
typed `default`. Existing null values remain null; `coalesce` handles null.
References may point to a producer on a conditional route, so consumers must
choose a missing policy appropriate to that route. A required destination field
must have a binding; a nullable binding cannot feed a non-null destination.

Prompt/tool IDs and contract versions are schema references. Phase 71 publication
checks prompt ownership/existence and retains source links and content snapshots.
Tool resolution and handler availability are enforced at registry/execution
boundaries. HTTP, PostgreSQL and GitHub adapters are implemented; publication
pins their tenant-owned contracts and policies. See [tool contracts](TOOL_CONTRACTS.md).

## Validation evidence

`apps/api/tests/test_workflow_graph.py` covers all primitives and serialization,
condition routes, typed missing/null/default behavior, invalid graph/reference/
expression/policy shapes, graph size/depth, closed revisions and executor gates.
These are deterministic schema fixtures, not live workflow execution evidence.

## Definitions and publications

`/workflow-definitions` supports paginated listing and creation. Each definition
owns its current name, description and editable JSON draft. Incomplete drafts may
be saved within payload limits; `POST /{id}/validate` returns graph errors and a
separate runtime capability result. Operators/admins draft; all tenant members
may read and validate. Admins publish and archive. Service identities also need
the matching explicit `workflow.draft`, `workflow.publish` or `read` scope.

`PUT /{id}/draft` and `POST /{id}/publish` require `expected_revision`. A row lock
and fresh revision comparison serialize concurrent edits/publications. Each
successful edit, publish or archive increments the draft revision; stale requests
return 409. Publication validates and snapshots the graph, name and description,
records a canonical graph hash and monotonic per-definition version number, and
atomically moves the published pointer with its authenticated audit event.

`GET /{id}/versions` and `GET /{id}/versions/{version_id}` retain history.
`GET /{id}/versions/{version_id}/diff?compare_to={other_version_id}` compares
metadata, graph and pinned prompts. Published graph/content and prompt links
cannot be updated or deleted through ORM or migrated database writes. Prompt
activation remains allowed; a published prompt's template, name, type and version
are frozen, and its foreign-key link prevents deletion. Snapshots retain the
publication-time template and explicit model/configuration values.
Default prompt reseeding also preserves existing templates and notes; changed
defaults require a new prompt version.

`POST /{id}/archive` archives a definition; the version-specific `/archive` path
archives one version. Both require the current revision and admin permission.
Archival clears an affected published pointer and blocks future starts, retaining
history for later version-pinned runs. There is no deletion or unarchive API.
Migration rollback refuses to discard existing definitions; retain/export history
and use a forward migration when data exists.

Published versions may contain recognized but unavailable primitives.
`GET /{id}/versions/{version_id}/capabilities` exposes that distinction, and the
start-boundary helper rejects unavailable executors. The builder's server action
requires runnable validation before publication, while direct API publication
can retain a recognized graph with an unavailable handler. Tool references and
policies are validated/bound on publication; runtime settings are pinned at start.
All eight primitives have implementations, but configured references and handler
versions must still be available. See [execution](EXECUTION_RECORDS.md).
