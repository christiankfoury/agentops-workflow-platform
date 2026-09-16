# GitHub issue tool

Phase 89 adds `github` to the [tool catalog and effect ledger](TOOL_CONTRACTS.md).
It supports bounded issue reads and approved issue creation for configured
repositories. It uses the [HTTP transport](HTTP_TOOL.md) and its destination,
timeout, cancellation, payload and credential-header protections.

## Configuration and contracts

Set `GITHUB_TOOL_REPOSITORIES` on API and workers to a JSON object keyed by
`<organization UUID>/<repository alias>`. `{}` disables access. Example entry:

```json
{
  "owner": "example-org",
  "repo": "workflow-sandbox",
  "credential_alias": "github-sandbox",
  "actor_id": 123456,
  "operations": ["read_issues", "create_issue"],
  "origin": "https://api.github.com",
  "max_pages": 10,
  "max_response_bytes": 128000
}
```

`actor_id` is the numeric GitHub user or app-bot ID expected to author created
issues; it is required when creation is enabled. Creation also requires
`read_issues` in the allowlist so reconciliation reads are explicitly permitted.
Read-only configuration defaults
to `operations: ["read_issues"]` and can omit it. Production configuration targets
GitHub.com; alternate origins, explicit `allow_plain_http`, and
`allowed_private_cidrs` support local provider fixtures. GitHub Enterprise URL
mapping is not provided by this phase. Redirects and provider idempotency-key
replay are disabled. The adapter pins API version `2026-03-10` and protocol headers.

Create a catalog credential reference with the configured source alias. Put its
token in the worker-only `TOOL_CREDENTIAL_VALUES` entry
`<organization UUID>/github-sandbox`. Use a token scoped to the selected repository
with Issues read permission for listing, and Issues write for creation. Never put
a token in a workflow, tool options, issue text or server repository configuration.
Publication pins the repository policy; changing the repository, operations,
expected author or limits requires republication. Existing dispatch checks enforce
tenant ownership, enablement, credential revocation and credential identity.

Tool options are exactly:

```json
{"repository": "sandbox", "operation": "read_issues"}
```

Use `adapter: "github"` in the contract and graph config, and pin `tool_id` and
numbered `version`. For reads, set `side_effecting: false`. Arguments may contain
`state` (`open`, `closed`, `all`), `page` (1–20) and `per_page` (1–100); defaults are
`open`, 1 and 10. The configured maximum page also applies. The result is:

```json
{
  "issues": [{"number": 1, "title": "Example", "body": "Details", "state": "open", "url": "https://github.com/example-org/workflow-sandbox/issues/1"}],
  "next_page": null,
  "page_limit_reached": false
}
```

Declare these fields in a closed output schema; `next_page` is integer or null.
Pull requests returned by GitHub's issues endpoint are filtered out. Pagination
counts the provider's original page, so a page containing only pull requests can
still have a next page. `page_limit_reached` signals a full final allowed page.
Large provider pages fail the byte limit; reduce `per_page` rather than assuming
the adapter silently truncates issue text. Returned URLs are constructed from the
configured repository and validated issue number, never copied from provider text.

For creation, use `operation: "create_issue"`, `side_effecting: true`, and arguments
`title` (nonblank, at most 256 characters) and optional `body` (at most 20,000).
The output is `{"issue": <the issue object above>}`. Input schemas must declare
the desired supported fields. Repository, author, token, headers and correlation
marker cannot be overridden by arguments. Provider errors retain only safe codes.
The shared result validator/redactor protects persisted receipts and workflow output.

## Approval and uncertain outcomes

A create node needs an upstream human approval gate. The approved payload must
exactly equal `{"node_id": ..., "tool_id": ..., "version": ..., "arguments": ...}`,
as described in [HTTP governed actions](HTTP_TOOL.md). Approval is rechecked at
reservation and dispatch, including argument/source hashes, expiry, current human
reviewer authorization and pinned server policy. Reads do not require a write gate.

Before POST, the ledger commits a stable HMAC marker derived from its immutable
effect key and the resolved credential. The adapter appends it as an HTML comment
to the issue body. That marker survives worker crashes and remains in retained
effect metadata; the token itself does not. The returned creation receipt must
match the approved title/body and configured author. The hidden comment is removed
from the returned creation body. Caller-supplied marker comments are rejected.

GitHub creation is **not** assumed to support the local idempotency key. After a
timeout, lost response or worker crash, recovery lists recent issues in descending
creation order, at ten per page, up to the configured page limit. A single matching
receipt among the inspected pages must have the exact marker, title/body and
expected author. Missing, edited, forged or multiple matching receipts leave the
effect `unknown`. The adapter never reports proven absence and never repeats an
ambiguous POST. An authorized operator must use the existing resolution flow when
reconciliation cannot establish a receipt; resolution does not restart a terminal run.

The bounded listing can miss an older issue on a busy repository. That limitation
reduces automatic recovery availability, not the duplicate-create safeguard.
Successful receipts are retained and reused. Credential rotation blocks retry of
an existing effect; policy or approval changes cannot authorize replay implicitly.

## Rate limits and retry timing

429 and recognized primary/secondary-limit 403 responses map to `tool_rate_limit`.
The adapter honors numeric `Retry-After` and primary `X-RateLimit-Reset`, using the
provider's Date header to calculate a duration rather than the worker's wall clock.
A 60-second minimum applies; malformed timing falls back to an hour. Delays above
one day are denied rather than shortened. Other permission/authentication errors
are permanent; 5xx and uncertain transport failures follow the shared retry policy.

The effect outcome commits a database-based `retry_not_before` timestamp. The
workflow's queued retry uses the later of this timestamp and its own backoff/jitter.
Run deadlines still apply. Even an early recovery delivery checks retained effect
metadata before dispatching, so a crash between effect recording and workflow
checkpointing cannot bypass a recorded provider delay. Configure tool and node
retry policies consistently and include `tool_rate_limit` where retries are desired.

This guard applies to the logical effect, not a shared token-wide rate limiter.
Operators should avoid high concurrency against the same credential and provision
repository/token scopes accordingly. No new migration is required: marker and
backoff metadata use the existing retained JSON field.

## Validation and optional live check

Automatic tests use a local GitHub-like HTTP fixture and disposable PostgreSQL:

```powershell
uv run --directory apps/api pytest tests/test_github_tool.py tests/test_github_tool_runtime.py -q
```

They cover reads, pagination, approval, revocation, policy changes, schema/size
limits, errors, backoff, persisted markers, worker crashes, lost responses and
uncertain reconciliation. These are provider-contract fixtures, not a live GitHub
integration or deployment claim.

An optional live check requires an explicitly authorized **sandbox repository**,
a scoped token in the worker secret store, its author ID, and permission to create
a clearly labeled test issue (creation notifies repository subscribers). Configure
the sandbox policy, publish a read tool and verify a small page. Publish a create
tool with the exact human gate, approve a test title/body, and check that one issue
and its marker match the retained receipt. Keep the issue URL and workflow/effect
IDs as evidence. Do not simulate lost responses by blindly submitting another POST;
use fixture tests for that failure case. No live check was run for this phase.

Provider references: [GitHub issues API](https://docs.github.com/en/rest/issues/issues),
[repository issue listing](https://docs.github.com/en/rest/issues/issues#list-repository-issues),
and [rate-limit retry guidance](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#handle-rate-limit-errors-appropriately).
