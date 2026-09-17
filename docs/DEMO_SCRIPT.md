# Five-minute platform demo script

**Audience:** an engineering hiring manager or teammate assessing the system.
**Deliverable:** recording script, not a generated or recorded video.
**Editorial target:** 5:00, including UI holds; rehearse before recording.
The eight spoken sections contain **563 words**: about 241 seconds at 140 words
per minute, leaving about 59 seconds for holds. Each section fits its own window
at that rate. This is a word-count estimate, not a recorded-duration claim.
Use the [walkthrough](demo-walkthrough.md) to prepare data and reproduce every
action. The [evidence index](PLATFORM_EVIDENCE.md) links implementation and tests.

Keep these labels visible throughout the relevant shots:

- **Local runtime + synthetic model responses** for builder, approval and sales.
- **Assigned demo metrics — not live model results** for comparison/evaluation.
- **Measured local experiment** for benchmark, fault and Kubernetes evidence.
- **Hosted / paid-provider acceptance not performed** on the closing slide.

## 1. Problem and product — 0:00–0:25

**Screen:** `/workflow-definitions`, then the prepared status-check draft.
**Setup:** walkthrough sections 1–2; fixture manifest supplies its definition ID.
**Hold:** show the four-node graph before moving the pointer.

**Say:**

> A generated answer is only one part of an automation. We also need to know
> which workflow version ran, what a person approved, and what happens when a
> worker or remote request fails. AgentOps makes those decisions durable and
> inspectable. The original sales, feedback and incident workflows now run as
> templates on this shared platform.

## 2. Author and publish — 0:25–1:05

**Screen:** draft editor, then **Validation and versions**.
**Action:** inspect `route`, `gate`, `read_status` and `skip`; show the primitive
selector. Choose **Validate saved draft**, then **Publish saved draft**.
**Setup:** walkthrough section 2; this is a fresh draft, not a business template.

**Say:**

> A draft combines typed steps: model calls, code, tools, conditions, approvals,
> transforms, parallel branches and delays. This example chooses a route, pauses
> for review, then reads a local HTTP fixture. Validation checks the graph and
> available execution capabilities. Publishing creates an immutable version.
> Every accepted run pins that version, so a later draft edit cannot silently
> change work already in progress. Tools also pin their configured contract.

## 3. Start, branch and approve — 1:05–1:45

**Screen:** release page manual-start input `{"check":true}`, followed by its
generic debugger and **Approvals** section.
**Action:** **Start selected version**, run the fixture worker, inspect the
waiting gate. Show the terminal API decision from walkthrough section 3, then
return to the trace. Optional alternate take uses `{"check":false}` and shows
the skipped review route, with no HTTP request.
**Do not invent a generic approval button:** this decision uses the API; the
business approval form appears in scene 6.

**Say:**

> Starting commits the run and its first durable job before returning acceptance.
> The input selects the review branch. The approval wait releases worker capacity
> and retains the exact payload under review. Here I submit that decision through
> the API and inspect it in the debugger. This tool performs a local read, not an
> external write. Real writes additionally need the tool's approval and effect
> safeguards; an approval is never a substitute for tenant permission.

## 4. Retry and inspect — 1:45–2:20

**Screen:** `read_status` step's attempts, then **Events**, **Tools**, and pinned
graph edge decisions. Use **Refresh now** after draining due work.
**Action:** first fixture response is HTTP 503; show failed attempt, persisted
retry due time or retained timestamps, then the successful second attempt after
five seconds. The worker may finish both attempts in one drain command.
**Setup:** walkthrough section 3; do not probe the fixture before the first run.

**Say:**

> The fixture deliberately fails its first request. The engine records that
> attempt, schedules bounded backoff, and later succeeds. The logical step and
> its separate attempts remain visible. For worker loss, leases and fencing
> prevent an expired owner from committing a late result. Execution is at least
> once. An uncertain remote write stays unknown unless the adapter or an
> authorized operator has enough evidence to reconcile it.

## 5. Permissions — 2:20–2:40

**Screen:** `/account` in the local preview, beside the
[identity contract](IDENTITY.md) and [authenticated cluster evidence](KUBERNETES_RESULTS.md).
**Action:** explicitly label local prototype identity. Point to recorded
unauthenticated rejection and verified session checks; do not simulate a tenant
switch or claim this development session proves isolation.

**Say:**

