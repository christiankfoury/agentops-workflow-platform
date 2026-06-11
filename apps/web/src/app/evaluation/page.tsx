import Link from "next/link";
import { getEvaluationSummary } from "@/lib/api";
import type { EvaluationMetricsSummary, RunMode, WorkflowType } from "@/lib/types";

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

function formatMode(mode: RunMode): string {
  return mode === "multi_agent" ? "Multi-Agent" : "Baseline";
}

function formatWorkflow(type: WorkflowType): string {
  if (type === "customer_feedback") return "Customer Feedback";
  if (type === "incident_log") return "Incident Log";
  return "Sales Report";
}

function findSummary(
  summaries: EvaluationMetricsSummary[],
  workflowType: WorkflowType,
  mode: RunMode,
): EvaluationMetricsSummary | undefined {
  return summaries.find(
    (summary) => summary.workflow_type === workflowType && summary.run_mode === mode,
  );
}

function metricRows(
  baseline: EvaluationMetricsSummary | undefined,
  multiAgent: EvaluationMetricsSummary | undefined,
) {
  return [
    {
      label: "Factual Accuracy",
      baseline: formatPercent(baseline?.factual_accuracy ?? 0),
      multiAgent: formatPercent(multiAgent?.factual_accuracy ?? 0),
    },
    {
      label: "Unsupported Claims",
      baseline: formatPercent(baseline?.unsupported_claim_rate ?? 0),
      multiAgent: formatPercent(multiAgent?.unsupported_claim_rate ?? 0),
    },
    {
      label: "Completeness",
      baseline: formatPercent(baseline?.completeness_score ?? 0),
      multiAgent: formatPercent(multiAgent?.completeness_score ?? 0),
    },
    {
      label: "Router Accuracy",
      baseline: formatPercent(baseline?.router_accuracy ?? 0),
      multiAgent: formatPercent(multiAgent?.router_accuracy ?? 0),
    },
    {
      label: "Router Confidence",
      baseline: formatPercent(baseline?.average_router_confidence ?? 0),
      multiAgent: formatPercent(multiAgent?.average_router_confidence ?? 0),
    },
    {
      label: "Human Approval Rate",
      baseline: formatPercent(baseline?.human_approval_rate ?? 0),
      multiAgent: formatPercent(multiAgent?.human_approval_rate ?? 0),
    },
    {
      label: "Average Retries",
      baseline: (baseline?.average_retries ?? 0).toFixed(2),
      multiAgent: (multiAgent?.average_retries ?? 0).toFixed(2),
    },
    {
      label: "Average Cost",
      baseline: formatCost(baseline?.average_cost ?? 0),
      multiAgent: formatCost(multiAgent?.average_cost ?? 0),
    },
    {
      label: "Average Latency",
      baseline: formatLatency(baseline?.average_latency_ms ?? 0),
      multiAgent: formatLatency(multiAgent?.average_latency_ms ?? 0),
    },
  ];
}

function SummaryCard({ summary }: { summary: EvaluationMetricsSummary }) {
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">{formatMode(summary.run_mode)}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {formatWorkflow(summary.workflow_type)} · {summary.run_count} completed runs
          </p>
        </div>
        <span className="rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium">
          {summary.run_mode}
        </span>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-muted-foreground">Accuracy</dt>
          <dd className="mt-1 font-medium">{formatPercent(summary.factual_accuracy)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Completeness</dt>
          <dd className="mt-1 font-medium">{formatPercent(summary.completeness_score)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Unsupported</dt>
          <dd className="mt-1 font-medium">
            {formatPercent(summary.unsupported_claim_rate)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Avg Cost</dt>
          <dd className="mt-1 font-medium">{formatCost(summary.average_cost)}</dd>
        </div>
      </dl>
    </section>
  );
}

export default async function EvaluationDashboardPage() {
  const summaries = await getEvaluationSummary();
  const workflowTypes = Array.from(
    new Set(summaries.map((summary) => summary.workflow_type)),
  ).sort();

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Evaluation Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Baseline vs multi-agent workflow quality, cost, and latency by workflow type.
          </p>
        </div>
        <Link
          href="/workflow-runs"
          className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
        >
          Workflow Runs
        </Link>
      </div>

      {summaries.every((summary) => summary.run_count === 0) ? (
        <section className="mt-6 rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
          No completed evaluation results are available yet.
        </section>
      ) : (
        <div className="mt-6 space-y-8">
          {workflowTypes.map((workflowType) => {
            const baseline = findSummary(summaries, workflowType, "baseline");
            const multiAgent = findSummary(summaries, workflowType, "multi_agent");
            const rows = metricRows(baseline, multiAgent);
            return (
              <section key={workflowType}>
                <h2 className="text-lg font-semibold">{formatWorkflow(workflowType)}</h2>
                <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
                  {baseline && <SummaryCard summary={baseline} />}
                  {multiAgent && <SummaryCard summary={multiAgent} />}
                </div>

                <div className="mt-4 overflow-hidden rounded-lg border border-border">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-muted text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3">Metric</th>
                        <th className="px-4 py-3 text-right">Baseline</th>
                        <th className="px-4 py-3 text-right">Multi-Agent</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.label} className="border-t border-border">
                          <td className="px-4 py-3 font-medium">{row.label}</td>
                          <td className="px-4 py-3 text-right">{row.baseline}</td>
                          <td className="px-4 py-3 text-right">{row.multiAgent}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
