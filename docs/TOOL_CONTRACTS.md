# Tool contracts and effect history

Phase 86 provides the shared tool catalog, credential references and effect ledger.
Production adapters and graph dispatch arrive in Phases 87–89. The default adapter
registry is empty; recognizing a `tool` graph node does not make it executable.
The tests register fixture adapters and exercise real PostgreSQL worker claims.

## Catalog and authorization

- Administrators create a definition and its first immutable contract with
  `POST /tools`, then publish another numbered contract with
  `POST /tools/{definition_id}/versions` and `expected_version`.
- `GET /tools` and `GET /tools/{definition_id}/versions` expose tenant-scoped
  metadata. `GET /tools/versions/{version_id}` retains historical contracts.
- A contract includes adapter identity, closed input/output schemas, timeout,
  bounded retry policy, side-effect declaration, options and an optional
  `credential_ref`. The worker verifies the node's pinned definition/number and
  adapter. The registered adapter determines whether the operation has effects;
  authors cannot bypass that policy by labeling a write as a read.
- `PATCH /tools/{definition_id}` toggles availability. Disabling a definition
  prevents new dispatches, including reservations accepted before disablement.
- Version and effect identities are protected by ORM checks and PostgreSQL
  triggers. There is no delete API. Tenant-qualified foreign keys prevent
  cross-organization credential and execution references.

## Worker credentials

An administrator creates a reference with `POST /tools/credentials`, providing a
display name and a non-secret `source_alias`. The response ID can be placed in a
tool contract. `PATCH /tools/credentials/{id}` enables or revokes that reference.
The alias is immutable; create a new reference when changing its intended account.

Configure `TOOL_CREDENTIAL_VALUES` only on workers. It is a JSON object whose keys
are `<organization UUID>/<source_alias>` and whose values are credential strings.
The development Compose configuration passes this variable to the worker only;
its default is `{}`. Populate it through the deployment's secret delivery mechanism,
never through graph input or a committed environment file. The API handles metadata
and does not resolve these values.

Resolution requires an active owned worker claim and running attempt, a matching
pinned tool contract, an active organization/tool/reference, and an unexpired
execution/attempt deadline. The worker rechecks availability immediately before
dispatch and audits credential use without recording the value. Revocation stops
future dispatch; it cannot undo a remote request already accepted.

Each effect retains a private, salted PBKDF2 credential fingerprint after its first
dispatch. A changed credential cannot silently replay the same logical effect under
another account. This fingerprint and worker reservation tokens are excluded from
API reads. A rotation during an uncertain effect requires explicit review; a new
credential reference/version can be used for future work.

Known credential fields and URL user information are rejected in contract options.
Tool validation responses omit submitted values. Request/result records redact
sensitive field names; returned results also redact the resolved credential value
before output-schema validation. Provider exception text is never persisted or
returned. Adapters must keep secrets out of diagnostics and avoid returning encoded
or transformed credentials. Redaction is not permission to embed secrets in inputs.

## Effect identity and recovery

The effect key comes from the persisted logical step and call ID. It is stable
across attempts and worker restarts. New branches/iterations have distinct step
identities and therefore distinct effects. The request fingerprint also binds the
immutable tool version and canonical arguments. Changed arguments conflict with
an existing logical call.

| State | Meaning |
| --- | --- |
| `pending` | Reserved; the `dispatched` marker distinguishes the I/O boundary. |
| `succeeded` | A validated, redacted provider result was recorded. |
| `failed` | No uncertain write remains from this attempt; retry still requires policy and budget. |
| `unknown` | A write may have been accepted; blind replay is forbidden. |
| `reconciled` | An adapter or authorized administrator recorded the verified outcome. |

Concurrent requests serialize on the execution/effect record. Only one reservation
can dispatch; duplicates reuse a confirmed result or report an in-progress call.
The dispatch marker commits before external I/O. No database lock spans provider
I/O. A crash before that marker is safe to resume. A crash after it is conservatively
uncertain, even if the provider may not have received the request.

The worker also marks abandoned dispatches unknown after lease loss, including
when the workflow's recovery budget is exhausted. Confirmed late receipts can still
be retained as effect evidence after workflow cancellation. They do not complete
the cancelled workflow, and an aborted caller does not receive a successful output.

Server-registered adapters declare one recovery contract:

- **None:** an uncertain write requires operator resolution.
- **Idempotent:** the provider must enforce the supplied stable effect key for the
  same action/account and the entire supported recovery interval. A local key alone
  is insufficient.
- **Reconcile:** a lookup must return a confirmed result, prove that no completed
  or pending effect exists, or return unknown. Only proven absence permits another
  write. The lookup outcome is retained before another invocation.

Adapters must enforce transport size/time limits, honor cooperative cancellation,
classify definite rejection separately from uncertain acceptance, and keep retries
within the contract. The coordinator bounds JSON payloads to 128 KB, checks types,
tracks elapsed time and supplies the remaining timeout after reconciliation.
It cannot forcibly interrupt arbitrary server code; concrete adapters own their
transport cancellation and timeout implementation.

Administrators inspect `GET /tools/executions/{id}` and use
`POST /tools/executions/{id}/resolve` only after checking remote evidence. The body
contains `succeeded`, a schema-valid `result` for success, and an `evidence` summary.
Resolution fences late replies, is audited and immutable, and does not automatically
resume a terminal workflow. A failed resolution prevents replay of that logical call.
Never declare absence just because a request timed out.

## Migration and validation

Apply `alembic upgrade head` before deploying updated workers. Migration
`f086_tool_contracts` adds four tenant-owned tables and immutable-history triggers;
existing business and execution rows remain unchanged. Downgrade is supported only
while the new tables are empty. Disable definitions/references to stop future use
while retaining history.

Fixture tests cover version publication races, role/tenant checks, credential
revocation and rotation, duplicate claims, independent iterations, crashes around
dispatch, provider idempotency, reconciliation, operator resolution, cancellation,
deadline checks, redaction and migration retention. They are not live HTTP,
PostgreSQL data-source or GitHub integration evidence. See [phase progress](phase-progress.md).
