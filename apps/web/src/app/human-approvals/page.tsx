import Link from "next/link";
import { LocalDateTime } from "@/components/local-date-time";
import { getWorkflowRun, listHumanApprovals } from "@/lib/api";
import type { HumanApproval, WorkflowRun } from "@/lib/types";

function statusClass(status: string): string {
  if (status === "blocked") {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300";
  }
  if (status === "approved") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300";
  }
  if (status === "rejected") {
    return "border-destructive/30 bg-destructive/10 text-destructive";
  }
  if (status === "retry_requested") {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300";
  }
  return "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300";
}

function formatWorkflow(value: string | undefined): string {
  if (value === "customer_feedback") return "Customer Feedback";
  if (value === "incident_log") return "Incident Log";
  if (value === "sales_report") return "Sales Report";
  return "Unknown";
}

function scoreLabel(value: number | null): string {
  if (value == null) return "-";
  return `${Math.round(value * 100)}%`;
}

function approvalDisplayStatus(
  approval: HumanApproval,
  run: WorkflowRun | undefined,
): string {
  if (
    approval.status === "pending" &&
    run !== undefined &&
    run.status !== "waiting_for_human"
  ) {
    return "blocked";
  }
  return approval.status;
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

async function loadRunsById(approvals: HumanApproval[]): Promise<Map<string, WorkflowRun>> {
  const entries = await Promise.all(
    approvals.map(async (approval) => {
      const run = await getWorkflowRun(approval.workflow_run_id).catch(() => null);
      return [approval.workflow_run_id, run] as const;
    }),
  );
  return new Map(
    entries.filter((entry): entry is readonly [string, WorkflowRun] => entry[1] !== null),
  );
}

export default async function HumanApprovalsPage() {
  let approvals: HumanApproval[] = [];
  let runsById = new Map<string, WorkflowRun>();
  let apiError = false;

  try {
    approvals = await listHumanApprovals();
    runsById = await loadRunsById(approvals);
  } catch {
    apiError = true;
  }

  const actionablePendingCount = approvals.filter((approval) => {
    const run = runsById.get(approval.workflow_run_id);
    return approval.status === "pending" && run?.status === "waiting_for_human";
  }).length;
  const blockedCount = approvals.filter((approval) => {
    const run = runsById.get(approval.workflow_run_id);
    return (
      approval.status === "pending" &&
      run !== undefined &&
      run.status !== "waiting_for_human"
    );
  }).length;
  const resolvedCount = approvals.length - actionablePendingCount - blockedCount;
  const editedCount = approvals.filter((approval) => approval.edited_analysis_json).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Human Approvals</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Review gates for agent outputs that need approval, retries, rejection,
            or structured human edits.
          </p>
        </div>
        <Link
          href="/workflow-runs"
          className="w-fit rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
        >
          Workflow Runs
        </Link>
      </div>

      {apiError && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          Human approval data is unavailable because the API did not respond.
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard label="Total" value={String(approvals.length)} />
        <SummaryCard label="Pending" value={String(actionablePendingCount)} />
        <SummaryCard label="Resolved" value={String(resolvedCount)} />
        <SummaryCard label="Blocked" value={String(blockedCount)} />
      </section>

      {approvals.length === 0 ? (
        <section className="rounded-lg border border-dashed border-border p-8">
          <h2 className="text-lg font-semibold">No human approvals yet</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Approvals appear when a reviewer pauses a workflow for human review.
            Run a multi-agent demo workflow to generate review decisions.
          </p>
          <Link
            href="/demo"
            className="mt-4 inline-flex rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
          >
            Open Demo Mode
          </Link>
        </section>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Approval</th>
                <th className="px-4 py-3 text-left font-medium">Workflow</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Score</th>
                <th className="px-4 py-3 text-left font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {approvals.map((approval) => {
                const run = runsById.get(approval.workflow_run_id);
                const displayStatus = approvalDisplayStatus(approval, run);
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
                    <td className="px-4 py-3 font-medium">
                      {formatWorkflow(run?.workflow_type)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusClass(
                          displayStatus,
                        )}`}
                      >
                        {displayStatus}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {scoreLabel(approval.reviewer_score)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <LocalDateTime value={approval.created_at} />
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
