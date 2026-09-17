"use server";

import { builderRequest } from "@/lib/api";
import type { ControlRequest, ControlResult, ControlState } from "@/lib/execution-controls";

export async function controlExecution(scope: string | null, id: string, request: ControlRequest): Promise<ControlResult> {
  try {
    const access = await builderRequest<{ organization_id: string | null; actions: string[] }>("/access/permissions");
    const needed = request.action === "read" ? ["read"] : request.action === "resolve" ? ["tool.resolve"]
      : request.action === "recover" ? ["workflow.control", "workflow.start"] : ["workflow.control"];
    if (access.organization_id !== scope || needed.some(action => !access.actions.includes(action))) return { error: "Control access changed. Reload in the original organization." };
    const base = `/workflow-executions/${encodeURIComponent(id)}`;
    let recovery_id: string | undefined;
    if (request.action === "cancel") await builderRequest(`${base}/cancel`, { reason: request.reason }, "POST");
    else if (request.action === "recover") recovery_id = (await builderRequest<{ id: string }>(`${base}/recover`, { reason: request.reason }, "POST")).id;
    else if (request.action === "retry") await builderRequest(`${base}/jobs/${encodeURIComponent(request.job)}/retry`, {}, "POST");
    else if (request.action === "resolve") {
      const state = await builderRequest<ControlState>(`${base}/controls`);
      if (!state.effects.some(effect => effect.id === request.effect && effect.needs_resolution)) return { error: "Effect eligibility changed. Reload controls before recording reconciliation." };
      await builderRequest(`/tools/executions/${encodeURIComponent(request.effect)}/resolve`, { succeeded: request.succeeded, result: request.result, evidence: request.evidence }, "POST");
    } else if (request.action !== "read") return { error: "Unknown execution action." };
    return { state: await builderRequest<ControlState>(`${base}/controls`), recovery_id };
  } catch { return { error: "The action could not be confirmed. Reload eligibility before retrying. Recovery requests return the same linked run; retry budgets and effect resolution still apply." }; }
}
