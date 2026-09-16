import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test, { afterEach } from "node:test";
import ts from "typescript";
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost" });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.HTMLElement = dom.window.HTMLElement;
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const require = createRequire(import.meta.url);
const React = require("react");
const { render, screen, fireEvent, cleanup, waitFor } = await import("@testing-library/react");
afterEach(cleanup);
function load(path, mocks = {}) {
  const source = readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const exports = {};
  new Function("require", "exports", compiled)(name => mocks[name] ?? (name === "next/cache" ? { revalidatePath: () => {} } : require(name)), exports);
  return exports;
}
const model = load("lib/workflow-builder.ts");
const fields = load("components/workflow-builder/fields.tsx");
const { WorkflowBuilder } = load("components/workflow-builder/editor.tsx", {
  "@/lib/workflow-builder": model, "./fields": fields,
});
const initial = () => ({ id: "definition-a", organization_id: "org-a", name: "Example", description: "",
  draft_graph: model.starterGraph(), draft_revision: 3, archived: false, published_version_id: null });
function setup(props = {}) {
  return render(React.createElement(WorkflowBuilder, { scope: "org-a", canEdit: true,
    save: async () => { throw new Error("Unexpected save"); }, ...props }));
}
function change(label, value) { fireEvent.change(screen.getByLabelText(label, { exact: true }), { target: { value } }); }
function click(name) { fireEvent.click(screen.getByRole("button", { name, exact: true })); }
function add(type) { change("New step type", type); click("Add node"); }

test("creates a deterministic two-node graph, saves and reopens equivalent semantics", async () => {
  let stored;
  setup({ save: async (id, scope, body) => {
    assert.equal(id, null); assert.equal(scope, "org-a"); assert.equal(body.expected_revision, undefined);
    stored = { ...initial(), name: body.name, draft_graph: structuredClone(body.graph), draft_revision: 1 };
    return { definition: stored };
  } });
  change("Workflow name", "Delivery note"); add("delay"); change("Delay seconds", "0");
  change("From node", "message"); change("To node", "delay_1"); click("Add connection");
  click("Save draft"); await screen.findByText("Saved draft revision 1.");
  assert.equal(stored.draft_graph.nodes[1].config.seconds, 0);
  assert.deepEqual(stored.draft_graph.edges, [{ source: "message", target: "delay_1" }]);
  cleanup(); let resaved;
  setup({ initial: stored, save: async (_id, _scope, body) => { resaved = body; return { definition: { ...stored, draft_revision: 2 } }; } });
  change("Inspect node", "delay_1"); assert.equal(screen.getByLabelText("Delay seconds").value, "0");
  click("Save draft"); await screen.findByText("Saved draft revision 2.");
  assert.deepEqual(resaved.graph, stored.draft_graph); assert.equal(resaved.expected_revision, 1);
});

test("all eight typed forms edit their own node configuration", async () => {
  let body;
  setup({ tools: [{ id: "tool-id", name: "Issue tracker" }], prompts: [{ id: "prompt-id", name: "Summarizer" }],
    save: async (_id, _scope, draft) => { body = draft; return { definition: { ...initial(), draft_graph: draft.graph } }; } });
  add("code"); change("Handler", "builtin.identity"); change("Handler version", "2");
  add("llm"); change("Prompt version", "prompt-id"); change("Model", "fixture-model"); change("Maximum tokens", "64");
  add("tool"); change("Tool", "tool-id"); change("Adapter", "github"); change("Tool version", "3");
  add("condition"); change("Default outcome", "fallback"); change("Condition cases JSON · [{label, when}]", '[{"label":"yes","when":{"op":"literal","value":true}}]');
  add("approval"); change("Review retries", "3"); change("Approval deadline (seconds)", "300"); change("Timeout action", "reject");
  add("transform"); change("Assignments JSON", '{"result":{"op":"literal","value":true}}');
  add("parallel"); change("Join node", "join"); change("Branches JSON · [{name, entry_node}]", '[{"name":"left","entry_node":"code_1"},{"name":"right","entry_node":"tool_3"}]');
  add("delay"); change("Delay seconds", ""); change("Wake at", "2027-01-01T10:00:00Z");
  click("Save draft"); await screen.findByText("Saved draft revision 3.");
  const nodes = body.graph.nodes.slice(1);
  assert.deepEqual(nodes.map(n => n.type), ["code", "llm", "tool", "condition", "approval", "transform", "parallel", "delay"]);
  assert.equal(nodes[0].config.version, 2); assert.equal(nodes[1].config.prompt_version_id, "prompt-id");
  assert.equal(nodes[2].config.adapter, "github"); assert.equal(nodes[3].config.default, "fallback");
  assert.equal(nodes[4].config.deadline_seconds, 300); assert.equal(nodes[5].config.assign.result.value, true);
  assert.equal(nodes[6].config.branches.length, 2); assert.equal(nodes[7].config.seconds, undefined);
});