> Production identity comes from verified sign-in and organization membership.
> Authors, operators, reviewers and administrators have different permissions,
> enforced again on the server. This preview uses development identity. The
> separate deployed fixture verified authenticated access; tenant-isolation and
> revoked-permission tests are linked in the evidence index.

## 6. Sales review, human edit and final report — 2:40–3:40

**Screen:** manifest's sales run and approval; **Edit approved analysis**,
**Recommendations**, **Save Edits**, new pending approval, **Approve**, final output.
**Action:** replace the recommendation with
`Assign renewal review to account owners.` Save, follow the replacement approval,
approve, then drain the fixture worker. Show that exact sentence in final output.
**Setup:** walkthrough section 4. Leave model-response labels visible; zero
fixture usage and a configured model name are not a live provider measurement.

**Say:**

> The same runtime supports the original business flow: analyst, reviewer, human
> approval and writer. The reviewer output and source stay available while a
> person decides. Even a favorable review does not bypass the published
> template's approval gate. I change the recommendation, save a replacement
> approval, and approve that revised payload. The writer receives the approved
> analysis, and the final report contains the edit. These model responses are
> synthetic; the version, queue, approval and output transitions are actual local
> execution. Historical business reports remain readable alongside generic traces.

## 7. Evaluation and improvement tradeoffs — 3:40–4:25

**Screen:** `/workflow-comparison`, search **[Demo] Remediation impact showcase**,
open details and **Remediation impact**. Then show `/evaluation` and `/costs`.
**Setup:** walkthrough section 5; use seeded completed comparisons. Do not click
**Create corrected run** during this credential-free take.
**Overlay:** the case-specific table in [Evaluation](EVALUATION.md), not the
base-case constants or overall dashboard averages.

**Say:**

> Comparison keeps quality, cost and latency together. These demo values are
> assigned illustrations, not measured model improvement. In this showcase the
> corrected report removes a reviewer issue, yet its unsupported-claim score
> worsens from zero to point three three. Assigned cost falls from zero point
> zero zero two zero five dollars to zero point zero zero one nine eight, and
> latency from ten point two three to seven point nine three seconds. That is a
> mixed outcome. Deterministic coverage checks are useful proxies, so I inspect
> the actual output and reviewer explanation as well.

## 8. Measured operations and close — 4:25–5:00

**Screen:** `/operations`, then result tables and retained logs from
[benchmark](BENCHMARK_RESULTS.md), [faults](RELIABILITY_RESULTS.md) and
[Kubernetes operations](KUBERNETES_OPERATIONS_RESULTS.md).
**Setup:** walkthrough section 6. These are recorded experiments, not new runs
performed during the video. Show the single-node and controlled-sink limits.

**Say:**

> Separate runtime experiments completed ten thousand workflows with no lost
> accepted work or duplicate sink effects. Forty-five fault cases accounted for
> every accepted run, including expected failures and unknown outcomes. In the
> local Kubernetes operations suite, twenty-one workflows produced twenty-one
> effects across rollout, worker loss and recovery. Backup and fresh-database
> restore matched retained history. Hosted deployment and paid-provider
> acceptance remain unperformed. The result is a workflow system whose behavior,
> tradeoffs and limits can be inspected and reproduced.

## Recording and review checklist

- Prepare and rehearse before capture; setup, migrations and dependency installs
  are outside the five-minute cut. Use edits between verified states rather than
  claiming an asynchronous result was instantaneous.
- Capture at readable desktop size. Zoom into the relevant panel; keep request
  bodies, approval hashes and attempt numbers readable. Never show secrets or a
  real account's private data. Fixtures use repository-owned synthetic inputs.
- Link the walkthrough and evidence index in the video description. Preserve
  labels in cropped shots; avoid an unlabeled metric montage.
- Narration timing is an editorial estimate, not a measured finished video.
  The phase ledger records the browser walkthrough and word-count check.
- This deliverable does not claim a recorded video, hosted deployment, live
  model benchmark, universal exactly-once effects or production certification.

## Rehearsal evidence

The [Phase 104 record](evidence/phase104/summary.json) contains scene timing,
source hashes, browser observations and reconciled run IDs. Its linked
[raw records](evidence/phase104/walkthrough-records.json.gz) retain both condition
paths, failed/successful HTTP attempts, and the superseded/approved sales payloads.
The [phase ledger](phase-progress.md) records tests, commits, CI and review.
