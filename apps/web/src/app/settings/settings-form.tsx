"use client";

import { useActionState } from "react";
import type { AgentSetting, PromptVersion } from "@/lib/types";
import { updateAgentSettingAction, type SettingsActionState } from "./actions";

const initialState: SettingsActionState = { error: null, updatedAgent: null };

function formatAgent(agentType: string) {
  return agentType.replaceAll("_", " ");
}

export function AgentSettingsForm({
  setting,
  prompts,
}: {
  setting: AgentSetting;
  prompts: PromptVersion[];
}) {
  const [state, formAction, pending] = useActionState(
    updateAgentSettingAction,
    initialState,
  );
  const promptOptions = prompts.filter(
    (prompt) => prompt.agent_type === setting.agent_type,
  );

  return (
    <form action={formAction} className="border-t border-border px-4 py-4">
      <input type="hidden" name="agent_type" value={setting.agent_type} />
      <div className="grid gap-3 lg:grid-cols-[1fr_1.2fr_repeat(5,minmax(0,0.8fr))_auto]">
        <div>
          <p className="text-sm font-medium capitalize">{formatAgent(setting.agent_type)}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {setting.active_prompt_name ?? "No active prompt"}
          </p>
        </div>
        <label className="text-xs font-medium text-muted-foreground">
          Model
          <input
            name="model"
            defaultValue={setting.model}
            className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground"
          />
        </label>
        <label className="text-xs font-medium text-muted-foreground">
          Temp
          <input
            name="temperature"
            type="number"
            step="0.1"
            min="0"
            max="2"
            defaultValue={setting.temperature ?? ""}
            className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground"
          />
        </label>
        <label className="text-xs font-medium text-muted-foreground">
          Max Tokens
          <input
            name="max_tokens"
            type="number"
            min="1"
            defaultValue={setting.max_tokens}
            className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground"
          />
        </label>
        <label className="text-xs font-medium text-muted-foreground">
          Timeout
          <input
            name="timeout_seconds"
            type="number"
            min="1"
            defaultValue={setting.timeout_seconds ?? ""}
            className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground"
          />
        </label>
        <label className="text-xs font-medium text-muted-foreground">
          Retries
          <input
            name="max_retries"
            type="number"
            min="0"
            defaultValue={setting.max_retries}
            className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground"
          />
        </label>
        <label className="text-xs font-medium text-muted-foreground">
          Reviewer
          <input
            name="reviewer_approval_threshold"
            type="number"
            step="0.01"
            min="0"
            max="1"
            defaultValue={setting.reviewer_approval_threshold ?? ""}
            className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground"
          />
        </label>
        <label className="text-xs font-medium text-muted-foreground">
          Human
          <input
            name="human_approval_threshold"
            type="number"
            step="0.01"
            min="0"
            max="1"
            defaultValue={setting.human_approval_threshold ?? ""}
            className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground"
          />
        </label>
        <div className="lg:col-span-7">
          <label className="text-xs font-medium text-muted-foreground">
            Active Prompt Version
            <select
              name="active_prompt_version_id"
              defaultValue={setting.active_prompt_version_id ?? ""}
              className="mt-1 w-full rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground"
            >
              <option value="">Use active prompt fallback</option>
              {promptOptions.map((prompt) => (
                <option key={prompt.id} value={prompt.id}>
                  {prompt.name} v{prompt.version}
                  {prompt.is_active ? " (active)" : ""}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            {pending ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
      {state.error && (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {state.error}
        </p>
      )}
      {state.updatedAgent === setting.agent_type && (
        <p className="mt-3 text-sm text-muted-foreground">Saved.</p>
      )}
    </form>
  );
}