test("malformed JSON survives node changes and blocks save until repaired", () => {
  setup(); change("Inspect node", "message"); change("Assignments JSON", "{broken");
  add("delay"); assert.equal(screen.getByRole("button", { name: "Save draft" }).disabled, true);
  change("Inspect node", "message"); assert.equal(screen.getByLabelText("Assignments JSON").value, "{broken");
  change("Assignments JSON", "{}"); assert.equal(screen.getByRole("button", { name: "Save draft" }).disabled, false);
});

test("schema, binding, retry and bounded revision editors preserve their values", async () => {
  let saved;
  setup({ save: async (_id, _scope, body) => { saved = body; return { definition: initial() }; } });
  change("Inspect node", "message");
  const retry = { max_attempts: 3, retryable_errors: ["timeout"], initial_delay_seconds: 1, max_delay_seconds: 10, backoff_factor: 2, jitter_fraction: 0 };
  const quality = { entry_node: "message", review_node: "review", nodes: ["message", "review"], max_revisions: 2, retry_on_low_score: true };
  change("Retry policy JSON", JSON.stringify(retry));
  change("Bounded quality revision JSON (optional)", JSON.stringify(quality));
  change("Input bindings JSON", '{"value":{"op":"literal","value":1}}');
  change("Node input schema JSON", '{"type":"object","properties":{"value":{"type":"integer"}}}');
  change("Node timeout (seconds)", "90"); click("Save draft");
  await screen.findByText("Saved draft revision 3.");
  assert.deepEqual(saved.graph.nodes[0].retry, retry); assert.deepEqual(saved.graph.quality_revision, quality);
  assert.equal(saved.graph.nodes[0].inputs.value.value, 1); assert.equal(saved.graph.nodes[0].timeout_seconds, 90);
});

test("conflict preserves all edits, original revision and retry body", async () => {
  const calls = [];
  setup({ initial: initial(), save: async (...args) => { calls.push(structuredClone(args)); return { error: "Draft changed on the server", fields: ["nodes · delay: invalid field"] }; } });
  change("Workflow name", "My unsaved title"); add("delay"); click("Save draft");
  await screen.findByText("Draft changed on the server");
  assert.equal(screen.getByLabelText("Workflow name").value, "My unsaved title");
  assert.ok(screen.getByText("nodes · delay: invalid field"));
  click("Save draft"); await waitFor(() => assert.equal(calls.length, 2));
  assert.deepEqual(calls[0], calls[1]); assert.equal(calls[1][2].expected_revision, 3);
});

test("pending saves freeze mutations; rejected network calls retain edits", async () => {
  let reject;
  setup({ save: () => new Promise((_, no) => { reject = no; }) });
  click("Save draft"); assert.equal(screen.getByRole("button", { name: "Saving…" }).disabled, true);
  assert.equal(screen.getByLabelText("Workflow name").closest("fieldset").disabled, true);
  await React.act(async () => reject(new Error("offline")));
  await screen.findByText("The connection failed. Your edits are retained; retry saving.");
});

test("read-only and archived drafts allow inspection but no edits", () => {
  const draft = initial(); draft.draft_graph.nodes.push(model.newNode("delay", "wait"));
  setup({ initial: draft, canEdit: false });
  change("Inspect node", "wait"); assert.equal(screen.getByLabelText("Delay seconds").closest("fieldset").disabled, true);
  assert.equal(screen.getByRole("button", { name: "Save draft" }).disabled, true);
  cleanup(); setup({ initial: { ...draft, archived: true } });
  assert.equal(screen.getByRole("button", { name: "Save draft" }).disabled, true);
});

