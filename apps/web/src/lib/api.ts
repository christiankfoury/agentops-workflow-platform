import "server-only";

import type {
  AgentStep,
  CreateUploadedInputRequest,
  CreateWorkflowRunRequest,
  HumanApproval,
  HumanApprovalActionRequest,
  HumanApprovalEditRequest,
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

export async function listAgentSteps(runId: string): Promise<AgentStep[]> {
  const res = await fetch(apiUrl(`/workflow-runs/${runId}/agent-steps`), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch agent steps: ${res.status}`);
  return res.json() as Promise<AgentStep[]>;
}

export async function runSalesAnalyst(runId: string): Promise<AgentStep> {
  const res = await fetch(apiUrl(`/workflow-runs/${runId}/run-analyst`), {
    method: "POST",
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === "string" ? body.detail : String(res.status);
    throw new Error(`Failed to run analyst: ${detail}`);
  }
  return res.json() as Promise<AgentStep>;
}

export async function runSalesReviewer(runId: string): Promise<AgentStep> {
  const res = await fetch(apiUrl(`/workflow-runs/${runId}/run-reviewer`), {
    method: "POST",
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === "string" ? body.detail : String(res.status);
    throw new Error(`Failed to run reviewer: ${detail}`);
  }
  return res.json() as Promise<AgentStep>;
}

export async function listHumanApprovals(): Promise<HumanApproval[]> {
  const res = await fetch(apiUrl("/human-approvals"), { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch human approvals: ${res.status}`);
  return res.json() as Promise<HumanApproval[]>;
}

export async function getHumanApproval(id: string): Promise<HumanApproval | null> {
  const res = await fetch(apiUrl(`/human-approvals/${id}`), { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch human approval: ${res.status}`);
  return res.json() as Promise<HumanApproval>;
}

export async function approveHumanApproval(
  id: string,
  body: HumanApprovalActionRequest,
): Promise<HumanApproval> {
  return postHumanApprovalAction(id, "approve", body);
}

export async function requestHumanApprovalRetry(
  id: string,
  body: HumanApprovalActionRequest,
): Promise<HumanApproval> {
  return postHumanApprovalAction(id, "request-retry", body);
}

export async function rejectHumanApproval(
  id: string,
  body: HumanApprovalActionRequest,
): Promise<HumanApproval> {
  return postHumanApprovalAction(id, "reject", body);
}

export async function editHumanApproval(
  id: string,
  body: HumanApprovalEditRequest,
): Promise<HumanApproval> {
  const res = await fetch(apiUrl(`/human-approvals/${id}/edit`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to edit human approval: ${detail}`);
  }
  return res.json() as Promise<HumanApproval>;
}

async function postHumanApprovalAction(
  id: string,
  action: "approve" | "request-retry" | "reject",
  body: HumanApprovalActionRequest,
): Promise<HumanApproval> {
  const res = await fetch(apiUrl(`/human-approvals/${id}/${action}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to ${action} human approval: ${detail}`);
  }
  return res.json() as Promise<HumanApproval>;
}

async function getErrorDetail(res: Response): Promise<string> {
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
  return typeof body?.detail === "string" ? body.detail : String(res.status);
}
