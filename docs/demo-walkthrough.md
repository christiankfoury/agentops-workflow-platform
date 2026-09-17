# Reproducible demo walkthrough

Use this setup with the [five-minute script](DEMO_SCRIPT.md). This is a local,
credential-free rehearsal: synthetic model responses and assigned comparison
metrics, real database/queue/approval transitions, and a loopback HTTP read.
It is not a live-provider evaluation or a production identity demonstration.
The [example helper](../apps/api/examples/demo_fixture.py) is not part of API
startup and never falls back to an external model client.

## 1. Prepare an isolated fixture

Prerequisites: locked Python/web dependencies, a local PostgreSQL server and a
current web build. Follow [native setup](DEPLOYMENT.md) first. Create a **new**
database named `phase104_demo_<unique_suffix>` using your local database tools.
Do not reuse a business database, drop an existing database, or stop another
project to free a port. The helper refuses nonlocal databases, identity-enabled
mode, non-development mode, URL query parameters, existing runs and an existing
manifest. Connection query options are rejected because they can override the
host/database named in the URL; use the simple explicit connection form below.

From the repository root in PowerShell, configure each API/worker terminal:

```powershell
# Substitute the connection to the new local database; do not commit credentials.
$env:DATABASE_URL='postgresql://LOCAL_USER:LOCAL_PASSWORD@127.0.0.1:5432/phase104_demo_rehearsal'
$env:ENVIRONMENT='development'
$env:IDENTITY_ENABLED='false'
$env:API_AUTH_ENABLED='false'
$env:OPENAI_API_KEY=''
$env:HTTP_TOOL_DESTINATIONS='{"00000000-0000-0000-0000-000000000001/demo":{"origin":"http://127.0.0.1:8144","methods":["GET"],"allow_plain_http":true,"allowed_private_cidrs":["127.0.0.1/32"]}}'
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m examples.demo_fixture seed --manifest ../../.local/demo/manifest.json
```

Choose an unused manifest path for each fresh database. Commands below use that
same path. The seed creates 32 cases, 65 historical runs/results, 99 agent steps,
a new unpublished generic draft, and one additional sales run paused for review.
The manifest prints their IDs and the database name, not the connection secret.
Do not run a normal provider-backed worker against this fixture database.

In separate terminals, keep the following foreground processes running:

```powershell
# API terminal, with the same database and destination environment:
uv run --directory apps/api uvicorn src.main:app --host 127.0.0.1 --port 8008

# HTTP fixture terminal; first /health GET is 503, later GETs are 200:
uv run --directory apps/api python -m examples.demo_fixture serve

# Web terminal, after a current build is available:
$env:ENVIRONMENT='development'
$env:IDENTITY_ENABLED='false'
$env:API_INTERNAL_URL='http://127.0.0.1:8008'
$env:NEXT_PUBLIC_API_URL='http://127.0.0.1:8008'
$env:APP_ORIGIN='http://127.0.0.1:3109'
pnpm --dir apps/web start --hostname 127.0.0.1 --port 3109
```

The helper uses fixed loopback port 8144 and only serves `/health`; it performs
no writes. Do not probe this endpoint before the first tool run, or the probe
will consume its intentional failure. API health on port 8008 is independent.
If a required port is occupied, use another isolated environment or change the
fixture and configured destination together before starting; do not kill its owner.
For a clean checkout, build once with `pnpm --dir apps/web build`; do not rebuild
shared assets underneath another active preview.

The example worker runs only when explicitly drained:

```powershell
uv run --directory apps/api python -m examples.demo_fixture drain --manifest ../../.local/demo/manifest.json
```

It refuses unrelated active work and a manifest/database mismatch. Its model
adapter recognizes only the fixture's analyst, reviewer and writer schemas.
Model usage is synthetic zero; the configured model name is not evidence of a
provider call. The writer constructs its output from the actual approved analysis.
No schema migration beyond the existing application head is introduced.

## 2. Builder, version and admission

Open `http://127.0.0.1:3109/workflow-definitions/<definition_id>` using the manifest.

1. Inspect the condition, approval, HTTP tool and skip transform. Show the eight
   available primitive types. The draft is separate from installed business templates.
2. Open **Validation and versions**. Validate the saved draft, then publish the
   validated revision. Observe the published version and source revision.
3. Use manual-start input `{"check":true}` and **Start selected version**. Follow
   the returned debugger link and retain the execution ID for the next commands.
4. Drain the fixture worker. Refresh the trace: the condition selects `review`,
   the gate waits for approval, and the tool has not run. Inspect the pinned graph
   and its **Edge decisions and branch state** disclosure.

Publication is immutable; edits require a new revision/version. Do not modify
business templates just to demonstrate the builder. A repeated identical start
key reuses a run, while a changed payload with that key conflicts; the existing
[start tests](../apps/api/tests/test_execution_starts.py) verify that contract.

## 3. Generic approval, retry and debugger

The generic debugger displays approvals but does not offer a decision form.
For this local read fixture, show the actual API decision in a terminal:

```powershell
$demoExecutionId='EXECUTION_ID_FROM_THE_START'
$demoApprovals=Invoke-RestMethod "http://127.0.0.1:8008/execution-approvals?execution_id=$demoExecutionId"
$demoPending=$demoApprovals | Where-Object status -eq 'pending'
if (@($demoPending).Count -ne 1) { throw 'Expected exactly one pending approval' }
$demoDecision=@{action='approve'; expected_payload_hash=$demoPending.payload_hash} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8008/execution-approvals/$($demoPending.id)/decide" -ContentType 'application/json' -Body $demoDecision
uv run --directory apps/api python -m examples.demo_fixture drain --manifest ../../.local/demo/manifest.json
```

