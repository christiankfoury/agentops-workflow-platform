"use client";

import { Sparkles } from "lucide-react";
import { useActionState } from "react";
import { createWorkflow } from "./actions";

const initialState = { error: null };

export function NewWorkflowForm() {
  const [state, formAction, pending] = useActionState(
    createWorkflow,
    initialState,
  );

  return (
    <form action={formAction} className="mt-6 space-y-5">
      <div>
        <label htmlFor="title" className="block text-sm font-medium">
          Input Title
        </label>
        <input
          id="title"
          name="title"
          type="text"
          required
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Q1 Sales Report"
        />
      </div>

      <div>
        <label htmlFor="raw_text" className="block text-sm font-medium">
          Input Text
        </label>
        <textarea
          id="raw_text"
          name="raw_text"
          rows={10}
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Paste a sales report, customer feedback, or incident log..."
        />
      </div>

      <div>
        <label htmlFor="input_file" className="block text-sm font-medium">
          Upload Text File
        </label>
        <input
          id="input_file"
          name="input_file"
          type="file"
          accept=".txt,.md,.csv,text/plain,text/markdown,text/csv"
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-1.5 file:text-sm"
        />
      </div>

      <div>
        <label htmlFor="notes" className="block text-sm font-medium">
          Notes
        </label>
        <textarea
          id="notes"
          name="notes"
          rows={3}
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Optional context for this run"
        />
      </div>

      <div>
        <label htmlFor="workflow_type" className="block text-sm font-medium">
          Workflow Type
        </label>
        <select
          id="workflow_type"
          name="workflow_type"
          required
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="sales_report">Sales Report</option>
          <option value="customer_feedback">Customer Feedback</option>
          <option value="incident_log">Incident Log</option>
        </select>
      </div>

      <label className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm">
        <input
          type="checkbox"
          name="auto_detect_workflow"
          className="h-4 w-4 rounded border-input"
        />
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        <span>Auto-detect workflow type</span>
      </label>

      <div>
        <label htmlFor="run_mode" className="block text-sm font-medium">
          Run Mode
        </label>
        <select
          id="run_mode"
          name="run_mode"
          required
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="multi_agent">Multi-Agent</option>
          <option value="baseline">Baseline</option>
        </select>
      </div>

      {state.error && (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {state.error}
        </p>
      )}

      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Creating..." : "Create Workflow Run"}
      </button>
    </form>
  );
}
