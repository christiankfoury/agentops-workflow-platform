"use client";

import { useActionState } from "react";
import { agentDisplayConfigs } from "@/lib/agent-display";
import { createPromptVersionAction } from "./actions";

const initialState = { error: null };

export function PromptVersionForm() {
  const [state, formAction, pending] = useActionState(
    createPromptVersionAction,
    initialState,
  );

  return (
    <form action={formAction} className="mt-5 space-y-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <label htmlFor="agent_type" className="block text-sm font-medium">
            Agent
          </label>
          <select id="agent_type" name="agent_type" className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/35">
            {agentDisplayConfigs.map((config) => (
              <option key={config.agentType} value={config.agentType}>
                {config.displayName} - {config.workflowLabel}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="name" className="block text-sm font-medium">Name</label>
          <input id="name" name="name" className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/35" />
        </div>
        <div>
          <label htmlFor="version" className="block text-sm font-medium">Version</label>
          <input id="version" name="version" type="number" min="1" className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/35" />
        </div>
      </div>
      <div>
        <label htmlFor="template" className="block text-sm font-medium">Template</label>
        <textarea id="template" name="template" rows={6} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-ring/35" />
      </div>
      <div>
        <label htmlFor="notes" className="block text-sm font-medium">Notes</label>
        <textarea id="notes" name="notes" rows={2} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-ring/35" />
      </div>
      <label className="flex w-fit items-center gap-2 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm">
        <input name="is_active" type="checkbox" className="h-4 w-4 rounded border-input" />
        Activate after creation
      </label>
      {state.error && <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{state.error}</p>}
      <button type="submit" disabled={pending} className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60">
        {pending ? "Creating..." : "Create Prompt Version"}
      </button>
    </form>
  );
}
