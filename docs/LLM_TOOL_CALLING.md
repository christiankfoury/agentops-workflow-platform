# Governed LLM tool calling

Phase 90 lets a durable `llm` node request published tool versions. Existing nodes
with no `config.tools` use the existing structured-output execution path.

## Configuration

Add bindings to the LLM node's existing prompt/model configuration:

```json
{
  "tools": {
    "lookup_issue": {
      "tool_id": "<published-tool-definition-uuid>",
      "version": 1,
      "adapter": "github",
      "description": "Read issues from the configured support repository"
    }
  },
  "max_tool_calls": 8,
  "max_provider_rounds": 6,
  "max_cost_usd": 1
}
```

Bindings accept up to eight function names. Publication pins the adapter policy
fingerprint; changing the server policy requires a new workflow version. Tools,
credentials and policies are resolved in the execution's organization. Descriptions
are part of the pinned graph, rather than mutable catalog descriptions. Unknown
model pricing is rejected at run acceptance when tools are enabled.

The worker rechecks the initiating user's current membership or service principal's
`workflow.start` scope before provider reservations and tool dispatch. Disablement,
role/scope revocation, cancellation and expired deadlines stop subsequent work.

## Exact approval for writes

Every side-effecting LLM binding requires `approval_node` pointing to an upstream
approval node. Its reviewed payload and completed output must exactly equal:

```json
{
  "node_id": "the_llm_node_id",
  "tool_id": "<published-tool-definition-uuid>",
  "version": 1,
  "arguments": {"title": "The exact reviewed action"}
}
```

Use a planning node, approval gate, then the tool-calling LLM node when the proposed
action is generated dynamically. Approval happens before this LLM conversation;
there is no implicit mid-conversation approval or automatic expansion of the action.
Different actions require their own gates/bindings. Approval expiry, source changes,
changed arguments and revoked reviewers deny execution. Rejection prevents reaching
the LLM node.

One approval authorizes one logical side effect per step. The ledger key uses the
approval identity for writes, so new provider call IDs or repeated requests cannot
multiply that action. Read calls use the retained provider call ID. Existing adapter
reconciliation and unknown-effect operator resolution apply unchanged.

## Conversation and limits

Provider batches are validated in full before any call in that batch executes.
Only declared functions are accepted; arguments must match their closed schemas.
Duplicate call IDs, duplicate JSON keys and forged credential/tenant fields are
rejected. Calls run sequentially through `ToolExecution`. The provider receives only
validated, redacted tool results as `tool` messages. Results are untrusted data and
cannot edit the tool list, credentials, approval, server policy or principal.

`llm_conversations` stores a bounded private checkpoint per logical step: original
messages, provider reservations/usage, pending call IDs and arguments, tool result
messages, and the validated final output. Provider responses commit before tool I/O;
effect receipts commit before continuation. A replacement worker reuses pending
calls and cached receipts. No provider/network call occurs under a database lock.
Conversation content is application data and should receive the same storage/access
protections as workflow inputs. Public attempt traces expose safe usage and tool
name/version/call ID/effect-key linkage, without the raw conversation. Attempt reads
also resolve the effect record ID and current status for direct ledger inspection.

Call, round, estimated-cost and total conversation-time limits survive retry and
worker replacement. Schema repair also consumes the round/cost/time budgets.
Maximums are 32 calls and 16 provider requests; defaults are 8 and 6. The conversation
time allowance is the first attempt's pinned LLM timeout, also bounded by each
attempt/run deadline. Checkpoints are capped at 1.5 MB before persistence.

Cost enforcement uses pinned model prices and a conservative input-byte/protocol
allowance plus the configured output-token cap before every request. Returned usage
replaces its reservation; a lost response retains an unconfirmed reservation and
unknown cost rather than reporting zero. This is an estimated application budget,
not a provider billing guarantee. Unknown pricing prevents acceptance. Traces retain
usage per original attempt even if a worker dies before normal attempt completion;
late returned usage can refresh a terminal business projection.

## Delivery and validation

Apply migration `f090_llm_conversations` before deploying API/workers. It adds a
tenant-owned table and immutable identity/retention guards; existing graphs and
effect records are unchanged. Downgrade refuses to discard populated conversations.

The implementation preserves the existing Chat Completions/model interface and
uses [OpenAI function-call messages](https://developers.openai.com/api/docs/guides/function-calling).
Function schemas use `strict: false` to preserve optional properties in existing
tool contracts; the backend independently validates every argument. SDK retries
are disabled so durable budgets own retries.

Automated validation uses provider fixtures and disposable PostgreSQL only. No
live API key, paid request, live integration action or deployment is evidence of
this phase. Any optional live check requires separately authorized credentials and
an appropriately scoped sandbox tool; side-effect approval remains mandatory.
