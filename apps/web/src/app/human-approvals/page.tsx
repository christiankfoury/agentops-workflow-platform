import Link from "next/link";
import { getWorkflowRun, listHumanApprovals } from "@/lib/api";

export default async function HumanApprovalsPage() {
  const approvals = await listHumanApprovals();
  const runEntries = await Promise.all(
    approvals.map(async (approval) => [
      approval.workflow_run_id,
      await getWorkflowRun(approval.workflow_run_id),
    ] as const),
  );
  const runsById = new Map(runEntries);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Human Approvals</h1>
        <Link
          href="/workflow-runs"
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent"
        >
          Workflow Runs
        </Link>
      </div>

      {approvals.length === 0 ? (
        <p className="mt-12 text-center text-muted-foreground">
          No human approvals yet.
        </p>
      ) : (
        <div className="mt-6 overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">ID</th>
                <th className="px-4 py-3 text-left font-medium">Workflow</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Score</th>
                <th className="px-4 py-3 text-left font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {approvals.map((approval) => {
                const run = runsById.get(approval.workflow_run_id);
                return (
                  <tr key={approval.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3">
                      <Link
                        href={`/human-approvals/${approval.id}`}
                        className="font-mono text-xs text-primary underline hover:opacity-80"
                      >
                        {approval.id.slice(0, 8)}...
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {run?.workflow_type ?? "Unknown"}
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                        {approval.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {approval.reviewer_score ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(approval.created_at).toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
