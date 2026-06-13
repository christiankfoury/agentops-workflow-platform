import "server-only";

import { apiUrl } from "./api-url";
import type {
  AgentStep,
  AgentSetting,
  AgentPerformanceSummary,
  CorrectedEvaluationComparison,
  CreateUploadedInputRequest,
  DemoDatasetSummary,
  DemoSeedTarget,
  EvaluationComparison,
  CreateWorkflowRunRequest,
  DetectWorkflowRequest,
  EvaluationMetricsSummary,
  EvaluationResult,
  HumanApproval,
  HumanApprovalActionRequest,
  HumanApprovalEditRequest,
  HumanFeedbackSummary,
  CreatePromptVersionRequest,
  PromptVersion,
  UpdateAgentSettingRequest,
  UploadInputFileRequest,
  UploadedInput,
  WorkflowDetection,
  WorkflowEvent,
  WorkflowRunEvaluationComparison,
  WorkflowRun,
} from "./types";

const DEFAULT_FETCH_TIMEOUT_MS = 2500;
const AGENT_ACTION_FETCH_TIMEOUT_MS = 120000;
const EVALUATION_COMPARISON_FETCH_TIMEOUT_MS = 300000;

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(apiUrl(path), {
    ...init,
    signal: init.signal ?? AbortSignal.timeout(DEFAULT_FETCH_TIMEOUT_MS),
  });
}

export async function listWorkflowRuns(): Promise<WorkflowRun[]> {
  const res = await apiFetch("/workflow-runs", { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch workflow runs: ${res.status}`);
  return res.json() as Promise<WorkflowRun[]>;
}

export async function getWorkflowRun(id: string): Promise<WorkflowRun | null> {
  const res = await apiFetch(`/workflow-runs/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch workflow run: ${res.status}`);
  return res.json() as Promise<WorkflowRun>;
}

export async function createWorkflowRun(
  body: CreateWorkflowRunRequest,
): Promise<WorkflowRun> {
  const res = await apiFetch("/workflow-runs", {
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
  const res = await apiFetch("/uploaded-inputs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create uploaded input: ${res.status}`);
  return res.json() as Promise<UploadedInput>;
}

export async function uploadInputFile(
  body: UploadInputFileRequest,
): Promise<UploadedInput> {
  const formData = new FormData();
  formData.append("title", body.title);
  formData.append("input_type", body.input_type);
  if (body.notes) formData.append("notes", body.notes);
  formData.append("file", body.file);

  const res = await apiFetch("/uploaded-inputs/upload", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to upload input file: ${detail}`);
  }
  return res.json() as Promise<UploadedInput>;
}

export async function getUploadedInput(id: string): Promise<UploadedInput | null> {
  const res = await apiFetch(`/uploaded-inputs/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch uploaded input: ${res.status}`);
  return res.json() as Promise<UploadedInput>;
}

export async function detectWorkflowType(
  body: DetectWorkflowRequest,
): Promise<WorkflowDetection> {
  const res = await apiFetch("/uploaded-inputs/detect-workflow", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to detect workflow type: ${detail}`);
  }
  return res.json() as Promise<WorkflowDetection>;
}

export async function listAgentSteps(runId: string): Promise<AgentStep[]> {
  const res = await apiFetch(`/workflow-runs/${runId}/agent-steps`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch agent steps: ${res.status}`);
  return res.json() as Promise<AgentStep[]>;
}

export async function listWorkflowEvents(runId: string): Promise<WorkflowEvent[]> {
  const res = await apiFetch(`/workflow-runs/${runId}/events`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch workflow events: ${res.status}`);
  return res.json() as Promise<WorkflowEvent[]>;
}

