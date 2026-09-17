import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
const require = createRequire(import.meta.url);
function load(path, mocks = {}) {
  const source = readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const exports = {}; new Function("require", "exports", compiled)(name => mocks[name] ?? require(name), exports); return exports;
}
const { startPolling } = load("lib/live-poll.ts");
const flush = () => new Promise(resolve => setImmediate(resolve));
function setup(read, terminal = false) {
  const timers = new Map(), status = []; let next = 0, available = true, refreshed = 0;
  const loop = startPolling({ read, terminal, refresh: () => refreshed++, status: text => status.push(text),
    available: () => available, schedule: (fn, ms) => { timers.set(++next, { fn, ms }); return next; }, cancel: id => timers.delete(id) });
  return { loop, timers, status, available: value => { available = value; }, refreshed: () => refreshed,
    delay: () => [...timers.values()][0]?.ms,
    async tick() { const [id, timer] = timers.entries().next().value; timers.delete(id); timer.fn(); await flush(); } };
}
const pulse = (token = "a", terminal = false, interval_ms = 5000) => ({ data: { token, terminal, interval_ms } });

test("polling never overlaps and queues a mutation refresh during an in-flight read", async () => {
  const resolvers = []; let calls = 0;
  const state = setup(() => { calls++; return new Promise(resolve => resolvers.push(resolve)); });
  await state.tick(); state.loop.wake(); state.loop.wake(true); state.loop.wake(true);
  assert.equal(calls, 1);
  resolvers.shift()(pulse()); await flush(); assert.equal(calls, 2);
  resolvers.shift()(pulse()); await flush(); assert.equal(state.refreshed(), 2);
  assert.equal(state.timers.size, 1); state.loop.dispose();
});

test("offline and hidden tabs pause reads and reconnect once", async () => {
  let calls = 0; const state = setup(async () => { calls++; return pulse(); });
  state.available(false); await state.tick(); assert.equal(calls, 0); assert.equal(state.delay(), 15000);
  assert.match(state.status.at(-1), /paused/);
  state.available(true); state.loop.wake(); await flush(); assert.equal(calls, 1);
  assert.equal(state.refreshed(), 1); state.loop.dispose();
});

test("failures back off to 60 seconds, recover, and unchanged tokens avoid refresh", async () => {
  let fail = true; const state = setup(async () => fail ? { error: "offline" } : pulse("wait", false, 15000));
  for (const expected of [10000, 20000, 40000, 60000, 60000]) { await state.tick(); assert.equal(state.delay(), expected); }
  assert.equal(state.refreshed(), 0); fail = false; await state.tick(); assert.equal(state.delay(), 15000);
  await state.tick(); assert.equal(state.refreshed(), 1); state.loop.dispose();
});

test("terminal runs stop, manual refresh works, and permission changes stop automatic reads", async () => {
  const state = setup(async () => pulse("done", true)); await state.tick(); assert.equal(state.timers.size, 0);
  state.loop.wake(); await flush(); assert.equal(state.refreshed(), 1);
  state.loop.wake(true); await flush(); assert.equal(state.refreshed(), 2); state.loop.dispose();
  const denied = setup(async () => ({ error: "scope changed", stop: true })); await denied.tick();
  assert.equal(denied.timers.size, 0); assert.match(denied.status.at(-1), /access changed/); denied.loop.dispose();
  const initiallyDone = setup(async () => { throw Error("Must not read"); }, true);
  assert.equal(initiallyDone.timers.size, 0); initiallyDone.loop.dispose();
});

test("disposed polling ignores late results and server intervals are bounded", async () => {
  let resolve; const state = setup(() => new Promise(done => { resolve = done; }));
  await state.tick(); state.loop.dispose(); resolve(pulse()); await flush();
  assert.equal(state.refreshed(), 0); assert.equal(state.timers.size, 0);
  const bounded = setup(async () => pulse("active", false, 1)); await bounded.tick();
  assert.equal(bounded.delay(), 5000); bounded.loop.dispose();
});

