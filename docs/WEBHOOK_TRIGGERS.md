# Webhook triggers

Phase 91 accepts signed JSON events into the same durable start service used by
manual runs. A successful `202` acknowledges a persisted run and queue job; it does
not mean the workflow has finished. Delivery performs no provider or tool calls.

## Configure

Apply migration `f091_webhook_triggers`. An administrator creates a trigger with
`POST /webhook-triggers`; listing/detail and delivery history require `read`.
Configuration uses the existing organization's service principal with operator
role and `workflow.start` scope. The service account, principal and organization
must remain active, including in local mode with identity authentication disabled.

```json
{
  "name": "Incoming order",
  "definition_id": "<workflow definition UUID>",
  "version_policy": "published",
  "service_principal_id": "<service principal UUID>",
  "secret_alias": "orders-v1",
  "input_mapping": {
    "value": {"source": "input", "path": ["order", "amount"]}
  }
}
```

Use `pinned` with `version_id` to select an explicit published version. Otherwise
the current published pointer is resolved atomically at acceptance. Missing or
archived versions reject new events. Input mapping uses the graph's input-reference
path/default rules; omit it to pass the entire object, or use `{}` for empty input.
The resolved input must satisfy the workflow's input schema.

Provide `WEBHOOK_SECRET_VALUES` to the API as a JSON object mapping
`"<organization UUID>/<alias>"` to a signing secret of at least 32 UTF-8 bytes.
Use a cryptographically random secret and secure environment injection. No secret
is supplied in API configuration or stored in trigger/delivery/audit tables.
Aliases are write-only API fields. Empty configuration fails closed. Workers do
not require these signing secrets. Provision principals using the existing identity
administration process; caller-supplied tenant or principal headers never choose
the public delivery's authority.

`PUT /webhook-triggers/{id}` replaces configuration and requires
`expected_revision`. It retains the signing alias. Set `enabled:false` to pause;
retained configuration and delivery identities cannot be deleted or reassigned.
An administrator can disable a trigger whose key or service access has been revoked.

## Send an event

`POST /webhooks/{trigger UUID}` accepts `Content-Type: application/json` and exactly
one of each header:

- `X-AgentOps-Timestamp`: canonical decimal Unix seconds.
- `X-AgentOps-Event-ID`: 1–128 ASCII letters, digits, `.`, `_`, `:`, or `-`.
- `X-AgentOps-Signature`: `sha256=` followed by lowercase HMAC-SHA256 hex.

Sign these exact bytes, with no final newline after the body:

```python
message = f"{trigger_id}\n{timestamp}\n{event_id}\n".encode("utf-8") + raw_body
signature = "sha256=" + hmac.new(secret, message, hashlib.sha256).hexdigest()
```

Use the canonical lowercase UUID returned by configuration. Requests must be within
the configured freshness window (default 300 seconds, range 30–600), including
future timestamps. The default payload limit is 65,536 bytes; configurable limits
are 1,024–262,144 bytes with a hard streaming cap of 262,144. Payloads must be JSON
objects with no duplicate keys or nonfinite numbers, bounded depth, and bounded
mapped size. Public paths share the existing per-client API rate-limit bucket.

## Retry, rotation, and history

Retry with the same event ID and **identical body bytes**, using a fresh timestamp
and signature. Concurrent repeats start one run. Accepted repeats return its original
execution/version IDs even after publication, mapping, or version archival changes.
Changing whitespace also changes the payload fingerprint and returns `409`.
Current enablement, signature and principal permissions are checked on every retry.

Signed, authorized input/start rejections retain a receipt and audit outcome without
storing the rejected raw body. They can retry after configuration is repaired;
different bytes require a new event ID. Invalid signatures, revoked access and
disabled triggers create no delivery receipt. Unexpected transactional failures
roll back the receipt, run and job together. Retrying an accepted event never reruns
a failed workflow; use the workflow's explicit retry controls or a new event ID.

`POST /webhook-triggers/{id}/rotate-key` takes `expected_revision`, `secret_alias`
and `grace_seconds` (default 300, range 0–3600). Install the new alias on every API
replica before rotating. One previous key is accepted strictly before the grace
deadline; a second rotation replaces that previous key. Keep both configured during
the grace period: a missing required key fails closed with `503`. After expiry,
remove the previous secret from runtime configuration. Zero grace revokes it
immediately. Rotation and delivery serialize against the same trigger lock.

`GET /webhook-triggers/{id}/deliveries` exposes receipt status, attempts, fingerprint,
accepted configuration revision and execution/version/principal IDs. Per-delivery
`/{delivery_id}/events` gives chronological audit outcomes. Both lists are paginated
and tenant scoped. A principal with only `workflow.start` cannot read these histories
or execution input/output. Acknowledgements contain IDs and status only.

Validation uses disposable PostgreSQL and synthetic signing keys. No external webhook
provider, production credential, live model call, or deployment is claimed.
