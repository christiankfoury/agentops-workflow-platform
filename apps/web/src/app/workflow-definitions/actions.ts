"use server";

import { builderRequest } from "@/lib/api";
import { revalidatePath } from "next/cache";
import type { DraftBody, DraftDefinition, DraftResult } from "@/lib/workflow-builder";

export async function saveDraft(id: string | null, scope: string | null, body: DraftBody): Promise<DraftResult> {
  try {
    const access = await builderRequest<{ organization_id: string | null; actions: string[] }>("/access/permissions");
    if (access.organization_id !== scope) return { error: "Your organization changed. Your edits are retained; return to the original organization before saving." };
    if (!access.actions.includes("workflow.draft")) return { error: "You do not have permission to edit workflows." };
    const definition = await builderRequest<DraftDefinition>(id ? `/workflow-definitions/${encodeURIComponent(id)}/draft` : "/workflow-definitions", body, id ? "PUT" : "POST");
    revalidatePath("/workflow-definitions");
    return { definition };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "Draft could not be saved. Your edits are retained.",
      fields: error instanceof Error && "fields" in error ? error.fields as string[] : [] };
  }
}
