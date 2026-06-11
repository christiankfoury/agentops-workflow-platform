import Link from "next/link";
import { listAgentSteps, listHumanApprovals, listWorkflowRuns } from "@/lib/api";
import type { AgentStep, HumanApproval, WorkflowRun } from "@/lib/types";

type RunWithSteps = {
  run: WorkflowRun;
  steps: AgentStep[];
};

function formatPercent(value: number | null): string {
  if (value === null) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

async function getRunWithSteps(): Promise<RunWithSteps[]> {
  const runs = await listWorkflowRuns();
  return Promise.all(
    runs.map(async (run) => ({
      run,
      steps: await listAgentSteps(run.id).catch(() => []),
    })),
  );
}

function getFailureLabel(step: AgentStep): string {
  if (step.error_message) {
    return step.error_message.split(/[.\n]/)[0] || "Agent failure";
  }
  return `${step.agent_name} failed`;
}

function isSchemaFailure(step: AgentStep): boolean {
  const message = (step.error_message ?? "").toLowerCase();
  return message.includes("schema") || message.includes("validation");
}

function countByLabel(labels: string[]): { label: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const label of labels) counts.set(label, (counts.get(label) ?? 0) + 1);
  return [...counts.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label));
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function LowScoreRuns({ runs }: { runs: WorkflowRun[] }) {
  const rows = runs
    .filter((run) => run.quality_score !== null)
    .sort((left, right) => (left.quality_score ?? 1) - (right.quality_score ?? 1))
    .slice(0, 8);

  return (
    <section>
      <h2 className="text-lg font-semibold">Lowest Scoring Runs</h2>
      <div className="mt-3 overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Run</th>
              <th className="px-4 py-3 text-left font-medium">Workflow</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-left font-medium">Score</th>
              <th className="px-4 py-3 text-left font-medium">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-muted-foreground" colSpan={5}>
                  No scored workflow runs are available yet.
                </td>
              </tr>
            ) : (
              rows.map((run) => (
                <tr key={run.id}>
                  <td className="px-4 py-3">
                    <Link
                      href={`/workflow-runs/${run.id}`}
                      className="font-mono text-xs text-primary underline hover:opacity-80"
                    >
                      {run.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{run.workflow_type}</td>
                  <td className="px-4 py-3">{run.status}</td>
                  <td className="px-4 py-3">{formatPercent(run.quality_score)}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatDate(run.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function FailureList({
  title,
  rows,
  empty,
}: {
  title: string;
  rows: { label: string; count: number }[];
  empty: string;
}) {
  return (
    <section>
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-3 space-y-2">
        {rows.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            {empty}
          </p>
        ) : (
          rows.map((row) => (
            <div
              key={row.label}
              className="flex items-center justify-between gap-3 rounded-md border border-border p-3 text-sm"
            >
              <span>{row.label}</span>
              <span className="rounded-full bg-muted px-2 py-1 text-xs font-medium">
                {row.count}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function RejectedApprovals({ approvals }: { approvals: HumanApproval[] }) {
  const rows = approvals.filter((approval) => approval.status === "rejected").slice(0, 8);

  return (
    <section>
      <h2 className="text-lg font-semibold">Human Rejected Outputs</h2>
      <div className="mt-3 space-y-2">
        {rows.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No human-rejected outputs are recorded yet.
          </p>
        ) : (
          rows.map((approval) => (
            <Link
              key={approval.id}
              href={`/human-approvals/${approval.id}`}
              className="block rounded-md border border-border p-3 text-sm transition-colors hover:bg-muted"
            >
              <span className="font-mono text-xs text-primary">
                {approval.workflow_run_id.slice(0, 8)}
              </span>
              <span className="ml-3 text-muted-foreground">
                {approval.human_feedback || "Rejected without feedback"}
              </span>
            </Link>
          ))
        )}
      </div>
    </section>
  );
}

export default async function FailureCaseExplorerPage() {
  let items: RunWithSteps[] = [];
  let approvals: HumanApproval[] = [];
  let apiError = false;
  try {
    [items, approvals] = await Promise.all([getRunWithSteps(), listHumanApprovals()]);
  } catch {
    apiError = true;
  }

  const runs = items.map((item) => item.run);
  const steps = items.flatMap((item) => item.steps);
  const failedRuns = runs.filter((run) => run.status === "failed");
  const failedSteps = steps.filter((step) => step.status === "failed");
  const schemaFailures = failedSteps.filter(isSchemaFailure);
  const rejectedApprovals = approvals.filter((approval) => approval.status === "rejected");
  const commonFailures = countByLabel(failedSteps.map(getFailureLabel));
  const schemaFailureLabels = countByLabel(schemaFailures.map((step) => step.agent_name));

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Failure Case Explorer</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Low-quality runs, failed workflow steps, schema failures, and human rejected outputs.
          </p>
        </div>
        <Link
          href="/workflow-runs"
          className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
        >
          Workflow Runs
        </Link>
      </div>

      {apiError && (
        <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          Failure case data is unavailable because the API did not respond.
        </p>
      )}

      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Failed Runs" value={failedRuns.length.toLocaleString()} />
        <MetricCard label="Failed Agent Steps" value={failedSteps.length.toLocaleString()} />
        <MetricCard label="Schema Failures" value={schemaFailures.length.toLocaleString()} />
        <MetricCard label="Human Rejections" value={rejectedApprovals.length.toLocaleString()} />
      </section>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <LowScoreRuns runs={runs} />
        <RejectedApprovals approvals={approvals} />
        <FailureList
          title="Common Failure Types"
          rows={commonFailures}
          empty="No agent failures are recorded yet."
        />
        <FailureList
          title="Schema Validation Failures"
          rows={schemaFailureLabels}
          empty="No schema validation failures are recorded yet."
        />
      </div>
    </div>
  );
}
