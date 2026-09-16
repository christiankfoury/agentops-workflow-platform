# HTTP REST tool

Phase 87 adds a schema-bound HTTP adapter to durable workers. Publication and
start validation check tenant-owned tool references, schemas, active credentials,
destination policy and upstream approvals. The in-process deterministic runner
cannot dispatch tools. No schema migration is required beyond Phase 86.

## Configure destinations

Set `HTTP_TOOL_DESTINATIONS` on API and workers to the same JSON object. Keys are
`<organization UUID>/<destination alias>`. The default `{}` denies every request.
Example operator configuration (replace the example host before use):

```json
{
  "00000000-0000-0000-0000-000000000001/orders": {
    "origin": "https://orders.example.com",
    "methods": ["GET", "POST"],
    "credential_alias": "orders-account",
    "credential_header": "Authorization",
    "idempotency_retention_seconds": 0,
    "max_request_bytes": 64000,
    "max_response_bytes": 64000,
    "max_redirects": 0
  }
}
```

Only server configuration defines origins, methods, private-network exceptions,
credential header placement, transport limits and provider guarantees. Workflow
authors select a destination alias, method and fixed encoded path:

```json
{"destination": "orders", "method": "POST", "path": "/v1/orders"}
```

A contract's `credential_ref` must refer to the destination's `credential_alias`
in that organization, or both must be absent. The worker resolves its value from
`TOOL_CREDENTIAL_VALUES`; see [credential delivery](TOOL_CONTRACTS.md#worker-credentials).
`Authorization` injects `Bearer <value>`; `X-API-Key` injects the value directly.
Credentials are limited to 4 KB, cannot contain control characters, and are never
provided as graph arguments. Custom request headers and cookies are unsupported.

HTTPS is required unless the operator explicitly sets `allow_plain_http: true`.
Non-public IP addresses also require explicit `allowed_private_cidrs`, such as
`["127.0.0.1/32"]` for a local fixture. Metadata, link-local, multicast, unspecified,
reserved and IPv6 transition destinations remain blocked. Every DNS answer is
checked; mixed allowed/disallowed answers fail closed. Each connection uses a
vetted numeric address while TLS verifies the original hostname. Proxy environment
variables do not affect transport. Limit worker network egress in deployment too.

## Schemas and result mapping

`GET` and `HEAD` encode scalar arguments as query parameters. Other supported
methods (`POST`, `PUT`, `PATCH`, `DELETE`) send arguments as a JSON body and require
`side_effecting: true`. Read methods require `side_effecting: false`; operators must
only configure services that honor those method semantics. Paths cannot select a
different origin or embed a query string. Request targets are capped at 8 KB, also
subject to the configured request limit.

Results have this shape, validated against the tool and graph output schemas:

```json
{"status": 200, "body": {"value": "example"}}
```

Successful responses must contain JSON (except `HEAD`/204, whose body is `{}`).
No response headers are returned. Content encoding is restricted to identity;
declared and streamed body sizes are bounded before JSON parsing. The shared
ledger additionally bounds JSON to 128 KB and 24 levels. Schema violations and
malformed/oversized responses become `tool_response_invalid`.

429 maps to `tool_rate_limit`; 408/425/5xx to `tool_unavailable`; other HTTP errors
to `tool_denied`. Raw provider bodies and exception messages are not errors or
diagnostics. Tool and node retry policies both bound attempts; the transport performs
no hidden retries. The node policy controls scheduled backoff. Configure nonzero
backoff for rate-limited services.

The timeout covers DNS, connection, TLS, request and streamed response. At most
eight DNS lookups may remain outstanding per process; a late DNS result cannot
initiate I/O. A deadline timer and cooperative abort close tracked sockets. Worker
ownership, cancellation and run/attempt deadlines also fence committed results.

Redirects default to disabled. An operator may allow up to three redirects for
reads within the exact same origin. Each hop rechecks DNS and limits. Writes,
cross-origin redirects, fragments and missing/invalid locations are rejected.
Credentials cannot be forwarded to a redirected origin.

## Authorize writes

A write node pins `tool_id`, numbered `version`, `adapter: "http"`, and an upstream
`approval_node`. The approval payload/output must be this exact envelope:

```json
{
  "node_id": "create_order",
  "tool_id": "00000000-0000-0000-0000-000000000002",
  "version": 1,
  "arguments": {"value": "example"}
}
```

Use the approval's output arguments as the tool's input bindings. The gate uses
the existing structured review, hash-bound human decision, edit and expiry APIs.
An edit requires a new approval. Immediately before reservation and dispatch, the
worker verifies the completed gate, approved snapshot, exact envelope, source hash,
workflow version, current iteration and expiry. With identity enabled, the deciding
human must still have an active reviewer/admin membership; high-severity overrides
still require admin. One consumer node cannot reuse another node's approval.

Approvals authorize the immutable contract's destination alias and method/path.
Changing a contract requires a new numbered version and a newly published workflow.
Publication pins the server policy fingerprint into each tool node. Changing that
policy blocks existing versions at start and dispatch, even after approval and
before any effect reservation. Republish to bind the new policy and obtain fresh
approval. The policy also forms part of each effect fingerprint. Disable the
destination/reference to stop future dispatches; this cannot recall an accepted request.

## Ambiguous effects and provider guarantees

Writes with lost responses, timeouts, malformed receipts or HTTP failures remain
`unknown` when acceptance cannot be disproved. A local ledger alone does not imply
exactly-once remote execution. Without a provider guarantee, automatic attempts do
not repeat that write; operators must inspect remote evidence and resolve it.

Set `idempotency_retention_seconds` above zero **only** when the configured service
guarantees the same receipt for the same `Idempotency-Key`, payload and account
through that entire retention interval, including concurrent requests and failures.
The adapter uses the ledger's stable key. Recovery requires enough remaining
retention for the whole request budget, measured from PostgreSQL time plus local
elapsed time rather than the worker's wall clock. It replays with that key and records the
confirmed receipt as reconciled. Expired retention remains unknown. Credential
rotation or server policy changes cannot redirect recovery to another account or
service. This guarantee is operator configuration, never workflow/model input.

## Validation and limits

Run the local HTTP/TLS fixtures and PostgreSQL worker tests with:

```powershell
uv run --directory apps/api pytest tests/test_http_tool.py tests/test_http_tool_runtime.py tests/test_tool_effects.py -q
```

Set `WORKFLOW_TEST_DATABASE_URL` to a disposable PostgreSQL database for worker
tests. The fixtures check DNS pinning, metadata/redirect/header isolation, deadlines,
abort, schemas, approvals, tenant policy, revocation, bounded retries, lost responses
and crash recovery. They do not prove a real third party's idempotency promise or a
hosted deployment. Delivery results are recorded in [phase progress](phase-progress.md).

Design references: [Python HTTP client](https://docs.python.org/3.12/library/http.client.html),
[TLS hostname verification](https://docs.python.org/3.12/library/ssl.html), and
[OWASP SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
