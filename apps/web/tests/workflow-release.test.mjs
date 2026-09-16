import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test, { afterEach } from "node:test";
import ts from "typescript";
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost" });
globalThis.window = dom.window; globalThis.document = dom.window.document; globalThis.HTMLElement = dom.window.HTMLElement;
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const require = createRequire(import.meta.url), React = require("react");
const { render, screen, fireEvent, cleanup, waitFor } = await import("@testing-library/react");
afterEach(cleanup);
function load(path, mocks = {}) {
  const source = readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const exports = {};
  new Function("require", "exports", compiled)(name => mocks[name] ?? (name === "next/cache" ? { revalidatePath: () => {} } : require(name)), exports);
  return exports;
}
const builder = load("lib/workflow-builder.ts"), model = load("lib/workflow-release.ts");
const fields = load("components/workflow-builder/fields.tsx");
const mocks = { "@/lib/workflow-builder": builder, "@/lib/workflow-release": model, "./fields": fields };
const { WorkflowRelease } = load("components/workflow-builder/release.tsx", mocks);
const { TriggerEditor } = load("components/workflow-builder/trigger.tsx", mocks);
const permissions = ["read", "workflow.publish", "workflow.start", "trigger.manage"];
const definition = { id: "definition", name: "Example", description: "", draft_graph: builder.starterGraph(), draft_revision: 3, archived: false, published_version_id: "v2" };
const versions = [2, 1].map(number => ({ id: `v${number}`, number, source_revision: number, name: "Example", created_at: "2026-09-16T12:00:00Z", archived_at: null, graph: builder.starterGraph() }));
const valid = { valid: true, executable: true, errors: [], runtime_errors: [], draft_revision: 3 };
const trigger = { id: "hook", name: "Webhook", definition_id: "definition", service_principal_id: "principal", version_policy: "published", version_id: null, enabled: false, revision: 2, input_mapping: null, freshness_seconds: 300, max_payload_bytes: 65536 };
function release(action, extra = {}) { return render(React.createElement(WorkflowRelease, { initial: definition, initialVersions: versions, scope: "org", permissions, action, ...extra })); }
function editor(action, extra = {}) { return render(React.createElement(TriggerEditor, { kind: "webhook", scope: "org", canManage: true, action, ...extra })); }
function click(name) { fireEvent.click(screen.getByRole("button", { name, exact: true })); }
function change(name, value) { fireEvent.change(screen.getByLabelText(name, { exact: true }), { target: { value } }); }

test("saved revision validation gates publication and preserves version history", async () => {
  const calls = [];
  release(async (_scope, command) => { calls.push(command); return command.op === "validate" ? { data: valid } : { data: { definition: { ...definition, draft_revision: 4, published_version_id: "v3" }, version: { ...versions[0], id: "v3", number: 3 } } }; });
  assert.equal(screen.getByRole("button", { name: "Publish saved draft" }).disabled, true);
  click("Validate saved draft"); await screen.findByText("Checked draft revision 3.");
  click("Publish saved draft"); await screen.findByText("Published version 3. Running workflows retain their earlier versions.");
  assert.deepEqual(calls[1], { op: "publish", definition: "definition", revision: 3 });
  assert.equal(screen.getByRole("button", { name: "Publish saved draft" }).disabled, true);
  assert.ok(screen.getAllByRole("option", { name: /v1 · Example/ }).length);
});

test("stale or unsupported validation cannot enable publication", async () => {
  for (const data of [{ ...valid, draft_revision: 4 }, { ...valid, executable: false, runtime_errors: [{ loc: ["nodes", 0, "config"], msg: "Handler unavailable" }] }, { ...valid, valid: false, executable: false }]) {
    release(async () => ({ data })); click("Validate saved draft");
    await waitFor(() => assert.equal(screen.getByRole("button", { name: "Validate saved draft" }).disabled, false));
    assert.equal(screen.getByRole("button", { name: "Publish saved draft" }).disabled, true);
    if (data.runtime_errors.length) assert.ok(screen.getByText("nodes · 0 · config: Handler unavailable")); cleanup();
  }
});

test("older version pages start the visible historical selection", async () => {
  const calls = [];
  release(async (_scope, command) => { calls.push(command); return { data: { id: "run", version_id: command.request.version_id, status: "pending" } }; }, { initialVersions: [versions[1]] });
  assert.equal(screen.getByLabelText("Published version").value, "v1");
  click("Start selected version"); await screen.findByText(/Run run · version v1/);
  assert.equal(calls[0].request.version_id, "v1");
});

