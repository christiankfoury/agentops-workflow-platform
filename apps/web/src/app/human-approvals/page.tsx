import Link from "next/link";
import { getWorkflowRun, listHumanApprovals } from "@/lib/api";
import type { HumanApproval, WorkflowRun } from "@/lib/types";
import {
  HumanApprovalsTable,
  type HumanApprovalTableRow,
} from "./human-approvals-table";

const runFetchConcurrency = 6;

async function mapWithConcurrency<T, R>(
  items: T[],
  concurrency: number,
  mapper: (item: T) => Promise<R>,
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let nextIndex = 0;

  async function worker() {
    while (nextIndex < items.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      results[currentIndex] = await mapper(items[currentIndex]);
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, () => worker()),
  );
  return results;
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
  const runIds = Array.from(new Set(approvals.map((approval) => approval.workflow_run_id)));
  const entries = await mapWithConcurrency(
    runIds,
    runFetchConcurrency,
    async (workflowRunId) => {
      const run = await getWorkflowRun(workflowRunId).catch(() => null);
      return [workflowRunId, run] as const;
    },
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
  const approvalRows: HumanApprovalTableRow[] = approvals.map((approval) => {
    const run = runsById.get(approval.workflow_run_id);
    return {
      approval,
      displayStatus: approvalDisplayStatus(approval, run),
      run: run ?? null,
    };
  });

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
        <HumanApprovalsTable rows={approvalRows} />
      )}
    </div>
  );
}
