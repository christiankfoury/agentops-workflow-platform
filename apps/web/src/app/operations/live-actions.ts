"use server";

import { builderRequest } from "@/lib/api";
import type { LiveKind, Pulse, PulseResult } from "@/lib/live-poll";

export async function readPulse(scope: string | null, kind: LiveKind, id?: string): Promise<PulseResult> {
  try {
    const access = await builderRequest<{ organization_id: string | null; actions: string[] }>("/access/permissions");
    if (access.organization_id !== scope || !access.actions.includes("read")) return { error: "Access changed", stop: true };
    return { data: await builderRequest<Pulse>(`/operations/pulse?kind=${encodeURIComponent(kind)}${id ? `&identity=${encodeURIComponent(id)}` : ""}`) };
  } catch (error) { return { error: "Live state unavailable", stop: [401, 403, 404].includes(Number((error as { status?: number }).status)) }; }
}