test("version capabilities and diffs use explicit immutable version IDs", async () => {
  const calls = [];
  release(async (_scope, command) => { calls.push(command); return { data: command.op === "diff" ? { diff: "-Old\n+New" } : { ...valid, draft_revision: null } }; });
  click("Check version capabilities"); await screen.findByText(/Runtime capabilities are available/);
  click("Show version diff"); await screen.findByText(/-Old/);
  assert.deepEqual(calls, [{ op: "capabilities", definition: "definition", version: "v2" }, { op: "diff", definition: "definition", version: "v2", before: "v1" }]);
});

test("manual start freezes exact input/version/key across failed and successful retries", async () => {
  const calls = [];
  release(async (_scope, command) => { calls.push(structuredClone(command)); if (calls.length === 1) throw new Error("network"); return { data: { id: "run-one", version_id: "v2", status: "pending" } }; });
  change("Run input JSON", '{"value":1}'); click("Start selected version");
  await screen.findByText("Connection failed. Retry the same request when available.");
  assert.equal(screen.getByLabelText("Run input JSON").closest("fieldset").disabled, true);
  click("Retry same start"); await screen.findByText(/Run run-one/);
  assert.deepEqual(calls[0], calls[1]); assert.equal(calls[0].request.version_id, "v2"); assert.deepEqual(calls[0].request.input, { value: 1 });
  click("Retry same start"); await waitFor(() => assert.equal(calls.length, 3)); assert.deepEqual(calls[2], calls[0]);
  await waitFor(() => assert.equal(screen.getByRole("button", { name: "Prepare a separate run" }).disabled, false));
  click("Prepare a separate run"); click("Start selected version"); await waitFor(() => assert.equal(calls.length, 4));
  assert.notEqual(calls[3].request.idempotency_key, calls[0].request.idempotency_key);
});

test("duplicate clicks during a pending start invoke one action", async () => {
  let resolve; const calls = [];
  release(async (_scope, command) => { calls.push(command); return new Promise(ok => { resolve = ok; }); });
  click("Start selected version"); click("Retry same start"); assert.equal(calls.length, 1);
  await React.act(async () => resolve({ data: { id: "once", version_id: "v2", status: "pending" } }));
});

test("read-only users cannot publish or start; invalid input cannot start", () => {
  release(async () => { throw new Error("unexpected"); }, { permissions: ["read"] });
  assert.equal(screen.queryByRole("button", { name: "Publish saved draft" }), null); assert.equal(screen.queryByRole("button", { name: "Start selected version" }), null);
  cleanup(); release(async () => { throw new Error("unexpected"); }); change("Run input JSON", "[]");
  assert.equal(screen.getByRole("button", { name: "Start selected version" }).disabled, true);
});

test("webhook create masks aliases and updates omit signing configuration", async () => {
  const calls = [];
  editor(async (_scope, command) => { calls.push(command); return { data: { ...trigger, ...command.body, revision: 3, secret_alias: undefined } }; });
  change("Configured signing alias", "fixture-alias"); change("Definition ID", "definition"); change("Service principal ID", "principal");
  assert.equal(screen.getByLabelText("Configured signing alias").type, "password");
  click("Save trigger"); await screen.findByText("Configuration saved.");
  assert.equal(calls[0].body.secret_alias, "fixture-alias"); assert.equal(screen.queryByText("fixture-alias"), null);
  change("Trigger name", "Updated"); click("Save trigger"); await waitFor(() => assert.equal(calls.length, 2));
  assert.equal(calls[1].body.secret_alias, undefined); assert.equal(calls[1].body.expected_revision, 3);
});

test("rotation requires saved edits and sends only a new masked reference and revision", async () => {
  let call;
  editor(async (_scope, command) => { call = command; return { data: { ...trigger, revision: 3 } }; }, { initial: trigger });
  change("New configured signing alias", "rotation-fixture"); assert.equal(screen.getByLabelText("New configured signing alias").type, "password");
  click("Rotate signing reference"); await screen.findByText("Signing reference rotated.");
  assert.deepEqual(call, { op: "rotate", id: "hook", revision: 2, alias: "rotation-fixture", grace: 300 });
  assert.equal(screen.getByLabelText("New configured signing alias").value, "");
  change("Trigger name", "Unsaved"); assert.equal(screen.getByRole("button", { name: "Rotate signing reference" }).disabled, true);
});

