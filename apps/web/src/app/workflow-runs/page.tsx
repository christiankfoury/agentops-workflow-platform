import Link from "next/link";
import { listWorkflowRuns } from "@/lib/api";

export default async function WorkflowRunsPage() {
  const runs = await listWorkflowRuns();

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Workflow Runs</h1>
        <Link
          href="/workflow-runs/new"
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          New Workflow
        </Link>
      </div>

      {runs.length === 0 ? (
        <p className="mt-12 text-center text-muted-foreground">
          No workflow runs yet.{" "}
          <Link
            href="/workflow-runs/new"
            className="underline hover:text-foreground"
          >
            Create one.
          </Link>
        </p>
      ) : (
        <div className="mt-6 overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">ID</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
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
                      {run.id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {run.workflow_type}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {run.run_mode}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
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
