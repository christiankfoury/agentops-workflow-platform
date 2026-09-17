import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test, { afterEach } from "node:test";
import ts from "typescript";
import { JSDOM } from "jsdom";
const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost" });
globalThis.window = dom.window; globalThis.document = dom.window.document; globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.FormData = dom.window.FormData;
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const require = createRequire(import.meta.url), React = require("react");
const { render, screen, fireEvent, cleanup, waitFor } = await import("@testing-library/react");
afterEach(cleanup);
function load(path, mocks = {}) {
  const source = readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const exports = {}; new Function("require", "exports", compiled)(name => mocks[name] ?? require(name), exports); return exports;
}
const { ExecutionControls } = load("components/execution-traces/controls.tsx", { "next/link": { default: props => React.createElement("a", props) } });
const initial = { id: "run", status: "failed", state_revision: 7, source_id: null, recovery_id: null, can_cancel: false, can_recover: true, can_resolve: false, reasons: [], jobs: [], effects: [] };
function view(action) { render(React.createElement(ExecutionControls, { id: "run", scope: "org", action })); }
function click(name) { fireEvent.click(screen.getByRole("button", { name, exact: true })); }
async function ready() { click("Load control eligibility"); await screen.findByText("Current state: failed · revision 7"); }

test("controls require explicit eligibility and show the reason for blocked recovery", async () => {
  let calls = 0;
  view(async () => { calls++; return { state: { ...initial, can_recover: false, reasons: ["Effect outcome is uncertain; reconcile first."] } }; });
  assert.equal(calls, 0); await ready(); assert.equal(calls, 1);
  assert.ok(screen.getByText("Effect outcome is uncertain; reconcile first."));
  assert.equal(screen.getByRole("button", { name: "Create linked recovery" }).disabled, true);
  assert.equal(screen.getByRole("button", { name: "Cancel execution" }).disabled, true);
});

test("recovery double clicks submit once and retain the linked result", async () => {
  const calls = []; let complete;
  view(async (_scope, _id, request) => { calls.push(request); if (request.action === "read") return { state: initial }; return await new Promise(resolve => { complete = resolve; }); });
  await ready(); fireEvent.change(screen.getByLabelText("Reason for action"), { target: { value: "Recover the failed final node" } });
  click("Create linked recovery"); click("Create linked recovery");
  await waitFor(() => assert.equal(calls.length, 2));
  await React.act(async () => complete({ state: { ...initial, recovery_id: "child" }, recovery_id: "child" }));
  assert.equal(screen.getByRole("link", { name: "Open linked recovery run" }).getAttribute("href"), "/execution-traces/child");
  assert.deepEqual(calls[1], { action: "recover", reason: "Recover the failed final node" });
});

test("failed control requests retain eligibility and entered reason for an explicit retry", async () => {
  let failed = false;
  view(async () => failed ? { error: "Permission changed; reload" } : { state: initial });
  await ready(); fireEvent.change(screen.getByLabelText("Reason for action"), { target: { value: "Retained reason" } });
  failed = true; click("Create linked recovery"); await screen.findByRole("alert");
  assert.equal(screen.getByLabelText("Reason for action").value, "Retained reason");
  assert.ok(screen.getByText("Current state: failed · revision 7"));
});

test("reconciliation validates JSON and sends evidence without repeating the remote action", async () => {
  const calls = [], state = { ...initial, can_recover: false, can_resolve: true, effects: [{ id: "effect", status: "unknown", needs_resolution: true }] };
  view(async (_scope, _id, request) => { calls.push(request); return { state }; }); await ready();
  fireEvent.change(screen.getByLabelText("Reconciliation evidence"), { target: { value: "Verified local sink record" } });
  fireEvent.change(screen.getByLabelText("Successful result JSON"), { target: { value: "invalid" } });
  click("Record confirmed success"); assert.equal(calls.length, 1); assert.ok(screen.getByRole("alert"));
  fireEvent.change(screen.getByLabelText("Successful result JSON"), { target: { value: '{"value":"one"}' } });
  click("Record confirmed success"); await waitFor(() => assert.equal(calls.length, 2));
  assert.deepEqual(calls[1], { action: "resolve", effect: "effect", succeeded: true, result: { value: "one" }, evidence: "Verified local sink record" });
});

test("job recovery eligibility preserves queued backoff and sends the exact expired job", async () => {
  const calls = [], state = { ...initial, jobs: [
    { id: "queued", status: "queued", can_retry: false, note: "Already scheduled", recovery_count: 1, max_recoveries: 3 },
    { id: "expired", status: "running", can_retry: true, note: "Existing budgets apply", recovery_count: 2, max_recoveries: 3 },
  ] };
  view(async (_scope, _id, request) => { calls.push(request); return { state }; }); await ready();
  assert.equal(screen.getByRole("button", { name: "Recover expired job queued" }).disabled, true);
  click("Recover expired job expired"); await waitFor(() => assert.equal(calls.length, 2));
  assert.deepEqual(calls[1], { action: "retry", job: "expired" });
});

test("server controls check current scope, both recovery permissions and effect ownership", async () => {
  const calls = []; let access = { organization_id: "other", actions: ["read", "workflow.control", "workflow.start", "tool.resolve"] };
  const { controlExecution } = load("app/execution-traces/control-actions.ts", { "@/lib/api": { builderRequest: async (path, body, method) => {
    calls.push({ path, body, method }); if (path === "/access/permissions") return access;
    if (path.endsWith("/controls")) return initial; return { id: "child" };
  } } });
  assert.ok((await controlExecution("org", "run", { action: "recover", reason: "test" })).error); assert.equal(calls.length, 1);
  access = { organization_id: "org", actions: ["workflow.control"] };
  assert.ok((await controlExecution("org", "run", { action: "recover", reason: "test" })).error); assert.equal(calls.length, 2);
  access.actions.push("workflow.start");
  assert.equal((await controlExecution("org", "run", { action: "recover", reason: "test" })).recovery_id, "child");
  assert.ok(calls.some(call => call.path === "/workflow-executions/run/recover" && call.method === "POST"));
  access.actions.push("tool.resolve"); const before = calls.length;
  assert.ok((await controlExecution("org", "run", { action: "resolve", effect: "other-effect", succeeded: false, result: null, evidence: "test" })).error);
  assert.equal(calls.length, before + 2);
});