test("cron edits retain configuration on conflicts and block invalid JSON", async () => {
  const calls = [];
  editor(async (_scope, command) => { calls.push(command); return { error: "Configuration changed" }; }, { kind: "schedule", initial: { ...trigger, id: "schedule", cron: "0 9 * * *", timezone: "UTC", input: {} } });
  change("Cron expression", "*/5 * * * *"); change("Time zone", "America/Toronto"); change("Version policy", "pinned"); change("Pinned version ID", "v1");
  change("Schedule input JSON", "{"); assert.equal(screen.getByRole("button", { name: "Save trigger" }).disabled, true);
  change("Schedule input JSON", "{}"); fireEvent.click(screen.getByLabelText("Enabled")); click("Save trigger"); await screen.findByText("Configuration changed");
  assert.equal(screen.getByLabelText("Cron expression").value, "*/5 * * * *"); assert.equal(calls[0].body.expected_revision, 2);
  assert.equal(calls[0].body.enabled, true); assert.equal(calls[0].body.version_id, "v1"); assert.equal(calls[0].body.concurrency_policy, "forbid");
});

test("history pagination preserves unsaved configuration and read-only controls", async () => {
  const calls = [];
  editor(async (_scope, command) => { calls.push(command); return { data: [] }; }, { initial: trigger, initialHistory: Array.from({ length: 50 }, (_, i) => ({ id: i, status: "accepted", execution_id: `run-${i}`, version_id: "v1", attempts: 1 })) });
  change("Trigger name", "Unsaved"); click("Older history"); await screen.findByText("No recorded decisions on this page.");
  assert.equal(calls[0].offset, 50); assert.equal(screen.getByLabelText("Trigger name").value, "Unsaved");
  cleanup(); editor(async () => { throw new Error("unexpected"); }, { initial: trigger, canManage: false });
  assert.equal(screen.getByRole("button", { name: "Save trigger" }).disabled, true);
});

function server(request) { return load("app/workflow-definitions/platform-actions.ts", { "@/lib/api": { builderRequest: request }, "@/lib/workflow-release": model }).runPlatformAction; }
test("all server actions enforce current organization and permission before requests", async () => {
  for (const command of [{ op: "publish", definition: "d", revision: 3 }, { op: "start", request: { version_id: "v1" } }, { op: "save-trigger", kind: "webhook", body: {} }, { op: "rotate", id: "hook" }, { op: "history", kind: "schedule", id: "s", offset: 0 }]) {
    for (const access of [{ organization_id: "other", actions: permissions }, { organization_id: "org", actions: [] }]) {
      const calls = [];
      const result = await server(async (...args) => { calls.push(args); return access; })("org", command);
      assert.ok(result.error); assert.equal(calls.length, 1);
    }
  }
});

test("publication revalidates revision and capabilities before creating a version", async () => {
  for (const validation of [{ ...valid, draft_revision: 4 }, { ...valid, executable: false }]) {
    const calls = [];
    const result = await server(async (...args) => { calls.push(args); return calls.length === 1 ? { organization_id: "org", actions: permissions } : validation; })("org", { op: "publish", definition: "d", revision: 3 });
    assert.ok(result.error); assert.equal(calls.length, 2);
  }
});

test("server routes explicit starts, trigger revisions and histories to scoped APIs", async () => {
  const calls = [];
  const run = server(async (...args) => { calls.push(args); return args[0] === "/access/permissions" ? { organization_id: "org", actions: permissions } : { id: "result" }; });
  const request = { definition_id: "d", version_id: "v", input: {}, idempotency_key: "stable-key" };
  await run("org", { op: "start", request }); assert.deepEqual(calls[1], ["/workflow-executions", request, "POST"]);
  await run("org", { op: "save-trigger", kind: "schedule", id: "a/b", body: { expected_revision: 7 } }); assert.deepEqual(calls[3], ["/workflow-schedules/a%2Fb", { expected_revision: 7 }, "PUT"]);
  await run("org", { op: "history", kind: "webhook", id: "a/b", offset: 50 }); assert.deepEqual(calls[5], ["/webhook-triggers/a%2Fb/deliveries?offset=50&limit=50"]);
});
