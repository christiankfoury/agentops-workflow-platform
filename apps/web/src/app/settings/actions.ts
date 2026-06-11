"use server";

import { revalidatePath } from "next/cache";
import { updateAgentSetting } from "@/lib/api";

export type SettingsActionState = { error: string | null; updatedAgent: string | null };

const optionalNumber = (value: FormDataEntryValue | null): number | null => {
  if (typeof value !== "string" || value.trim() === "") return null;
  return Number(value);
};

export async function updateAgentSettingAction(
  _state: SettingsActionState,
  formData: FormData,
): Promise<SettingsActionState> {
  const agentType = String(formData.get("agent_type") ?? "");
  const model = String(formData.get("model") ?? "").trim();
  const promptId = String(formData.get("active_prompt_version_id") ?? "");
  const maxTokens = Number(formData.get("max_tokens"));
  const maxRetries = Number(formData.get("max_retries"));
  if (!agentType || !model || !Number.isFinite(maxTokens) || !Number.isFinite(maxRetries)) {
    return { error: "Model, max tokens, and max retries are required.", updatedAgent: null };
  }

  try {
    await updateAgentSetting(agentType, {
      model,
      temperature: optionalNumber(formData.get("temperature")),
      max_tokens: maxTokens,
      timeout_seconds: optionalNumber(formData.get("timeout_seconds")),
      max_retries: maxRetries,
      active_prompt_version_id: promptId || null,
      reviewer_approval_threshold: optionalNumber(
        formData.get("reviewer_approval_threshold"),
      ),
      human_approval_threshold: optionalNumber(formData.get("human_approval_threshold")),
    });
    revalidatePath("/settings");
    return { error: null, updatedAgent: agentType };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Failed to update setting.",
      updatedAgent: null,
    };
  }
}
