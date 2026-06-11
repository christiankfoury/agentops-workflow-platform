import "server-only";

import type {
  CreateUploadedInputRequest,
  CreateWorkflowRunRequest,
  UploadedInput,
  WorkflowRun,
} from "./types";

function apiUrl(path: string): string {
  const base =
    process.env.API_INTERNAL_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000";
  return `${base}${path}`;
}

export async function listWorkflowRuns(): Promise<WorkflowRun[]> {
  const res = await fetch(apiUrl("/workflow-runs"), { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch workflow runs: ${res.status}`);
  return res.json() as Promise<WorkflowRun[]>;
}

export async function getWorkflowRun(id: string): Promise<WorkflowRun | null> {
  const res = await fetch(apiUrl(`/workflow-runs/${id}`), { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch workflow run: ${res.status}`);
  return res.json() as Promise<WorkflowRun>;
}

export async function createWorkflowRun(
  body: CreateWorkflowRunRequest,
): Promise<WorkflowRun> {
  const res = await fetch(apiUrl("/workflow-runs"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create workflow run: ${res.status}`);
  return res.json() as Promise<WorkflowRun>;
}

export async function createUploadedInput(
  body: CreateUploadedInputRequest,
): Promise<UploadedInput> {
  const res = await fetch(apiUrl("/uploaded-inputs"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create uploaded input: ${res.status}`);
  return res.json() as Promise<UploadedInput>;
}

export async function getUploadedInput(id: string): Promise<UploadedInput | null> {
  const res = await fetch(apiUrl(`/uploaded-inputs/${id}`), { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch uploaded input: ${res.status}`);
  return res.json() as Promise<UploadedInput>;
}
