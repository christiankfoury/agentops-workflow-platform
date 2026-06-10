import Link from "next/link";
import { listWorkflowRuns } from "@/lib/api";

export default async function Home() {
  let runCount = 0;
  try {
    const runs = await listWorkflowRuns();
    runCount = runs.length;
  } catch {
    // API may not be running — show 0
  }

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight">
        AgentOps Workflow Platform
      </h1>
      <p className="mt-2 text-muted-foreground">
        Enterprise multi-agent workflow platform.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-6">
          <p className="text-sm text-muted-foreground">Total Workflow Runs</p>
          <p className="mt-1 text-4xl font-bold">{runCount}</p>
        </div>
      </div>

      <div className="mt-8 flex gap-3">
        <Link
          href="/workflow-runs"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          View Runs
        </Link>
        <Link
          href="/workflow-runs/new"
          className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
        >
          New Workflow
        </Link>
      </div>
    </div>
  );
}
