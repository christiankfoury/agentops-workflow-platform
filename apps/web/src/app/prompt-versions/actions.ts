"use server";

import { redirect } from "next/navigation";
import { activatePromptVersion, createPromptVersion } from "@/lib/api";
import type { AgentType } from "@/lib/types";

export interface PromptVersionFormState {
  error: string | null;
}

function cleanOptional(value: FormDataEntryValue | null): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function isAgentType(value: FormDataEntryValue | null): value is AgentType {
  return (
    value === "analyst" ||
    value === "reviewer" ||
    value === "writer" ||
    value === "router" ||
    value === "timeline" ||
    value === "root_cause" ||
    value === "classifier" ||
    value === "insight"
  );
}

export async function createPromptVersionAction(
  _previousState: PromptVersionFormState,
  formData: FormData,
): Promise<PromptVersionFormState> {
  const agentType = formData.get("agent_type");
  const name = cleanOptional(formData.get("name"));
  const versionValue = Number(formData.get("version"));
  const template = cleanOptional(formData.get("template"));
  if (!isAgentType(agentType)) return { error: "Choose a valid agent type." };
  if (name === null) return { error: "Prompt name is required." };
  if (!Number.isInteger(versionValue) || versionValue < 1) {
    return { error: "Version must be a positive integer." };
  }
  if (template === null) return { error: "Template is required." };

  try {
    const prompt = await createPromptVersion({
      agent_type: agentType,
      name,
      version: versionValue,
      template,
      notes: cleanOptional(formData.get("notes")),
      is_active: formData.get("is_active") === "on",
    });
    redirect(`/prompt-versions/${prompt.id}`);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Failed to create prompt version.",
    };
  }
}

export async function activatePromptVersionAction(formData: FormData): Promise<void> {
  const promptId = formData.get("prompt_id");
  if (typeof promptId !== "string" || promptId.length === 0) {
    throw new Error("Prompt version id is required.");
  }
  await activatePromptVersion(promptId);
  redirect(`/prompt-versions/${promptId}`);
}
