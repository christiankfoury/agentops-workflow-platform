import Link from "next/link";
import { getEvaluationComparisons } from "@/lib/api";
import type { EvaluationComparison, EvaluationComparisonRun } from "@/lib/types";

function formatPercent(value: number | null): string {
  if (value === null) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function formatCost(value: number): string {
  return `$${value.toFixed(4)}`;
}

function formatSignedCost(value: number): string {
  const prefix = value >= 0 ? "+" : "-";
  return `${prefix}${formatCost(Math.abs(value))}`;
}

function formatLatency(value: number): string {
  if (value < 1000) return `${Math.round(value)}ms`;
  return `${(value / 1000).toFixed(2)}s`;
}

function formatSignedLatency(value: number): string {
  const prefix = value >= 0 ? "+" : "-";
  return `${prefix}${formatLatency(Math.abs(value))}`;
}

function metricRows(comparison: EvaluationComparison) {
  return [
    {
      label: "Factual Accuracy",
      baseline: formatPercent(comparison.baseline.factual_accuracy),
      multiAgent: formatPercent(comparison.multi_agent.factual_accuracy),
    },
    {
      label: "Unsupported Claims",
      baseline: formatPercent(comparison.baseline.unsupported_claim_rate),
      multiAgent: formatPercent(comparison.multi_agent.unsupported_claim_rate),
    },
    {
      label: "Completeness",
      baseline: formatPercent(comparison.baseline.completeness_score),
      multiAgent: formatPercent(comparison.multi_agent.completeness_score),
    },
    {
      label: "Cost",
      baseline: formatCost(comparison.baseline.cost),
      multiAgent: `${formatCost(comparison.multi_agent.cost)} (${formatSignedCost(
        comparison.cost_difference,
      )})`,
    },
    {
      label: "Latency",
      baseline: formatLatency(comparison.baseline.latency_ms),
      multiAgent: `${formatLatency(comparison.multi_agent.latency_ms)} (${formatSignedLatency(
        comparison.latency_difference_ms,
      )})`,
    },
  ];
}

function formatIssue(issue: Record<string, unknown>): string {
  const claim = typeof issue.claim === "string" ? issue.claim : "Reviewer issue";
  const problem = typeof issue.problem === "string" ? issue.problem : "";
  return problem ? `${claim}: ${problem}` : claim;
}

function OutputPanel({
  title,
  run,
}: {
  title: string;
  run: EvaluationComparisonRun;
}) {
  return (
    <section>
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold">{title}</h3>
        <Link
          href={`/workflow-runs/${run.workflow_run_id}`}
          className="font-mono text-xs text-primary underline hover:opacity-80"
        >
          {run.workflow_run_id.slice(0, 8)}
        </Link>
      </div>
      <div className="mt-3 min-h-48 rounded-lg border border-border bg-card p-4">
        <p className="whitespace-pre-wrap text-sm leading-6">
          {run.final_output || "No final output was stored for this run."}
        </p>
      </div>
    </section>
  );
}

function ComparisonCard({ comparison }: { comparison: EvaluationComparison }) {
  const rows = metricRows(comparison);

  return (
    <section className="border-b border-border pb-8">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs uppercase text-muted-foreground">
            {comparison.workflow_type}
          </p>
          <h2 className="mt-1 text-lg font-semibold">{comparison.title}</h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            {comparison.input_preview}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm lg:min-w-64">
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Cost Delta</p>
            <p className="mt-1 font-semibold">
              {formatSignedCost(comparison.cost_difference)}
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Latency Delta</p>
            <p className="mt-1 font-semibold">
              {formatSignedLatency(comparison.latency_difference_ms)}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 overflow-hidden rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Metric</th>
              <th className="px-4 py-3">Baseline</th>
              <th className="px-4 py-3">Multi-Agent</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-t border-border">
                <td className="px-4 py-3 font-medium">{row.label}</td>
                <td className="px-4 py-3">{row.baseline}</td>
                <td className="px-4 py-3">{row.multiAgent}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <OutputPanel title="Baseline Output" run={comparison.baseline} />
        <OutputPanel title="Multi-Agent Output" run={comparison.multi_agent} />
      </div>

      <section className="mt-5">
        <h3 className="font-semibold">Reviewer Issues</h3>
        {comparison.reviewer_issues.length === 0 ? (
          <p className="mt-2 rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No reviewer issues were recorded for this comparison.
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {comparison.reviewer_issues.map((issue, index) => (
              <li
                key={`${comparison.evaluation_case_id}-${index}`}
                className="rounded-md border border-border p-3 text-sm"
              >
                <p>{formatIssue(issue)}</p>
                {typeof issue.severity === "string" && (
                  <p className="mt-1 text-xs uppercase text-muted-foreground">
                    Severity: {issue.severity}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

export default async function WorkflowComparisonPage() {
  let comparisons: EvaluationComparison[] = [];
  let apiError = false;
  try {
    comparisons = await getEvaluationComparisons();
  } catch {
    apiError = true;
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Workflow Comparison
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Side-by-side baseline vs multi-agent outputs for matched evaluation inputs.
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
          Workflow comparison data is unavailable because the API did not respond.
        </p>
      )}

      {comparisons.length === 0 ? (
        <section className="mt-6 rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
          No paired baseline and multi-agent evaluation runs are available yet.
        </section>
      ) : (
        <div className="mt-6 space-y-6">
          {comparisons.map((comparison) => (
            <ComparisonCard
              key={comparison.evaluation_case_id}
              comparison={comparison}
            />
          ))}
        </div>
      )}
    </div>
  );
}
