# Workflow graph format

Phase 70 introduces `WorkflowGraph` schema version 1 and pure validation. It does
not add graph execution, publication, persistence or an API. Existing business
workflows continue through their existing services. Schema recognition covers
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
early or accept external edges. Branch declaration order is the output order
contract for the later executor.

Limits: 100 nodes, 300 edges, 256 routing paths per node, eight cases/branches,
100 fields per object, 16 path segments, eight nested expression operations,
32 payload nesting levels, and 256 KiB of JSON including serialized defaults.
Retries allow 1–10 attempts, bounded backoff/jitter and explicit error codes.
Attempt timeouts are at most one hour, overall deadlines at most 30 days,
delays at most seven days, and quality revisions at most five.

Quality revision metadata identifies a closed entry-to-review subgraph. Only its
entry may receive external edges and only its review node may exit. This reserves
a bounded revision contract without admitting cyclic edges or executing retries.

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

Prompt/tool IDs and contract versions are schema references here; tenant ownership,
reference existence and handler availability are enforced at later publication
and execution boundaries. Tool adapter recognition initially includes HTTP;
additional adapter contracts arrive with their integration phases.

## Validation evidence

`apps/api/tests/test_workflow_graph.py` covers all primitives and serialization,
condition routes, typed missing/null/default behavior, invalid graph/reference/
expression/policy shapes, graph size/depth, closed revisions and executor gates.
These are deterministic schema fixtures, not live workflow execution evidence.
