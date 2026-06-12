import Link from "next/link";
import { listAgentSteps, listWorkflowRuns } from "@/lib/api";
import type { AgentStep, WorkflowRun, WorkflowType } from "@/lib/types";

type RunWithSteps = {
  run: WorkflowRun;
  steps: AgentStep[];
  stepLoadFailed: boolean;
};

type NamedTotal = {
  name: string;
  cost: number;
  tokens: number;
};

const moneyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 6,
  maximumFractionDigits: 6,
});
const stepFetchConcurrency = 8;

function formatCost(value: number): string {
  return moneyFormatter.format(value);
}

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function getStepCost(step: AgentStep): number {
  return step.cost ?? 0;
}

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

async function getRunWithSteps(): Promise<RunWithSteps[]> {
  const runs = await listWorkflowRuns();
  return mapWithConcurrency(runs, stepFetchConcurrency, async (run) => {
    try {
      return {
        run,
        steps: await listAgentSteps(run.id),
        stepLoadFailed: false,
      };
    } catch {
      return {
        run,
        steps: [],
        stepLoadFailed: true,
      };
    }
  });
}

function groupCostByWorkflowType(runs: WorkflowRun[]): NamedTotal[] {
  const totals = new Map<WorkflowType, NamedTotal>();
  for (const run of runs) {
    const current = totals.get(run.workflow_type) ?? {
      name: run.workflow_type,
      cost: 0,
      tokens: 0,
    };
    current.cost += run.total_cost ?? 0;
    current.tokens += run.total_tokens ?? 0;
    totals.set(run.workflow_type, current);
  }
  return [...totals.values()].sort((left, right) => right.cost - left.cost);
}

function groupCostByAgent(items: RunWithSteps[]): NamedTotal[] {
  const totals = new Map<string, NamedTotal>();
  for (const item of items) {
    for (const step of item.steps) {
      const current = totals.get(step.agent_type) ?? {
        name: step.agent_type,
        cost: 0,
        tokens: 0,
      };
      current.cost += getStepCost(step);
      current.tokens += step.total_tokens ?? 0;
      totals.set(step.agent_type, current);
    }
  }
  return [...totals.values()].sort((left, right) => right.cost - left.cost);
}

function groupCostByDate(runs: WorkflowRun[]): NamedTotal[] {
  const totals = new Map<string, NamedTotal>();
  for (const run of runs) {
    const date = new Date(run.created_at).toLocaleDateString();
    const current = totals.get(date) ?? { name: date, cost: 0, tokens: 0 };
    current.cost += run.total_cost ?? 0;
    current.tokens += run.total_tokens ?? 0;
    totals.set(date, current);
  }
  return [...totals.values()].sort((left, right) => left.name.localeCompare(right.name));
}

