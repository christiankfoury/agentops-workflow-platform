import Link from "next/link";
import { getAgentPerformanceSummary } from "@/lib/api";
import type { AgentPerformanceSummary } from "@/lib/types";

const moneyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 6,
  maximumFractionDigits: 6,
});

function formatCost(value: number): string {
  return moneyFormatter.format(value);
}

function formatPercent(value: number | null): string {
  if (value === null) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function formatLatency(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
  return `${Math.round(value)}ms`;
}

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function AgentPerformanceTable({ rows }: { rows: AgentPerformanceSummary[] }) {
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold">Agent Metrics</h2>
      <div className="mt-3 overflow-x-auto rounded-lg border border-border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Agent</th>
              <th className="px-4 py-3 text-left font-medium">Steps</th>
              <th className="px-4 py-3 text-left font-medium">Avg Score</th>
              <th className="px-4 py-3 text-left font-medium">Avg Cost</th>
              <th className="px-4 py-3 text-left font-medium">Avg Latency</th>
              <th className="px-4 py-3 text-left font-medium">Failure Rate</th>
              <th className="px-4 py-3 text-left font-medium">Retry Rate</th>
              <th className="px-4 py-3 text-left font-medium">Schema Failures</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-muted-foreground" colSpan={8}>
                  No agent steps have been recorded yet.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.agent_type}>
                  <td className="px-4 py-3">
                    <p className="font-medium">{row.agent_name}</p>
                    <p className="text-xs text-muted-foreground">{row.agent_type}</p>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatNumber(row.step_count)}
                  </td>
                  <td className="px-4 py-3">
                    {formatPercent(row.average_reviewer_score)}
                  </td>
                  <td className="px-4 py-3">{formatCost(row.average_cost)}</td>
                  <td className="px-4 py-3">{formatLatency(row.average_latency_ms)}</td>
                  <td className="px-4 py-3">{formatPercent(row.failure_rate)}</td>
                  <td className="px-4 py-3">{formatPercent(row.retry_rate)}</td>
                  <td className="px-4 py-3">
                    {formatPercent(row.schema_validation_failure_rate)}
                    <span className="ml-1 text-xs text-muted-foreground">
                      ({formatNumber(row.schema_validation_failure_count)})
                    </span>
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

function ReliabilityBars({ rows }: { rows: AgentPerformanceSummary[] }) {
  return (
    <section>
      <h2 className="text-lg font-semibold">Reliability</h2>
      <div className="mt-3 space-y-3">
        {rows.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No reliability data recorded yet.
          </p>
        ) : (
          rows.map((row) => (
            <div key={row.agent_type}>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium">{row.agent_name}</span>
                <span className="text-muted-foreground">
                  {formatPercent(row.failure_rate)} failed
                </span>
              </div>
              <div className="mt-1 grid grid-cols-2 gap-2">
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-destructive"
                    style={{ width: `${Math.max(row.failure_rate * 100, 2)}%` }}
                  />
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary"
                    style={{ width: `${Math.max(row.retry_rate * 100, 2)}%` }}
                  />
                </div>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {formatPercent(row.retry_rate)} retry rate across {formatNumber(row.step_count)} steps
              </p>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function CostLatencyBars({ rows }: { rows: AgentPerformanceSummary[] }) {
  const maxCost = Math.max(...rows.map((row) => row.average_cost), 0);

  return (
    <section>
      <h2 className="text-lg font-semibold">Cost by Agent</h2>
      <div className="mt-3 space-y-3">
        {rows.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No cost data recorded yet.
          </p>
        ) : (
          rows.map((row) => {
            const width =
              maxCost > 0 ? Math.max((row.average_cost / maxCost) * 100, 2) : 2;
            return (
              <div key={row.agent_type}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium">{row.agent_name}</span>
                  <span className="text-muted-foreground">
                    {formatCost(row.average_cost)}
                  </span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary"
                    style={{ width: `${width}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Average latency {formatLatency(row.average_latency_ms)}
                </p>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

export default async function AgentPerformancePage() {
  let rows: AgentPerformanceSummary[] = [];
  let apiError = false;
  try {
    rows = await getAgentPerformanceSummary();
  } catch {
    apiError = true;
  }

  const totalSteps = rows.reduce((total, row) => total + row.step_count, 0);
  const totalFailures = rows.reduce((total, row) => total + row.failed_count, 0);
  const totalRetries = rows.reduce((total, row) => total + row.retry_count, 0);
  const totalSchemaFailures = rows.reduce(
    (total, row) => total + row.schema_validation_failure_count,
    0,
  );
  const averageCost =
    rows.length > 0
      ? rows.reduce((total, row) => total + row.average_cost, 0) / rows.length
      : 0;

  return (
    <div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Agent Performance Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Latency, cost, reliability, retry, reviewer score, and schema guardrail metrics by agent.
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
          Agent performance data is unavailable because the API did not respond.
        </p>
      )}

      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Agent Steps" value={formatNumber(totalSteps)} />
        <MetricCard label="Failure Rate" value={formatPercent(totalFailures / Math.max(totalSteps, 1))} />
        <MetricCard label="Retry Rate" value={formatPercent(totalRetries / Math.max(totalSteps, 1))} />
        <MetricCard label="Avg Agent Cost" value={formatCost(averageCost)} />
      </section>

      <section className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <MetricCard
          label="Schema Validation Failures"
          value={formatNumber(totalSchemaFailures)}
        />
        <MetricCard
          label="Schema Failure Rate"
          value={formatPercent(totalSchemaFailures / Math.max(totalSteps, 1))}
        />
      </section>

      <AgentPerformanceTable rows={rows} />

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <ReliabilityBars rows={rows} />
        <CostLatencyBars rows={rows} />
      </div>
    </div>
  );
}
