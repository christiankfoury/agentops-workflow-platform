import { PlusCircle } from "lucide-react";
import Link from "next/link";
import { listWorkflowRuns } from "@/lib/api";
import type { WorkflowRun } from "@/lib/types";

function formatWorkflow(value: string): string {
  if (value === "customer_feedback") return "Customer Feedback";
  if (value === "incident_log") return "Incident Log";
  return "Sales Report";
}

function formatMode(value: string): string {
  return value === "multi_agent" ? "Multi-Agent" : "Baseline";
}

function statusClass(status: string): string {
  if (status === "completed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300";
  }
  if (status === "failed" || status === "cancelled") {
    return "border-destructive/30 bg-destructive/10 text-destructive";
  }
  if (status === "waiting_for_human" || status === "retrying") {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300";
  }
  return "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300";
}

function countRuns(runs: WorkflowRun[], statuses: string[]): number {
  return runs.filter((run) => statuses.includes(run.status)).length;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

export default async function WorkflowRunsPage() {
  let runs: WorkflowRun[] = [];
  let apiError = false;

  try {
    runs = await listWorkflowRuns();
  } catch {
    apiError = true;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Workflow Runs</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track each workflow from uploaded input through agent trace, review,
            approval, and final output.
          </p>
        </div>
        <Link
          href="/workflow-runs/new"
          className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <PlusCircle className="h-4 w-4" aria-hidden="true" />
          New Workflow
        </Link>
      </div>

      {apiError && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          Workflow runs are unavailable because the API did not respond.
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard label="Total" value={String(runs.length)} />
        <SummaryCard
          label="Active"
          value={String(
            countRuns(runs, [
              "created",
              "running",
              "reviewer_running",
              "writer_running",
              "retrying",
            ]),
          )}
        />
        <SummaryCard
          label="Waiting"
          value={String(countRuns(runs, ["waiting_for_human"]))}
        />
        <SummaryCard
          label="Completed"
          value={String(countRuns(runs, ["completed"]))}
        />
      </section>

      {runs.length === 0 ? (
        <section className="rounded-lg border border-dashed border-border p-8">
          <h2 className="text-lg font-semibold">No workflow runs yet</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Create a workflow manually or seed demo data to inspect agent steps,
            review events, costs, and final outputs.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/workflow-runs/new"
              className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Create Workflow
            </Link>
            <Link
              href="/demo"
              className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
            >
              Open Demo Mode
            </Link>
          </div>
        </section>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Run</th>
                <th className="px-4 py-3 text-left font-medium">Workflow</th>
                <th className="px-4 py-3 text-left font-medium">Mode</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {runs.map((run) => (
                <tr key={run.id} className="hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/workflow-runs/${run.id}`}
                      className="font-mono text-xs text-primary underline hover:opacity-80"
                    >
                      {run.id.slice(0, 8)}...
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-medium">
                    {formatWorkflow(run.workflow_type)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatMode(run.run_mode)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusClass(
                        run.status,
                      )}`}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(run.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
