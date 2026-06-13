import { PlusCircle } from "lucide-react";
import Link from "next/link";
import { listWorkflowRuns } from "@/lib/api";
import type { WorkflowRun } from "@/lib/types";
import { WorkflowRunsTable } from "./workflow-runs-table";

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
        <WorkflowRunsTable runs={runs} />
      )}
    </div>
  );
}
