import Link from "next/link";
import { listEvaluationResults } from "@/lib/api";
import type { EvaluationResult } from "@/lib/types";

type TrendPoint = {
  sortDate: string;
  date: string;
  runCount: number;
  factualAccuracy: number;
  unsupportedClaimRate: number;
  completenessScore: number;
  humanApprovalRate: number;
  averageCost: number;
  averageLatencyMs: number;
};

function average(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatCost(value: number): string {
  return `$${value.toFixed(4)}`;
}

function formatLatency(value: number): string {
  if (value < 1000) return `${Math.round(value)}ms`;
  return `${(value / 1000).toFixed(2)}s`;
}

function buildTrend(results: EvaluationResult[]): TrendPoint[] {
  const completed = results.filter((result) => result.status === "completed");
  const grouped = new Map<string, EvaluationResult[]>();
  for (const result of completed) {
    const sortDate = new Date(result.created_at).toISOString().slice(0, 10);
    grouped.set(sortDate, [...(grouped.get(sortDate) ?? []), result]);
  }

  return [...grouped.entries()]
    .map(([sortDate, items]) => {
      const approvals = items.filter((item) => item.human_approval_required);
      const approved = approvals.filter((item) => item.human_approved);
      return {
        sortDate,
        date: new Date(`${sortDate}T00:00:00`).toLocaleDateString(),
        runCount: items.length,
        factualAccuracy: average(
          items.flatMap((item) => (item.factual_accuracy === null ? [] : [item.factual_accuracy])),
        ),
        unsupportedClaimRate: average(
          items.flatMap((item) =>
            item.unsupported_claim_rate === null ? [] : [item.unsupported_claim_rate],
          ),
        ),
        completenessScore: average(
          items.flatMap((item) =>
            item.completeness_score === null ? [] : [item.completeness_score],
          ),
        ),
        humanApprovalRate: approvals.length > 0 ? approved.length / approvals.length : 0,
        averageCost: average(items.flatMap((item) => (item.cost === null ? [] : [item.cost]))),
        averageLatencyMs: average(
          items.flatMap((item) => (item.latency_ms === null ? [] : [item.latency_ms])),
        ),
      };
    })
    .sort((left, right) => left.sortDate.localeCompare(right.sortDate));
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function TrendTable({ rows }: { rows: TrendPoint[] }) {
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold">Evaluation Trends</h2>
      <div className="mt-3 overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Date</th>
              <th className="px-4 py-3 text-left font-medium">Runs</th>
              <th className="px-4 py-3 text-left font-medium">Accuracy</th>
              <th className="px-4 py-3 text-left font-medium">Unsupported</th>
              <th className="px-4 py-3 text-left font-medium">Completeness</th>
              <th className="px-4 py-3 text-left font-medium">Approval</th>
              <th className="px-4 py-3 text-left font-medium">Cost</th>
              <th className="px-4 py-3 text-left font-medium">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-muted-foreground" colSpan={8}>
                  No completed evaluation results are available yet.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.sortDate}>
                  <td className="px-4 py-3 font-medium">{row.date}</td>
                  <td className="px-4 py-3 text-muted-foreground">{row.runCount}</td>
                  <td className="px-4 py-3">{formatPercent(row.factualAccuracy)}</td>
                  <td className="px-4 py-3">{formatPercent(row.unsupportedClaimRate)}</td>
                  <td className="px-4 py-3">{formatPercent(row.completenessScore)}</td>
                  <td className="px-4 py-3">{formatPercent(row.humanApprovalRate)}</td>
                  <td className="px-4 py-3">{formatCost(row.averageCost)}</td>
                  <td className="px-4 py-3">{formatLatency(row.averageLatencyMs)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default async function ImprovementTrackingPage() {
  let results: EvaluationResult[] = [];
  let apiError = false;
  try {
    results = await listEvaluationResults();
  } catch {
    apiError = true;
  }

  const trend = buildTrend(results);
  const latest = trend.at(-1);

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Improvement Tracking</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Evaluation quality, cost, latency, and human approval trends over time.
          </p>
        </div>
        <Link
          href="/evaluation"
          className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
        >
          Evaluation Dashboard
        </Link>
      </div>

      {apiError && (
        <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          Improvement data is unavailable because the API did not respond.
        </p>
      )}

      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Trend Days" value={trend.length.toLocaleString()} />
        <MetricCard
          label="Latest Accuracy"
          value={latest ? formatPercent(latest.factualAccuracy) : "n/a"}
        />
        <MetricCard
          label="Latest Unsupported"
          value={latest ? formatPercent(latest.unsupportedClaimRate) : "n/a"}
        />
        <MetricCard
          label="Latest Avg Cost"
          value={latest ? formatCost(latest.averageCost) : "n/a"}
        />
      </section>

      <TrendTable rows={trend} />
    </div>
  );
}
