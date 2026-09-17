# Workflow draft builder

Open **Workflow builder → New definition**. Operators and administrators can
edit drafts; viewers and reviewers can inspect them. All requests use the current
organization and the API rechecks authority. Archived definitions are read-only.

## First deterministic workflow

1. Name the draft. The starter `message` transform emits `{ "text": "Ready" }`.
2. Choose **delay** under **New step type**, then **Add node**. Set **Delay seconds**
   to `0`; leave **Wake at** empty.
3. Connect `message` to the new delay node using **From node**, **To node**, and
   **Add connection**. Leave the outcome label empty for this linear connection.
4. Save. Open the saved draft link or return through the definition list, select
   the delay in **Inspect node**, and verify its duration and connection.

This example uses no model or external tool. Draft saving does not execute,
publish, or change existing published versions.

## Editing

The diagram shows connection direction; node buttons and **Inspect node** select
the form. Every operation has a keyboard-accessible control. IDs stay stable.
Removing a node also removes incident edges; remaining bindings are retained and
reported as missing references so their meaning is not silently changed.

The eight forms expose LLM, code, tool, condition, approval, transform, parallel,
and delay settings. Select registered tools and prompt versions from the catalog;
unavailable current IDs remain visible. Tool versions must be specified explicitly.
Schemas, bindings, retry policy, condition cases, LLM tool aliases, branches and
quality revision settings use labeled JSON editors. These preserve malformed text
across node selection and prevent saving until the JSON parses.

Examples:

```json
{"result":{"op":"literal","value":"Ready"}}
```

```json
{"result":{"op":"ref","ref":{"source":"node","node_id":"message","path":["text"]}}}
```

Conditions use cases such as `[{"label":"yes","when":{"op":"literal","value":true}}]`.
Use matching outcome labels on their connections. Parallel forks need at least two
named branch entries and a join node; joins specify their fork and wait for every
selected branch. Delays accept exactly one duration or an ISO wake time including
a UTC offset. Quality revision settings name an entry/review pair, member nodes,
one to five revisions and optional approval/score/severity rules.

## Saving and recovery

Local diagnostics identify node/field paths and connection problems. They are
authoring hints, not a guarantee of executable behavior. Incomplete configurations
can be saved for later repair. Unsupported structural drafts use a raw Graph JSON
repair view and retain their original data. Published-runtime validation is a
separate delivery gate.

**Edit graph JSON** also opens the complete graph from a supported draft, so extra
or unsupported fields can be repaired without an API client. Switching editors
keeps parsed values synchronized; repair malformed text before switching back.

Saves include the loaded revision. A conflict retains all local edits and never
overwrites newer work automatically. Use **Open saved draft in a new tab** to
compare before manually reapplying changes. Network and permission errors also
retain edits. Changing organization blocks submission from an older editor; return
to the original organization before saving. Editing controls are frozen during a
save so its response cannot replace newer local changes. The browser warns before
unloading a dirty draft; save before using application navigation links.

No migration is required. This interface uses existing definition draft APIs.

## Validation, publication, and manual starts

Open **Validation and versions** after saving. Validation reports the exact saved
revision and separates graph errors from unavailable runtime capabilities. An
administrator can publish only a runnable revision through this screen; its web
server action validates capability and the API rejects concurrent draft edits.
Direct API publication can retain recognized but unavailable handlers; every
start independently rechecks runtime support. Publishing creates an immutable version. Existing runs
retain their original version, even while a later draft is edited or published.

Select a published version to inspect its capabilities or compare it with another
version on the same history page. History is paginated in groups of 50. Older
pages select a visible historical version; verify that selection before starting.
Diff previews are limited to 120,000 characters. Archived versions cannot start.

Manual input must be a JSON object matching the workflow schema. The first start
freezes the selected version, input and request key. **Retry same start** submits
that identical request and returns the same run after an uncertain network result
or an accepted start. Keep the page open until the result is resolved; this key is
retained in page memory, not across reloads. **Prepare a separate run** explicitly
creates a new logical request on its next start. Publication errors retain the
loaded revision; reload after an uncertain publish to see whether it succeeded.
Accepted starts link to the [run debugger](WORKFLOW_DEBUGGER.md), which preserves
the pinned graph and exposes logical steps, attempts and durable trace details.

## Webhook and cron triggers

Open **Triggers** to list webhook or cron configurations. Administrators can
create, edit, enable and pause triggers. Supply the definition UUID and a
provisioned service principal UUID in the same organization with `workflow.start`
permission. Choose the current published version or an explicit pinned version.
Enablement rechecks the service principal and runnable target. Revision conflicts
retain edits; compare using **Open saved trigger in a new tab** before reloading.

Webhook forms accept only an operations-configured signing **alias**, using masked
inputs. Do not enter the actual key. Saved aliases and keys are not returned to
the browser. Rotation changes that reference with a bounded previous-key grace
period. Save configuration edits before rotating. Blank payload mapping forwards
the signed JSON payload; an object maps fields to input references.

Cron schedules accept five fields and an IANA time zone. They forbid overlapping
runs and coalesce missed ticks. Repeated local times use their first occurrence;
invalid local times are skipped. Configuration changes reset the next tick;
pause/resume preserves it. Delivery/fire histories show decisions, selected
versions, runs and error codes, with 50-record pagination and an explicit reload.
History failure does not discard configuration edits. These screens do not create
service principals or provision signing keys.