function getAverageRetryCost(items: RunWithSteps[]): number {
  const retrySteps = items.flatMap((item) =>
    item.steps.filter((step) => step.retry_count > 0 && getStepCost(step) > 0),
  );
  if (retrySteps.length === 0) return 0;
  return retrySteps.reduce((total, step) => total + getStepCost(step), 0) / retrySteps.length;
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function CostBars({ title, rows }: { title: string; rows: NamedTotal[] }) {
  const maxCost = Math.max(...rows.map((row) => row.cost), 0);

  return (
    <section>
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-3 space-y-3">
        {rows.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No cost data recorded yet.
          </p>
        ) : (
          rows.map((row) => {
            const width = maxCost > 0 ? Math.max((row.cost / maxCost) * 100, 2) : 2;
            return (
              <div key={row.name}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium">{row.name}</span>
                  <span className="text-muted-foreground">{formatCost(row.cost)}</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary"
                    style={{ width: `${width}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatNumber(row.tokens)} tokens
                </p>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

function TokenBars({ title, rows }: { title: string; rows: NamedTotal[] }) {
  const maxTokens = Math.max(...rows.map((row) => row.tokens), 0);

  return (
    <section>
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-3 space-y-3">
        {rows.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No token data recorded yet.
          </p>
        ) : (
          rows.map((row) => {
            const width =
              maxTokens > 0 ? Math.max((row.tokens / maxTokens) * 100, 2) : 2;
            return (
              <div key={row.name}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium">{row.name}</span>
                  <span className="text-muted-foreground">
                    {formatNumber(row.tokens)} tokens
                  </span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary"
                    style={{ width: `${width}%` }}
                  />
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

function MostExpensiveRuns({ runs }: { runs: WorkflowRun[] }) {
  const rows = runs
    .filter((run) => (run.total_cost ?? 0) > 0)
    .sort((left, right) => (right.total_cost ?? 0) - (left.total_cost ?? 0))
    .slice(0, 5);

  return (
    <section>
      <h2 className="text-lg font-semibold">Most Expensive Runs</h2>
      <div className="mt-3 overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Run</th>
              <th className="px-4 py-3 text-left font-medium">Type</th>
              <th className="px-4 py-3 text-left font-medium">Cost</th>
              <th className="px-4 py-3 text-left font-medium">Tokens</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-muted-foreground" colSpan={4}>
                  No costed workflow runs yet.
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
                  <td className="px-4 py-3 text-muted-foreground">
                    {run.workflow_type}
                  </td>
                  <td className="px-4 py-3">{formatCost(run.total_cost ?? 0)}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatNumber(run.total_tokens ?? 0)}
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

export default async function CostDashboardPage() {
  let items: RunWithSteps[] = [];
  let apiError = false;
  try {
    items = await getRunWithSteps();
  } catch {
    apiError = true;
  }

  const runs = items.map((item) => item.run);
  const steps = items.flatMap((item) => item.steps);
  const failedStepLoads = items.filter((item) => item.stepLoadFailed).length;
  const totalSpend = runs.reduce((total, run) => total + (run.total_cost ?? 0), 0);
  const averageCost = runs.length > 0 ? totalSpend / runs.length : 0;
  const totalTokens = runs.reduce((total, run) => total + (run.total_tokens ?? 0), 0);
  const retryCost = getAverageRetryCost(items);
  const costByWorkflowType = groupCostByWorkflowType(runs);
  const costByAgent = groupCostByAgent(items);
  const costOverTime = groupCostByDate(runs);

  return (
    <div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Cost Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Estimated spend, token usage, and retry cost across workflow runs.
          </p>
        </div>
        <Link
          href="/workflow-runs"
          className="w-fit rounded-md border border-border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted"
        >
          View Runs
        </Link>
      </div>

      {apiError && (
        <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          Cost data is unavailable because the API did not respond.
        </p>
      )}

      {failedStepLoads > 0 && (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          Agent-step costs are partially loaded. {formatNumber(failedStepLoads)} run
          {failedStepLoads === 1 ? "" : "s"} could not load step details before the
          request timed out.
        </p>
      )}

      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Total Spend" value={formatCost(totalSpend)} />
        <MetricCard label="Average Cost / Workflow" value={formatCost(averageCost)} />
        <MetricCard label="Average Retry Cost" value={formatCost(retryCost)} />
        <MetricCard label="Total Tokens" value={formatNumber(totalTokens)} />
      </section>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <CostBars title="Cost by Workflow Type" rows={costByWorkflowType} />
        <CostBars title="Cost by Agent" rows={costByAgent} />
        <CostBars title="Cost Over Time" rows={costOverTime} />
        <TokenBars title="Tokens by Agent" rows={costByAgent} />
      </div>

      <div className="mt-8">
        <MostExpensiveRuns runs={runs} />
      </div>

      <p className="mt-6 text-xs text-muted-foreground">
        Showing {formatNumber(runs.length)} runs and {formatNumber(steps.length)} agent
        steps with estimated token-based costs
        {failedStepLoads > 0
          ? ` (${formatNumber(failedStepLoads)} run detail loads failed).`
          : "."}
      </p>
    </div>
  );
}
