import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

test("workflow dashboard pages stay wired to the API flow", () => {
  assert.match(read("src/app/page.tsx"), /listWorkflowRuns/);
  assert.match(read("src/app/workflow-runs/page.tsx"), /listWorkflowRuns/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /getWorkflowRun/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /getUploadedInput/);
  assert.match(read("src/app/workflow-runs/new/page.tsx"), /createWorkflowRun/);
  assert.match(read("src/app/workflow-runs/new/page.tsx"), /createUploadedInput/);
});

test("workflow API client exposes workflow and uploaded input calls", () => {
  const api = read("src/lib/api.ts");

  assert.match(api, /export async function listWorkflowRuns/);
  assert.match(api, /export async function getWorkflowRun/);
  assert.match(api, /export async function createWorkflowRun/);
  assert.match(api, /export async function createUploadedInput/);
  assert.match(api, /export async function getUploadedInput/);
});