test("unsupported drafts are preserved and can be repaired as JSON", async () => {
  let saved;
  const draft = { ...initial(), draft_graph: { custom: "keep", nodes: [null] } };
  setup({ initial: draft, save: async (_id, _scope, body) => { saved = body; return { definition: draft }; } });
  assert.match(screen.getByLabelText("Graph JSON").value, /keep/);
  click("Save draft"); await screen.findByText("Saved draft revision 3."); assert.deepEqual(saved.graph, draft.draft_graph);
  change("Graph JSON", "[]"); assert.equal(screen.getByRole("button", { name: "Save draft" }).disabled, true);
  change("Graph JSON", JSON.stringify(model.starterGraph())); assert.ok(screen.getByRole("region", { name: "Graph canvas" }));
});

test("deletion removes incident edges and diagnoses remaining bindings", () => {
  const graph = model.starterGraph(); graph.nodes.push(model.newNode("delay", "wait")); graph.edges.push({ source: "message", target: "wait" });
  setup({ initial: { ...initial(), draft_graph: graph } }); change("Inspect node", "message"); click("Remove node message");
  assert.ok(screen.getByText("Bindings · message: referenced node is missing."));
  assert.equal(screen.queryByRole("button", { name: "Remove connection 1" }), null);
});

test("local diagnostics identify invalid edges, cycles and configuration paths", () => {
  const graph = model.starterGraph(); graph.edges.push({ source: "message", target: "message" });
  graph.nodes.push({ ...model.newNode("delay", "wait"), config: { seconds: -1, wake_at: "tomorrow" } });
  const issues = model.draftIssues(graph).join("\n");
  assert.match(issues, /self connections/); assert.match(issues, /cycle/); assert.match(issues, /wait · seconds/); assert.match(issues, /wait · wake_at/);
});

test("server actions reject changed organization and permissions before mutation", async () => {
  for (const access of [{ organization_id: "org-b", actions: ["workflow.draft"] }, { organization_id: "org-a", actions: ["read"] }]) {
    const requests = [];
    const { saveDraft } = load("app/workflow-definitions/actions.ts", { "@/lib/api": { builderRequest: async (...args) => { requests.push(args); return access; } } });
    const result = await saveDraft("definition-a", "org-a", { name: "Mine", graph: model.starterGraph(), description: "", expected_revision: 3 });
    assert.ok(result.error); assert.equal(requests.length, 1);
  }
});

test("server action sends exact revision and graph", async () => {
  const requests = [], draft = initial();
  const { saveDraft } = load("app/workflow-definitions/actions.ts", { "@/lib/api": { builderRequest: async (...args) => {
    requests.push(args); return requests.length === 1 ? { organization_id: "org-a", actions: ["workflow.draft"] } : draft;
  } } });
  const body = { name: draft.name, description: "", graph: draft.draft_graph, expected_revision: 3 };
  assert.deepEqual(await saveDraft("id/unsafe", "org-a", body), { definition: draft });
  assert.deepEqual(requests[1], ["/workflow-definitions/id%2Funsafe/draft", body, "PUT"]);
});

test("API adapter reports conflicts and field paths without reflecting submitted input", async () => {
  const originalFetch = globalThis.fetch;
  const api = load("lib/api.ts", { "server-only": {}, "./api-url": { apiUrl: p => `http://fixture${p}` },
    "./identity": { identityHeaders: async () => new Headers() } });
  try {
    for (const status of [403, 404, 409, 422, 500]) {
      globalThis.fetch = async () => new Response(JSON.stringify({ detail: [{ loc: ["body", "graph", "nodes", 0], msg: "Invalid node", input: "private draft" }] }), { status });
      await assert.rejects(api.builderRequest("/workflow-definitions", {}, "POST"), error => {
        assert.doesNotMatch(error.message, /private draft/);
        if (status === 422) assert.deepEqual(error.fields, ["body · graph · nodes · 0: Invalid node"]);
        if (status === 409) assert.match(error.message, /draft changed/);
        return true;
      });
    }
  } finally { globalThis.fetch = originalFetch; }
});
