import { redirect } from "next/navigation";
import { createWorkflowRun } from "@/lib/api";
import type { RunMode, WorkflowType } from "@/lib/types";

async function handleCreate(formData: FormData) {
  "use server";

  const run = await createWorkflowRun({
    workflow_type: formData.get("workflow_type") as WorkflowType,
    run_mode: formData.get("run_mode") as RunMode,
  });

  redirect(`/workflow-runs/${run.id}`);
}

export default function NewWorkflowPage() {
  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold tracking-tight">New Workflow Run</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Create a placeholder workflow run without executing agents.
      </p>

      <form action={handleCreate} className="mt-6 space-y-4">
        <div>
          <label
            htmlFor="workflow_type"
            className="block text-sm font-medium"
          >
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

        <button
          type="submit"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Create Workflow Run
        </button>
      </form>
    </div>
  );
}