test("live server action rechecks current organization and permissions", async () => {
  const calls = []; let access = { organization_id: "tenant-a", actions: ["read"] };
  const { readPulse } = load("app/operations/live-actions.ts", { "@/lib/api": { builderRequest: async path => {
    calls.push(path); return path === "/access/permissions" ? access : pulse().data;
  } } });
  assert.equal((await readPulse("tenant-b", "run", "id")).stop, true); assert.equal(calls.length, 1);
  access = { ...access, actions: [] }; assert.equal((await readPulse("tenant-a", "run", "id")).stop, true);
  access.actions = ["read"]; assert.equal((await readPulse("tenant-a", "execution", "id")).data.token, "a");
  assert.equal(calls.at(-1), "/operations/pulse?kind=execution&identity=id");
});

test("manual terminal retry has bounded failure backoff and disposed failures stay silent", async () => {
  const state = setup(async () => { throw Error("Offline"); }, true);
  state.loop.wake(true); await flush(); assert.equal(state.delay(), 10000); state.loop.dispose();
  let reject; const late = setup(() => new Promise((_resolve, fail) => { reject = fail; }));
  await late.tick(); const messages = late.status.length; late.loop.dispose(); reject(Error("Late")); await flush();
  assert.equal(late.status.length, messages); assert.equal(late.timers.size, 0);
});

test("mutation refresh survives a paused page refresh even when the token is unchanged", async () => {
  const state = setup(async () => pulse()); await state.tick(); assert.equal(state.refreshed(), 1);
  state.available(false); state.loop.wake(true); await flush(); assert.equal(state.refreshed(), 1);
  state.available(true); await state.tick(); assert.equal(state.refreshed(), 2); state.loop.dispose();
});

test("live lists bound pagination and approval run lookup fanout", async () => {
  const React = require("react"), { renderToStaticMarkup } = require("react-dom/server");
  const calls = [], rows = Array.from({ length: 26 }, (_, i) => ({ id: `a${i}`, workflow_run_id: `r${i}`, status: "pending" }));
  const { default: Page } = load("app/human-approvals/page.tsx", {
    "next/link": { default: props => React.createElement("a", props) }, "@/components/live-page": { LivePage: () => null },
    "./human-approvals-table": { HumanApprovalsTable: ({ rows }) => React.createElement("p", null, `Rendered ${rows.length} rows`) },
    "@/lib/api": { listHumanApprovals: async page => { calls.push(page); return rows; },
      getWorkflowRun: async id => { calls.push(id); return { id, status: "waiting_for_human" }; } },
  });
  const html = renderToStaticMarkup(await Page({ searchParams: Promise.resolve({ offset: "25" }) }));
  assert.deepEqual(calls[0], { offset: 25, limit: 26 }); assert.equal(calls.length, 26);
  assert.match(html, /Rendered 25 rows/); assert.match(html, /offset=50/); assert.match(html, /offset=0/);
  assert.match(html, /Counts and search apply to this page/);
});

test("operations renders bounded history, diagnostic meaning and current counts", async () => {
  const React = require("react"), { renderToStaticMarkup } = require("react-dom/server");
  const data = { observed_at: "fixture", jobs: { stale: 1, retrying: 2, dead_letter: 3 }, runs: {}, attempts: { completed: 4 },
    workers: {}, claims: 5, lease_recoveries: 1, abandoned_attempts: 1, linked_recoveries: 0, waiting_steps: 1,
    oldest_ready_seconds: 2, completed_in_window: 9, window_seconds: 900, queue_wait: { samples: 5, sum_seconds: 20, max_seconds: 7 } };
  const calls = [], { default: Page } = load("app/operations/page.tsx", {
    "next/link": { default: props => React.createElement("a", props) }, "@/components/live-page": { LivePage: () => null },
    "@/lib/api": { builderRequest: async path => { calls.push(path); return path === "/operations" ? data : { items: [], offset: 0, next_offset: null }; } },
  });
  const html = renderToStaticMarkup(await Page({ searchParams: Promise.resolve({ kind: "stale" }) }));
  assert.match(html, /Stale leases/); assert.match(html, /4\.00/); assert.match(html, /No jobs match/);
  assert.match(html, /does not prove the shared fleet is down/);
  assert.equal(calls[1], "/operations/jobs?kind=stale&offset=0&limit=25");
});
