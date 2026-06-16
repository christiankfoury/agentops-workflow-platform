"use client";

import { useActionState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { getAgentDisplay } from "@/lib/agent-display";
import type { AgentSetting, PromptVersion } from "@/lib/types";
import { updateAgentSettingAction, type SettingsActionState } from "./actions";

const initialState: SettingsActionState = { error: null, updatedAgent: null };

const reviewerAgentType = "reviewer";

function formatOptionalNumber(value: number | null): string {
  return value === null ? "Not set" : String(value);
}

function Field({
  children,
  label,
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <label className="text-xs font-medium uppercase text-muted-foreground">
      {label}
      {children}
    </label>
  );
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
  const agent = getAgentDisplay(setting.agent_type);
  const promptOptions = prompts.filter(
    (prompt) => prompt.agent_type === setting.agent_type,
  );
  const showApprovalThresholds = setting.agent_type === reviewerAgentType;

  return (
    <form action={formAction} className="rounded-lg border border-border bg-card shadow-sm">
      <input type="hidden" name="agent_type" value={setting.agent_type} />
      {!showApprovalThresholds ? (
        <>
          <input
            type="hidden"
            name="reviewer_approval_threshold"
            value={setting.reviewer_approval_threshold ?? ""}
          />
          <input
            type="hidden"
            name="human_approval_threshold"
            value={setting.human_approval_threshold ?? ""}
          />
        </>
      ) : null}

      <div className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-base font-semibold">{agent.displayName}</p>
            <p className="mt-1 text-sm text-muted-foreground">{agent.description}</p>
          </div>
          <span className="w-fit rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-950 dark:border-blue-900/60 dark:bg-blue-950/35 dark:text-blue-200">
            {agent.workflowLabel}
          </span>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <div className="rounded-md border border-border bg-muted/40 p-3 sm:col-span-2">
            <p className="text-xs font-medium uppercase text-muted-foreground">Active prompt</p>
            <p className="mt-1 truncate text-sm font-medium">
              {setting.active_prompt_name ?? "Globally active prompt"}
            </p>
          </div>
          <div className="rounded-md border border-border bg-muted/40 p-3">
            <p className="text-xs font-medium uppercase text-muted-foreground">Model</p>
            <p className="mt-1 truncate text-sm font-medium">{setting.model}</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md border border-border bg-muted/40 p-3">
              <p className="text-xs font-medium uppercase text-muted-foreground">Tokens</p>
              <p className="mt-1 text-sm font-medium">{setting.max_tokens}</p>
            </div>
            <div className="rounded-md border border-border bg-muted/40 p-3">
              <p className="text-xs font-medium uppercase text-muted-foreground">Retries</p>
              <p className="mt-1 text-sm font-medium">{setting.max_retries}</p>
            </div>
          </div>
        </div>
      </div>

      <details className="group border-t border-border">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-muted-foreground hover:bg-muted/40">
          <span className="inline-flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            Edit settings
          </span>
          <span className="text-xs uppercase group-open:hidden">Open</span>
          <span className="hidden text-xs uppercase group-open:inline">Close</span>
        </summary>

        <div className="space-y-5 border-t border-border bg-muted/20 p-4">
          <Field label="Active prompt version">
            <select
              name="active_prompt_version_id"
              defaultValue={setting.active_prompt_version_id ?? ""}
              className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/35"
            >
              <option value="">Use globally active prompt for this agent</option>
              {promptOptions.map((prompt) => (
                <option key={prompt.id} value={prompt.id}>
                  {prompt.name} v{prompt.version}
                  {prompt.is_active ? " (active)" : ""}
                </option>
              ))}
            </select>
          </Field>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <Field label="Model">
              <input
                name="model"
                defaultValue={setting.model}
                className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/35"
              />
            </Field>
            <Field label="Temperature">
              <input
                name="temperature"
                type="number"
                step="0.1"
                min="0"
                max="2"
                defaultValue={setting.temperature ?? ""}
                placeholder="Default"
                className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/35"
              />
            </Field>
            <Field label="Max tokens">
              <input
                name="max_tokens"
                type="number"
                min="1"
                defaultValue={setting.max_tokens}
                className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/35"
              />
            </Field>
            <Field label="Timeout seconds">
              <input
                name="timeout_seconds"
                type="number"
                min="1"
                defaultValue={setting.timeout_seconds ?? ""}
                placeholder="Default"
                className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/35"
              />
            </Field>
            <Field label="Max retries">
              <input
                name="max_retries"
                type="number"
                min="0"
                defaultValue={setting.max_retries}
                className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/35"
              />
            </Field>
          </div>

          {showApprovalThresholds ? (
            <div className="rounded-lg border border-blue-200 bg-blue-50/70 p-4 dark:border-blue-900/60 dark:bg-blue-950/25">
              <p className="text-sm font-semibold text-blue-950 dark:text-blue-100">Approval policy</p>
              <p className="mt-1 text-sm text-blue-950/70 dark:text-blue-100/70">
                Reviewer thresholds control when output proceeds automatically or pauses for human review.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <Field label="Reviewer approval threshold">
                  <input
                    name="reviewer_approval_threshold"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    defaultValue={setting.reviewer_approval_threshold ?? ""}
                    placeholder={formatOptionalNumber(setting.reviewer_approval_threshold)}
                    className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/35"
                  />
                </Field>
                <Field label="Human approval threshold">
                  <input
                    name="human_approval_threshold"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    defaultValue={setting.human_approval_threshold ?? ""}
                    placeholder={formatOptionalNumber(setting.human_approval_threshold)}
                    className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/35"
                  />
                </Field>
              </div>
            </div>
          ) : null}

          <div className="flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              {state.error ? (
                <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {state.error}
                </p>
              ) : null}
              {state.updatedAgent === setting.agent_type ? (
                <p className="text-sm text-muted-foreground">Saved.</p>
              ) : null}
            </div>
            <button
              type="submit"
              disabled={pending}
              className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pending ? "Saving..." : "Save settings"}
            </button>
          </div>
        </div>
      </details>
    </form>
  );
}
