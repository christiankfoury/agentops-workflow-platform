"use server";

import { revalidatePath } from "next/cache";
import { builderRequest } from "@/lib/api";
import { triggerPath, type ActionResult, type PlatformAction, type Validation } from "@/lib/workflow-release";
import type { DraftDefinition } from "@/lib/workflow-builder";

export async function runPlatformAction(scope: string | null, action: PlatformAction): Promise<ActionResult> {
  try {
    const access = await builderRequest<{ organization_id: string | null; actions: string[] }>("/access/permissions");
    if (access.organization_id !== scope) return { error: "Your organization changed. Return to the original organization before retrying." };
    const required = { validate: "read", capabilities: "read", diff: "read", history: "read", publish: "workflow.publish", start: "workflow.start", "save-trigger": "trigger.manage", rotate: "trigger.manage" }[action.op];
    if (!required || !access.actions.includes(required)) return { error: "You do not have permission for this action." };
    const encoded = encodeURIComponent;
    if (action.op === "validate") return { data: await builderRequest(`/workflow-definitions/${encoded(action.definition)}/validate`, {}, "POST") };
    if (action.op === "publish") {
      const path = `/workflow-definitions/${encoded(action.definition)}`;
      const validation = await builderRequest<Validation>(`${path}/validate`, {}, "POST");
      if (validation.draft_revision !== action.revision) return { error: "The saved draft changed. Reload and validate its current revision before publishing." };
      if (!validation.valid || !validation.executable) return { error: "The saved draft is not runnable. Resolve validation and capability errors before publishing.", fields: [...validation.errors, ...validation.runtime_errors].map(e => `${e.loc?.join(" · ") ?? "Graph"}: ${e.msg}`) };
      const version = await builderRequest(`${path}/publish`, { expected_revision: action.revision }, "POST");
      const definition = await builderRequest<DraftDefinition>(path);
      revalidatePath("/workflow-definitions");
      return { data: { version, definition } };
    }
    if (action.op === "capabilities") return { data: await builderRequest(`/workflow-definitions/${encoded(action.definition)}/versions/${encoded(action.version)}/capabilities`) };
    if (action.op === "diff") return { data: await builderRequest(`/workflow-definitions/${encoded(action.definition)}/versions/${encoded(action.version)}/diff?compare_to=${encoded(action.before)}`) };
    if (action.op === "start") {
      if (!action.request.version_id) return { error: "Select an explicit published version." };
      return { data: await builderRequest("/workflow-executions", action.request, "POST") };
    }
    if (action.op === "save-trigger") {
      const data = await builderRequest(`${triggerPath(action.kind)}${action.id ? `/${encoded(action.id)}` : ""}`, action.body, action.id ? "PUT" : "POST");
      revalidatePath("/workflow-triggers"); return { data };
    }
    if (action.op === "rotate") return { data: await builderRequest(`/webhook-triggers/${encoded(action.id)}/rotate-key`, { expected_revision: action.revision, secret_alias: action.alias, grace_seconds: action.grace }, "POST") };
    if (action.op === "history") return { data: await builderRequest(`${triggerPath(action.kind)}/${encoded(action.id)}/${action.kind === "webhook" ? "deliveries" : "fires"}?offset=${action.offset}&limit=50`) };
    return { error: "Unknown action" };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "The request failed. Your edits are retained.",
      fields: error instanceof Error && "fields" in error ? error.fields as string[] : [] };
  }
}