export async function getEvaluationSummary(): Promise<EvaluationMetricsSummary[]> {
  const res = await apiFetch("/evaluation-results/summary", {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch evaluation summary: ${res.status}`);
  return res.json() as Promise<EvaluationMetricsSummary[]>;
}

export async function listEvaluationResults(): Promise<EvaluationResult[]> {
  const res = await apiFetch("/evaluation-results", {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch evaluation results: ${res.status}`);
  return res.json() as Promise<EvaluationResult[]>;
}

export async function getEvaluationComparisons(): Promise<EvaluationComparison[]> {
  const res = await apiFetch("/evaluation-results/comparisons", {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch evaluation comparisons: ${res.status}`);
  return res.json() as Promise<EvaluationComparison[]>;
}

export async function seedDemoDataset(
  target: DemoSeedTarget,
): Promise<DemoDatasetSummary> {
  const res = await apiFetch(`/demo/${target}`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to seed demo dataset: ${detail}`);
  }
  return res.json() as Promise<DemoDatasetSummary>;
}

export async function getAgentPerformanceSummary(): Promise<AgentPerformanceSummary[]> {
  const res = await apiFetch("/agent-performance", {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to fetch agent performance: ${res.status}`);
  return res.json() as Promise<AgentPerformanceSummary[]>;
}

export async function listPromptVersions(): Promise<PromptVersion[]> {
  const res = await apiFetch("/prompt-versions", { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch prompt versions: ${res.status}`);
  return res.json() as Promise<PromptVersion[]>;
}

export async function getPromptVersion(id: string): Promise<PromptVersion | null> {
  const res = await apiFetch(`/prompt-versions/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch prompt version: ${res.status}`);
  return res.json() as Promise<PromptVersion>;
}

export async function createPromptVersion(
  body: CreatePromptVersionRequest,
): Promise<PromptVersion> {
  const res = await apiFetch("/prompt-versions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to create prompt version: ${detail}`);
  }
  return res.json() as Promise<PromptVersion>;
}

export async function activatePromptVersion(id: string): Promise<PromptVersion> {
  const res = await apiFetch(`/prompt-versions/${id}/activate`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to activate prompt version: ${detail}`);
  }
  return res.json() as Promise<PromptVersion>;
}

export async function listAgentSettings(): Promise<AgentSetting[]> {
  const res = await apiFetch("/agent-settings", { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch agent settings: ${res.status}`);
  return res.json() as Promise<AgentSetting[]>;
}

export async function updateAgentSetting(
  agentType: string,
  body: UpdateAgentSettingRequest,
): Promise<AgentSetting> {
  const res = await apiFetch(`/agent-settings/${agentType}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to update agent setting: ${detail}`);
  }
  return res.json() as Promise<AgentSetting>;
}

export async function runSalesAnalyst(runId: string): Promise<AgentStep> {
  const res = await apiFetch(`/workflow-runs/${runId}/run-analyst`, {
    method: "POST",
    signal: AbortSignal.timeout(AGENT_ACTION_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === "string" ? body.detail : String(res.status);
    throw new Error(`Failed to run analyst: ${detail}`);
  }
  return res.json() as Promise<AgentStep>;
}

export async function runSalesBaseline(runId: string): Promise<AgentStep> {
  const res = await apiFetch(`/workflow-runs/${runId}/run-baseline`, {
    method: "POST",
    signal: AbortSignal.timeout(AGENT_ACTION_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === "string" ? body.detail : String(res.status);
    throw new Error(`Failed to run baseline: ${detail}`);
  }
  return res.json() as Promise<AgentStep>;
}

export async function runSalesReviewer(runId: string): Promise<AgentStep> {
  const res = await apiFetch(`/workflow-runs/${runId}/run-reviewer`, {
    method: "POST",
    signal: AbortSignal.timeout(AGENT_ACTION_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === "string" ? body.detail : String(res.status);
    throw new Error(`Failed to run reviewer: ${detail}`);
  }
  return res.json() as Promise<AgentStep>;
}

export async function runSalesWriter(runId: string): Promise<AgentStep> {
  const res = await apiFetch(`/workflow-runs/${runId}/run-writer`, {
    method: "POST",
    signal: AbortSignal.timeout(AGENT_ACTION_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === "string" ? body.detail : String(res.status);
    throw new Error(`Failed to run writer: ${detail}`);
  }
  return res.json() as Promise<AgentStep>;
}

export async function cancelWorkflowRun(runId: string): Promise<WorkflowRun> {
  const res = await apiFetch(`/workflow-runs/${runId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to cancel workflow run: ${detail}`);
  }
  return res.json() as Promise<WorkflowRun>;
}

export async function createEvaluationComparisonFromRun(
  runId: string,
): Promise<WorkflowRunEvaluationComparison> {
  const res = await apiFetch(`/workflow-runs/${runId}/evaluation-comparison`, {
    method: "POST",
    signal: AbortSignal.timeout(EVALUATION_COMPARISON_FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to create evaluation comparison: ${detail}`);
  }
  return res.json() as Promise<WorkflowRunEvaluationComparison>;
}

export async function createCorrectedEvaluationComparisonRun(
  evaluationCaseId: string,
): Promise<CorrectedEvaluationComparison> {
  const res = await apiFetch(
    `/evaluation-results/comparisons/${evaluationCaseId}/corrected-run`,
    {
      method: "POST",
      signal: AbortSignal.timeout(EVALUATION_COMPARISON_FETCH_TIMEOUT_MS),
    },
  );
  if (!res.ok) {
    const detail = await getErrorDetail(res);
    throw new Error(`Failed to create corrected run: ${detail}`);
  }
  return res.json() as Promise<CorrectedEvaluationComparison>;
}

export async function listHumanApprovals(): Promise<HumanApproval[]> {
  const res = await apiFetch("/human-approvals", { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch human approvals: ${res.status}`);
  return res.json() as Promise<HumanApproval[]>;
}

export async function getHumanApproval(id: string): Promise<HumanApproval | null> {
  const res = await apiFetch(`/human-approvals/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch human approval: ${res.status}`);
  return res.json() as Promise<HumanApproval>;
}

export async function getHumanFeedbackSummary(): Promise<HumanFeedbackSummary> {
  const res = await apiFetch("/human-approvals/feedback-summary", {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch human feedback summary: ${res.status}`);
  }
  return res.json() as Promise<HumanFeedbackSummary>;
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
  const res = await apiFetch(`/human-approvals/${id}/edit`, {
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
  const res = await apiFetch(`/human-approvals/${id}/${action}`, {
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
