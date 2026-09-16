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
  const exports = {};
  new Function("require", "exports", compiled)(name => mocks[name] ?? require(name), exports);
  return exports;
}
const model = load("lib/execution-traces.ts"), { TraceDebugger } = load("components/execution-traces/debugger.tsx");
const old = { id: "step-old", node_id: "compute", iteration: 0, branch: "main", status: "failed" };
const current = { id: "step-current", node_id: "compute", iteration: 1, branch: "main/left", status: "waiting", waiting_reason: "delay" };
const head = { source: "generic", run: { id: "run", status: "waiting" }, version: { id: "pinned-v1", number: 1, name: "Fixture" },
  graph: { nodes: [{ id: "compute", type: "code" }, { id: "later", type: "transform" }], edges: [{ source: "compute", target: "later", state: "skipped" }] },
  latest_steps: [current], usage_source: "Per-attempt usage only; projections excluded." };
const empty = { items: [], offset: 0, next_offset: null };
function view(read, extras = {}) { return render(React.createElement(TraceDebugger, { head, initial: { ...empty, items: [old, current] }, scope: "org", read, ...extras })); }
function click(name) { fireEvent.click(screen.getByRole("button", { name, exact: true })); }
const payload = text => ({ text, truncated: false, limit: 64000 });

test("pinned graph selection uses latest identity while history inspects the earlier iteration", async () => {
  const calls = [];
  view(async (_scope, request) => { calls.push(request); return { data: { record: request.record === old.id ? old : current, payloads: { output: payload(request.record) } } }; });
  assert.ok(screen.getByText("Pinned version 1 · pinned-v1"));
  assert.ok(screen.getByRole("img", { name: "Immutable graph with current edge decisions" }));
  click("compute · code · waiting"); await screen.findByText("Selected record · step-current");
  click("Inspect step-old"); await screen.findByText("Selected record · step-old");
  assert.deepEqual(calls.map(call => call.record), [current.id, old.id]);
  click("later · transform · not started"); assert.ok(screen.getByText("No step record exists for later yet."));
});

test("attempt paging retains exact logical step and renders only selected attempt usage", async () => {
  const calls = [];
  view(async (_scope, request) => { calls.push(request); return { data: request.record ? { record: { id: "attempt", number: 2, status: "failed" }, usage: { total_tokens: 12, estimated_cost_usd: null, usage_complete: false }, payloads: {} } : { items: [{ id: "attempt", number: 2 }], offset: request.offset, next_offset: request.offset === 0 ? 25 : null } }; });
  click("Attempts for step-old"); await screen.findByText("Trace history · attempts");
  click("Next page"); await waitFor(() => assert.equal(calls.length, 2));
  await waitFor(() => assert.equal(screen.getByRole("button", { name: "Inspect attempt" }).disabled, false));
  click("Inspect attempt"); await screen.findByText("Selected attempt usage");
  assert.ok(calls.every(call => call.step === old.id)); assert.equal(calls[1].offset, 25);
  assert.ok(screen.getByText("12")); assert.ok(screen.getByText("Unavailable"));
});

test("section failure retains existing records and successful retry replaces only the section", async () => {
  let fail = true;
  view(async () => fail ? { error: "Tools temporarily unavailable" } : { data: { ...empty, items: [{ id: "effect", status: "unknown", call_id: "call-1" }] } });
  click("Tools"); await screen.findByRole("alert"); assert.ok(screen.getByRole("button", { name: "Inspect step-old" }));
  fail = false; click("Tools"); await screen.findByText("Trace history · tools"); assert.ok(screen.getByText("unknown"));
  assert.equal(screen.queryByRole("button", { name: "Inspect step-old" }), null);
});

test("bounded details, empty approvals and initial history failure remain usable", async () => {
  view(async (_scope, request) => ({ data: request.payloads ? { input: { text: "[REDACTED]", truncated: true, limit: 64000 } } : empty }), { initial: empty, initialError: true });
  assert.ok(screen.getByRole("alert")); click("Load run input, output and errors");
  await screen.findByText("Preview limited to 64,000 characters or the structure limit.");
  assert.ok(screen.getByText("[REDACTED]")); click("Approvals"); await screen.findByText("Trace history · approvals");
  assert.ok(screen.getByText("No records on this page."));
});

test("legacy views preserve source totals and labels without invented graph or generic controls", () => {
  view(async () => { throw new Error("unexpected"); }, { head: { source: "legacy", run: { id: "legacy", total_tokens: 18, total_cost: 0.2 }, usage_source: "Historical source totals" }, initial: { ...empty, items: [{ id: "agent", agent_name: "Original analyst", cost: 0.2 }] } });
  assert.ok(screen.getByText("Original analyst")); assert.ok(screen.getByText("18"));
  assert.equal(screen.queryByRole("img"), null); assert.equal(screen.queryByRole("button", { name: "Tools" }), null);
  assert.equal(screen.queryByRole("button", { name: "Attempts for agent" }), null);
});

test("pending detail requests suppress double clicks", async () => {
  let resolve, count = 0;
  view(async () => { count++; return new Promise(ok => { resolve = ok; }); });
  click("Inspect step-old"); click("Inspect step-current"); assert.equal(count, 1);
  await React.act(async () => resolve({ data: { record: old, payloads: {} } }));
});

test("server trace reads recheck current tenant and read permission before detail access", async () => {
  const calls = [];
  let access = { organization_id: "other", actions: ["read"] };
  const read = load("app/execution-traces/actions.ts", { "@/lib/execution-traces": model, "@/lib/api": { builderRequest: async path => { calls.push(path); return path === "/access/permissions" ? access : empty; } } }).readTrace;
  assert.ok((await read("org", { id: "run", kind: "steps" })).error); assert.equal(calls.length, 1);
  access = { organization_id: "org", actions: [] }; assert.ok((await read("org", { id: "run", kind: "steps" })).error);
  access.actions = ["read"]; await read("org", { id: "a/b", kind: "attempts", record: "c/d", step: "e/f" });
  assert.equal(calls.at(-1), "/execution-traces/a%2Fb/records/attempts/c%2Fd?offset=0&limit=25&step_id=e%2Ff");
  assert.throws(() => model.tracePath({ id: "run", legacy: true, kind: "tools" }));
});
