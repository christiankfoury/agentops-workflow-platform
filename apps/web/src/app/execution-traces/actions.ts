"use server";

import { builderRequest } from "@/lib/api";
import { tracePath, type TraceRequest, type TraceResult } from "@/lib/execution-traces";

export async function readTrace(scope: string | null, request: TraceRequest): Promise<TraceResult> {
  try {
    const access = await builderRequest<{ organization_id: string | null; actions: string[] }>("/access/permissions");
    if (access.organization_id !== scope || !access.actions.includes("read")) return { error: "Trace access changed. Reload in the original organization to continue." };
    return { data: await builderRequest(tracePath(request)) };
  } catch { return { error: "This trace section is unavailable. It may be missing or outside your current organization. Retry to reload it." }; }
}