Inspect the tool step: the first request returns 503, the failed attempt is retained,
and retry due time is persisted. The drain command can remain running through
backoff and complete the second attempt itself. Observe while it runs, or inspect
the retained attempt timestamps afterward; do not promise a paused terminal state.
If due work remains after it exits, drain again after five seconds. The second
request succeeds. **Refresh now**, select the tool node and open its
**Attempts for ...** control. Show both attempts, then **Events**, **Tools** and
**Approvals**. This is a read-only tool demonstration; no external write is implied.
The [recorded Kubernetes experiment](KUBERNETES_OPERATIONS_RESULTS.md) separately
covers approved writes and sink reconciliation.

For the alternate branch, start the same published version with `{"check":false}`
and a fresh UI start intent. Drain and inspect `skip` completed, with no approval
or HTTP attempt for that execution. Do not reuse the prior run ID as a new take.
To rehearse the initial 503 again, restart only this walkthrough's fixture server
and start a fresh run. Preserve the old run's history.

## 4. Original sales workflow and human edit

Open `/workflow-runs/<sales_run_id>`, then
`/human-approvals/<sales_approval_id>` from the manifest.

1. Show the analyst output, reviewer result, source and pending human gate.
2. Expand **Edit approved analysis**. Replace **Recommendations** with
   `Assign renewal review to account owners.` and add feedback explaining the edit.
3. Choose **Save Edits**. Follow the replacement approval; the old decision payload
   remains retained. Inspect the edited analysis and choose **Approve** there.
4. Drain the fixture worker. Open the run's **Final Output** link and verify the
   exact edited recommendation in the report. Show the agent-step trace and approval.

A favorable model review still waits for human approval in this published template.
These are actual local state transitions with explicitly synthetic responses,
not an observed quality gain or paid execution. The focused
[sales migration tests](../apps/api/tests/test_sales_template.py) also verify that
stale approvals cannot approve a superseded edit and writers receive approved input.

## 5. Comparison, evaluation and the improvement story

The fresh seed already populates the dashboards. For an ordinary separate local
demo dataset, `/demo` offers **Load Full Demo**; it seeds assigned results, not live
model evaluations. Do not reseed this rehearsal while filming.

On `/workflow-comparison`, search and open these named cases:

- **[Demo] Reviewer issue correction path:** `Needs review`, reviewer evidence
  explaining why declining pipeline coverage is a risk, and **Create corrected run**.
  Show the action without invoking it: a new correction uses the real model path.
- **[Demo] Remediation impact showcase:** previous and corrected output links,
  reviewer issue change and the **Remediation impact** panel. `vs baseline` and
  `vs previous run` use different comparison denominators. The assigned unsupported
  score worsens from 0.00 to 0.33 despite removal of the reviewer issue.

Visit `/evaluation`, `/costs`, `/agent-performance`, `/failures` and `/improvements`
as optional B-roll. Use the exact case-specific [evaluation table](EVALUATION.md)
for the narration; base-case constants are not overall averages. Deterministic
keyword/numeric scoring is a proxy with documented limits. The live fixture's
synthetic zero usage must not be blended into a claimed provider cost result.
For a customer feedback example, supply raw comments only; expected-theme answer
keys belong in evaluation cases, not workflow input.

## 6. Permissions, recovery and measured operations

Show `/account` and `/operations`, explicitly labeled development identity/local
fixture. The production identity flow and tenant boundaries are documented and
linked to tests in [Identity](IDENTITY.md) and [the evidence index](PLATFORM_EVIDENCE.md).
Use the recorded synthetic-OIDC sign-in and unauthenticated rejection from
[Kubernetes acceptance](KUBERNETES_RESULTS.md); do not claim the local prototype
session is an authenticated multi-tenant test.

Show the published result tables/logs for:

- [Benchmark](BENCHMARK_RESULTS.md): 10,000 completed workflows, no lost accepted
  work or duplicate sink effects in that deterministic service-level experiment.
- [Faults](RELIABILITY_RESULTS.md): 45 cases across three repetitions; expected
  terminal failures/cancellations and deliberately unknown remote outcomes retained.
- [Kubernetes operations](KUBERNETES_OPERATIONS_RESULTS.md): 21 completed workflows,
  21 effects from 23 requests, stale-owner fencing, persistent history, backup/restore
  and compatible metadata-only rollback in a single-node kind cluster.

Their linked runbooks reproduce those experiments independently; do not launch
fault injection during this five-minute walkthrough. Hosted deployment, real
identity-provider/account acceptance and paid-model comparison remain unperformed.
Leave all datasets and original evidence intact. Stop only the three rehearsal
processes you started when finished; deletion is not part of this walkthrough.

## Recorded rehearsal

[Phase 104 evidence](evidence/phase104/summary.json) records the completed browser
walkthrough and API reconciliation. Both condition paths and the sales fixture
completed; the HTTP retry gap was 5.134355 seconds. The sales edit produced a
superseding approval and appeared in the final report. The 65 seeded evaluation results
remain explicitly assigned examples, separate from these three executions.
