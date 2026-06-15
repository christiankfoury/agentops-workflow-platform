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

const preciseMoneyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 6,
  maximumFractionDigits: 6,
});
const readableMoneyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const chartMoneyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});
const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});
const stepFetchConcurrency = 8;
const costOverTimeLimit = 10;

function formatCost(
  value: number,
  precision: "chart" | "readable" | "precise" = "precise",
): string {
  if (precision === "readable") return readableMoneyFormatter.format(value);
  if (precision === "chart") return chartMoneyFormatter.format(value);
  return preciseMoneyFormatter.format(value);
}

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function getStepCost(step: AgentStep): number {
  return step.cost ?? 0;
}

function formatWorkflow(value: string): string {
  if (value === "customer_feedback") return "Customer feedback";
  if (value === "incident_log") return "Incident log";
  if (value === "sales_report") return "Sales report";
  return value.replaceAll("_", " ");
}

function formatAgent(value: string): string {
  const labels: Record<string, string> = {
    analyst: "Analyst",
    baseline: "Baseline",
    classifier: "Classifier",
    insight: "Insight agent",
    reviewer: "Reviewer",
    root_cause: "Root cause",
    timeline: "Timeline",
    writer: "Writer",
  };
  return labels[value] ?? value.replaceAll("_", " ");
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
      name: formatWorkflow(run.workflow_type),
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
        name: formatAgent(step.agent_type),
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
  const totals = new Map<string, NamedTotal & { timestamp: number }>();
  for (const run of runs) {
    const date = new Date(run.created_at);
    const dateKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(
      2,
      "0",
    )}-${String(date.getDate()).padStart(2, "0")}`;
    const current = totals.get(dateKey) ?? {
      name: dateFormatter.format(date),
      cost: 0,
      timestamp: date.setHours(0, 0, 0, 0),
      tokens: 0,
    };
    current.cost += run.total_cost ?? 0;
    current.tokens += run.total_tokens ?? 0;
    totals.set(dateKey, current);
  }
  return [...totals.values()]
    .sort((left, right) => left.timestamp - right.timestamp)
    .map(({ timestamp, ...row }) => {
      void timestamp;
      return row;
    });
}

function getAverageRetryCost(items: RunWithSteps[]): number {
  const retrySteps = items.flatMap((item) =>
    item.steps.filter((step) => step.retry_count > 0 && getStepCost(step) > 0),
  );
  if (retrySteps.length === 0) return 0;
  return retrySteps.reduce((total, step) => total + getStepCost(step), 0) / retrySteps.length;
}

function topCostDriver(rows: NamedTotal[]): NamedTotal | null {
  return rows.length > 0 ? rows[0] : null;
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function InsightSummary({
  agent,
  run,
  workflow,
}: {
  agent: NamedTotal | null;
  run: WorkflowRun | null;
  workflow: NamedTotal | null;
}) {
  return (
    <section className="mt-6 rounded-lg border border-border bg-card p-4">
      <h2 className="text-sm font-semibold">Cost Insights</h2>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-md bg-muted p-3">
          <p className="text-xs text-muted-foreground">Top workflow spend</p>
          <p className="mt-1 font-medium">
            {workflow ? `${workflow.name} - ${formatCost(workflow.cost, "readable")}` : "-"}
          </p>
        </div>
        <div className="rounded-md bg-muted p-3">
          <p className="text-xs text-muted-foreground">Top agent cost driver</p>
          <p className="mt-1 font-medium">
            {agent ? `${agent.name} - ${formatCost(agent.cost, "readable")}` : "-"}
          </p>
        </div>
        <div className="rounded-md bg-muted p-3">
          <p className="text-xs text-muted-foreground">Most expensive run</p>
          <p className="mt-1 font-medium">
            {run
              ? `${run.input_title ?? formatWorkflow(run.workflow_type)} - ${formatCost(
                  run.total_cost ?? 0,
                  "readable",
                )}`
              : "-"}
          </p>
        </div>
      </div>
    </section>
  );
}

function CostBars({ title, rows }: { title?: string; rows: NamedTotal[] }) {
  const maxCost = Math.max(...rows.map((row) => row.cost), 0);

  return (
    <section>
      {title && <h2 className="text-lg font-semibold">{title}</h2>}
      <div className={title ? "mt-3 space-y-3" : "space-y-3"}>
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
                  <span className="text-muted-foreground">
                    {formatCost(row.cost, "chart")}
                  </span>
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

function CostOverTime({ rows }: { rows: NamedTotal[] }) {
  const visibleRows = rows.slice(-costOverTimeLimit);
  const hiddenCount = Math.max(rows.length - visibleRows.length, 0);

  return (
    <section>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Recent Cost Over Time</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Latest {visibleRows.length} period{visibleRows.length === 1 ? "" : "s"}.
            {hiddenCount > 0 ? ` ${hiddenCount} older periods hidden to keep the view scannable.` : ""}
          </p>
        </div>
      </div>
      <div className="mt-3">
        <CostBars rows={visibleRows} />
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
      <p className="mt-1 text-sm text-muted-foreground">
        Highest-cost workflow records by stored token-based estimate.
      </p>
      <div className="mt-3 overflow-x-auto rounded-lg border border-border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Workflow input</th>
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
                      className="font-medium text-primary underline hover:opacity-80"
                    >
                      {run.input_title ?? "Untitled workflow input"}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatWorkflow(run.workflow_type)}
                  </td>
                  <td className="px-4 py-3">{formatCost(run.total_cost ?? 0, "readable")}</td>
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
  const mostExpensiveRun =
    runs
      .filter((run) => (run.total_cost ?? 0) > 0)
      .sort((left, right) => (right.total_cost ?? 0) - (left.total_cost ?? 0))[0] ??
    null;

  return (
    <div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Cost Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track estimated spend by workflow, agent, retries, and high-cost
            runs to prove operational observability.
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
        <MetricCard label="Total Spend" value={formatCost(totalSpend, "readable")} />
        <MetricCard
          label="Average Cost / Workflow"
          value={formatCost(averageCost, "readable")}
        />
        <MetricCard
          label="Avg Cost / Retried Step"
          value={formatCost(retryCost, "readable")}
        />
        <MetricCard label="Total Tokens" value={formatNumber(totalTokens)} />
      </section>

      <p className="mt-3 text-xs text-muted-foreground">
        Costs are estimated from stored token and cost metadata. Seeded demo
        records are representative and are not live billing charges.
      </p>

      <InsightSummary
        agent={topCostDriver(costByAgent)}
        run={mostExpensiveRun}
        workflow={topCostDriver(costByWorkflowType)}
      />

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <CostBars title="Cost by Workflow Type" rows={costByWorkflowType} />
        <CostBars title="Cost by Agent" rows={costByAgent} />
        <CostOverTime rows={costOverTime} />
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
