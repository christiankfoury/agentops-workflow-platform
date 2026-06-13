"use client";

import Link from "next/link";
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import { useActionState, useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import type {
  EvaluationComparison,
  EvaluationComparisonRun,
  RemediationImpact,
  WorkflowType,
} from "@/lib/types";
import { createCorrectedRunAction } from "./actions";

type QuickFilter = "all" | WorkflowType | "needs_review";
type SortKey =
  | "accuracy"
  | "unsupported"
  | "cost"
  | "latency"
  | "title";

const pageSize = 10;

const workflowLabels: Record<WorkflowType, string> = {
  sales_report: "Sales",
  customer_feedback: "Feedback",
  incident_log: "Incidents",
};

const quickFilters: { key: QuickFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "sales_report", label: "Sales" },
  { key: "customer_feedback", label: "Feedback" },
  { key: "incident_log", label: "Incidents" },
  { key: "needs_review", label: "Needs Review" },
];

const sortOptions: { key: SortKey; label: string }[] = [
  { key: "accuracy", label: "Accuracy improvement" },
  { key: "unsupported", label: "Unsupported reduction" },
  { key: "cost", label: "Cost delta" },
  { key: "latency", label: "Latency delta" },
  { key: "title", label: "Title" },
];

function delta(
  baseline: number | null,
  multiAgent: number | null,
): number | null {
  if (baseline === null || multiAgent === null) return null;
  return multiAgent - baseline;
}

function average(values: (number | null)[]): number | null {
  const present = values.filter((value): value is number => value !== null);
  if (present.length === 0) return null;
  return present.reduce((total, value) => total + value, 0) / present.length;
}

function formatPercent(value: number | null): string {
  if (value === null) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function formatPercentDelta(value: number | null): string {
  if (value === null) return "n/a";
  const percentagePoints = Math.round(value * 100);
  const prefix = percentagePoints >= 0 ? "+" : "";
  return `${prefix}${percentagePoints}pp`;
}

function formatQualityDelta(value: number | null): string {
  if (value === null) return "n/a";
  if (value === 0) return "0pp no change";
  return `${formatPercentDelta(value)} ${value > 0 ? "better" : "worse"}`;
}

function formatUnsupportedDelta(value: number | null): string {
  if (value === null) return "n/a";
  if (value === 0) return "0pp no change";
  return `${formatPercentDelta(value)} ${value < 0 ? "better" : "worse"}`;
}

function formatCost(value: number): string {
  return `$${value.toFixed(4)}`;
}

function formatSignedCost(value: number): string {
  const prefix = value >= 0 ? "+" : "-";
  return `${prefix}${formatCost(Math.abs(value))}`;
}

function formatCostDelta(value: number): string {
  if (value === 0) return "$0.0000 no change";
  return `${formatSignedCost(value)} ${value > 0 ? "higher" : "lower"}`;
}

function formatLatency(value: number): string {
  if (value < 1000) return `${Math.round(value)}ms`;
  return `${(value / 1000).toFixed(2)}s`;
}

function formatSignedLatency(value: number): string {
  const prefix = value >= 0 ? "+" : "-";
  return `${prefix}${formatLatency(Math.abs(value))}`;
}

function formatLatencyDelta(value: number): string {
  if (value === 0) return "0ms no change";
  return `${formatSignedLatency(value)} ${value > 0 ? "slower" : "faster"}`;
}

function formatIssueDelta(previous: number, current: number): string {
  return `${previous} to ${current}`;
}

function qualityDirection(value: number | null): boolean | null {
  if (value === null || value === 0) return null;
  return value > 0;
}

function unsupportedDirection(value: number | null): boolean | null {
  if (value === null || value === 0) return null;
  return value < 0;
}

function issueSeverity(issue: Record<string, unknown>): string | null {
  return typeof issue.severity === "string" ? issue.severity.toLowerCase() : null;
}

function hasSeriousReviewerIssue(issues: Record<string, unknown>[]): boolean {
  return issues.some((issue) => {
    const severity = issueSeverity(issue);
    return severity !== "low";
  });
}

function formatIssue(issue: Record<string, unknown>): string {
  const claim = typeof issue.claim === "string" ? issue.claim : "Reviewer issue";
  const problem = typeof issue.problem === "string" ? issue.problem : "";
  return problem ? `${claim}: ${problem}` : claim;
}

function metricRows(comparison: EvaluationComparison) {
  return [
    {
      label: "Factual Accuracy",
      baseline: formatPercent(comparison.baseline.factual_accuracy),
      multiAgent: formatPercent(comparison.multi_agent.factual_accuracy),
      delta: formatPercentDelta(
        delta(
          comparison.baseline.factual_accuracy,
          comparison.multi_agent.factual_accuracy,
        ),
      ),
    },
    {
      label: "Unsupported Claims",
      baseline: formatPercent(comparison.baseline.unsupported_claim_rate),
      multiAgent: formatPercent(comparison.multi_agent.unsupported_claim_rate),
      delta: formatPercentDelta(
        delta(
          comparison.baseline.unsupported_claim_rate,
          comparison.multi_agent.unsupported_claim_rate,
        ),
      ),
    },
    {
      label: "Completeness",
      baseline: formatPercent(comparison.baseline.completeness_score),
      multiAgent: formatPercent(comparison.multi_agent.completeness_score),
      delta: formatPercentDelta(
        delta(
          comparison.baseline.completeness_score,
          comparison.multi_agent.completeness_score,
        ),
      ),
    },
    {
      label: "Cost",
      baseline: formatCost(comparison.baseline.cost),
      multiAgent: formatCost(comparison.multi_agent.cost),
      delta: formatSignedCost(comparison.cost_difference),
    },
    {
      label: "Latency",
      baseline: formatLatency(comparison.baseline.latency_ms),
      multiAgent: formatLatency(comparison.multi_agent.latency_ms),
      delta: formatSignedLatency(comparison.latency_difference_ms),
    },
  ];
}

function comparisonScore(comparison: EvaluationComparison): {
  accuracy: number | null;
  unsupported: number | null;
  completeness: number | null;
} {
  return {
    accuracy: delta(
      comparison.baseline.factual_accuracy,
      comparison.multi_agent.factual_accuracy,
    ),
    unsupported: delta(
      comparison.baseline.unsupported_claim_rate,
      comparison.multi_agent.unsupported_claim_rate,
    ),
    completeness: delta(
      comparison.baseline.completeness_score,
      comparison.multi_agent.completeness_score,
    ),
  };
}

function isMultiAgentBetter(comparison: EvaluationComparison): boolean {
  const scores = comparisonScore(comparison);
  const qualityImproved =
    (scores.accuracy !== null && scores.accuracy > 0) ||
    (scores.completeness !== null && scores.completeness > 0);
  const unsupportedNotWorse = scores.unsupported === null || scores.unsupported <= 0;
  return qualityImproved && unsupportedNotWorse;
}

function severityClasses(severity: string | null): string {
  if (severity === "high") {
    return "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200";
  }
  if (severity === "medium") {
    return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200";
  }
  if (severity === "low") {
    return "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200";
  }
  return "border-border bg-muted text-muted-foreground";
}

function MetricChip({
  label,
  value,
  context,
  positive,
}: {
  label: string;
  value: string;
  context?: string;
  positive?: boolean | null;
}) {
  return (
    <div className="rounded-md border border-border bg-background px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">{label}</p>
        {context && (
          <span className="text-[11px] font-medium text-muted-foreground">
            {context}
          </span>
        )}
      </div>
      <p
        className={cn(
          "mt-1 text-sm font-semibold",
          positive === true && "text-emerald-700 dark:text-emerald-300",
          positive === false && "text-amber-700 dark:text-amber-300",
        )}
      >
        {value}
      </p>
    </div>
  );
}

function Badge({
  children,
  variant = "neutral",
}: {
  children: React.ReactNode;
  variant?: "neutral" | "good" | "warning" | "danger";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium",
        variant === "neutral" && "border-border bg-muted text-muted-foreground",
        variant === "good" &&
          "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200",
        variant === "warning" &&
          "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200",
        variant === "danger" &&
          "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200",
      )}
    >
      {children}
    </span>
  );
}

function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

function RemediationImpactPanel({ impact }: { impact: RemediationImpact }) {
  const unsupportedWorsened =
    impact.unsupported_claim_rate_delta !== null &&
    impact.unsupported_claim_rate_delta > 0;
  const issuesImproved =
    impact.current_reviewer_issue_count < impact.previous_reviewer_issue_count;
  const statusLabel =
    impact.impact_status === "improved"
      ? "Improved"
      : impact.impact_status === "worsened"
        ? "Worsened"
        : "Mixed";
  const statusVariant =
    impact.impact_status === "improved"
      ? "good"
      : impact.impact_status === "worsened"
        ? "danger"
        : "warning";
  const summary =
    impact.impact_status === "improved"
      ? "The corrected run improved the available quality signals versus the previous multi-agent run."
      : impact.impact_status === "worsened"
        ? "The corrected run worsened the available quality signals versus the previous multi-agent run."
        : issuesImproved && unsupportedWorsened
          ? "Reviewer issues improved, but unsupported claims worsened versus the previous multi-agent run."
          : "The corrected run has a mix of improved and worsened signals versus the previous multi-agent run.";

  return (
    <section className="mb-5 rounded-lg border border-border bg-muted/30 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold">Remediation impact</h3>
            <Badge variant={statusVariant}>{statusLabel}</Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{summary}</p>
        </div>
        <div className="flex flex-wrap gap-3 text-xs">
          <Link
            href={`/workflow-runs/${impact.previous_multi_agent_run_id}`}
            className="font-mono text-primary underline hover:opacity-80"
          >
            previous {impact.previous_multi_agent_run_id.slice(0, 8)}
          </Link>
          <Link
            href={`/workflow-runs/${impact.corrected_multi_agent_run_id}`}
            className="font-mono text-primary underline hover:opacity-80"
          >
            corrected {impact.corrected_multi_agent_run_id.slice(0, 8)}
          </Link>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        <MetricChip
          label="Reviewer issues"
          context="vs previous run"
          value={formatIssueDelta(
            impact.previous_reviewer_issue_count,
            impact.current_reviewer_issue_count,
          )}
          positive={
            impact.current_reviewer_issue_count === impact.previous_reviewer_issue_count
              ? null
              : impact.current_reviewer_issue_count < impact.previous_reviewer_issue_count
          }
        />
        <MetricChip
          label="Unsupported"
          context="vs previous run"
          value={formatUnsupportedDelta(impact.unsupported_claim_rate_delta)}
          positive={unsupportedDirection(impact.unsupported_claim_rate_delta)}
        />
        <MetricChip
          label="Accuracy"
          context="vs previous run"
          value={formatQualityDelta(impact.factual_accuracy_delta)}
          positive={qualityDirection(impact.factual_accuracy_delta)}
        />
        <MetricChip
          label="Completeness"
          context="vs previous run"
          value={formatQualityDelta(impact.completeness_score_delta)}
          positive={qualityDirection(impact.completeness_score_delta)}
        />
        <MetricChip
          label="Cost / Latency"
          context="vs previous run"
          value={`${formatSignedCost(impact.cost_delta)} / ${formatSignedLatency(
            impact.latency_delta_ms,
          )}`}
          positive={null}
        />
      </div>
    </section>
  );
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
      <div className="mt-3 max-h-80 overflow-auto rounded-lg border border-border bg-background p-4">
        <p className="whitespace-pre-wrap text-sm leading-6">
          {run.final_output || "No final output was stored for this run."}
        </p>
      </div>
    </section>
  );
}

function CreateCorrectedRunForm({
  evaluationCaseId,
}: {
  evaluationCaseId: string;
}) {
  const [state, formAction, pending] = useActionState(createCorrectedRunAction, {
    error: null,
  });

  return (
    <form action={formAction} className="rounded-lg border border-border bg-muted/40 p-4">
      <input type="hidden" name="evaluation_case_id" value={evaluationCaseId} />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium">Create a corrected multi-agent run</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Uses these reviewer issues as guidance, auto-runs the workflow, and
            updates this comparison.
          </p>
        </div>
        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pending ? "Creating..." : "Create corrected run"}
        </button>
      </div>
      {state.error && (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {state.error}
        </p>
      )}
    </form>
  );
}

function DetailsPanel({ comparison }: { comparison: EvaluationComparison }) {
  const rows = metricRows(comparison);
  const severityCounts = comparison.reviewer_issues.reduce<Record<string, number>>(
    (counts, issue) => {
      const severity = issueSeverity(issue) ?? "unspecified";
      counts[severity] = (counts[severity] ?? 0) + 1;
      return counts;
    },
    {},
  );

  return (
    <div className="mt-5 border-t border-border pt-5">
      {comparison.remediation_impact && (
        <RemediationImpactPanel impact={comparison.remediation_impact} />
      )}

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Metric</th>
              <th className="px-4 py-3 text-right">Baseline</th>
              <th className="px-4 py-3 text-right">Multi-Agent</th>
              <th className="px-4 py-3 text-right">Delta vs baseline</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-t border-border">
                <td className="px-4 py-3 font-medium">{row.label}</td>
                <td className="px-4 py-3 text-right">{row.baseline}</td>
                <td className="px-4 py-3 text-right">{row.multiAgent}</td>
                <td className="px-4 py-3 text-right">{row.delta}</td>
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
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-semibold">Reviewer Issues</h3>
          {comparison.reviewer_issues.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(severityCounts).map(([severity, count]) => (
                <span
                  key={severity}
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-xs font-medium capitalize",
                    severityClasses(severity),
                  )}
                >
                  {severity}: {count}
                </span>
              ))}
            </div>
          )}
        </div>

        {comparison.reviewer_issues.length === 0 ? (
          <p className="mt-3 rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No reviewer issues were recorded for this comparison.
          </p>
        ) : (
          <div className="mt-3 space-y-3">
            <CreateCorrectedRunForm evaluationCaseId={comparison.evaluation_case_id} />
            <ul className="space-y-2">
              {comparison.reviewer_issues.map((issue, index) => {
                const severity = issueSeverity(issue);
                return (
                  <li
                    key={`${comparison.evaluation_case_id}-${index}`}
                    className="rounded-md border border-border bg-background p-3 text-sm"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <p>{formatIssue(issue)}</p>
                      <span
                        className={cn(
                          "w-fit rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
                          severityClasses(severity),
                        )}
                      >
                        {severity ?? "unspecified"}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}

function ComparisonCard({
  comparison,
  expanded,
  onToggle,
}: {
  comparison: EvaluationComparison;
  expanded: boolean;
  onToggle: () => void;
}) {
  const scores = comparisonScore(comparison);
  const hasIssues = comparison.reviewer_issues.length > 0;
  const seriousIssues = hasSeriousReviewerIssue(comparison.reviewer_issues);
  const better = isMultiAgentBetter(comparison);
  const higherCost = comparison.cost_difference > 0;

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{workflowLabels[comparison.workflow_type]}</Badge>
            {better && <Badge variant="good">Multi-agent better</Badge>}
            {higherCost && <Badge variant="warning">Higher cost</Badge>}
            {seriousIssues ? (
              <Badge variant="danger">Needs review</Badge>
            ) : hasIssues ? (
              <Badge variant="warning">Minor issue</Badge>
            ) : (
              <Badge variant="good">Reviewer clean</Badge>
            )}
          </div>
          <h2 className="mt-3 text-lg font-semibold">{comparison.title}</h2>
          <p className="mt-2 line-clamp-2 max-w-4xl text-sm leading-6 text-muted-foreground">
            {comparison.input_preview}
          </p>
        </div>

        <button
          type="button"
          onClick={onToggle}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium transition-colors hover:bg-muted lg:self-start"
          aria-expanded={expanded}
        >
          {expanded ? "Close details" : "View details"}
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        <MetricChip
          label="Accuracy"
          context="vs baseline"
          value={formatQualityDelta(scores.accuracy)}
          positive={qualityDirection(scores.accuracy)}
        />
        <MetricChip
          label="Unsupported"
          context="vs baseline"
          value={formatUnsupportedDelta(scores.unsupported)}
          positive={unsupportedDirection(scores.unsupported)}
        />
        <MetricChip
          label="Completeness"
          context="vs baseline"
          value={formatQualityDelta(scores.completeness)}
          positive={qualityDirection(scores.completeness)}
        />
        <MetricChip
          label="Cost"
          context="vs baseline"
          value={formatCostDelta(comparison.cost_difference)}
          positive={comparison.cost_difference <= 0}
        />
        <MetricChip
          label="Latency"
          context="vs baseline"
          value={formatLatencyDelta(comparison.latency_difference_ms)}
          positive={comparison.latency_difference_ms <= 0}
        />
      </div>

      {expanded && <DetailsPanel comparison={comparison} />}
    </section>
  );
}

function SummaryHeader({ comparisons }: { comparisons: EvaluationComparison[] }) {
  const accuracy = average(
    comparisons.map((comparison) =>
      delta(
        comparison.baseline.factual_accuracy,
        comparison.multi_agent.factual_accuracy,
      ),
    ),
  );
  const unsupported = average(
    comparisons.map((comparison) =>
      delta(
        comparison.baseline.unsupported_claim_rate,
        comparison.multi_agent.unsupported_claim_rate,
      ),
    ),
  );
  const cost =
    comparisons.reduce((total, comparison) => total + comparison.cost_difference, 0) /
    comparisons.length;
  const latency =
    comparisons.reduce(
      (total, comparison) => total + comparison.latency_difference_ms,
      0,
    ) / comparisons.length;

  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <SummaryCard
        label="Comparisons"
        value={String(comparisons.length)}
        hint="paired baseline and multi-agent runs"
      />
      <SummaryCard
        label="Avg Accuracy Delta"
        value={formatPercentDelta(accuracy)}
        hint="positive favors multi-agent"
      />
      <SummaryCard
        label="Avg Unsupported Delta"
        value={formatUnsupportedDelta(unsupported)}
        hint="lower is better"
      />
      <SummaryCard
        label="Avg Cost Delta"
        value={formatCostDelta(cost)}
        hint="per comparison"
      />
      <SummaryCard
        label="Avg Latency Delta"
        value={formatLatencyDelta(latency)}
        hint="per comparison"
      />
    </section>
  );
}

function compareNumbers(
  left: number | null,
  right: number | null,
  direction: "asc" | "desc",
): number {
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  return direction === "asc" ? left - right : right - left;
}

export function WorkflowComparisonExplorer({
  comparisons,
  initialSearch = "",
}: {
  comparisons: EvaluationComparison[];
  initialSearch?: string;
}) {
  const [query, setQuery] = useState(initialSearch);
  const [filter, setFilter] = useState<QuickFilter>("all");
  const [sort, setSort] = useState<SortKey>("accuracy");
  const [visibleCount, setVisibleCount] = useState(pageSize);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    setVisibleCount(pageSize);
    setExpandedId(null);
  }, [query, filter, sort]);

  const filteredComparisons = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return comparisons
      .filter((comparison) => {
        if (filter === "needs_review") return comparison.reviewer_issues.length > 0;
        if (filter === "all") return true;
        return comparison.workflow_type === filter;
      })
      .filter((comparison) => {
        if (!normalizedQuery) return true;
        const searchable = `${comparison.title} ${comparison.input_preview}`.toLowerCase();
        return searchable.includes(normalizedQuery);
      })
      .sort((left, right) => {
        const leftScores = comparisonScore(left);
        const rightScores = comparisonScore(right);

        if (sort === "accuracy") {
          return compareNumbers(leftScores.accuracy, rightScores.accuracy, "desc");
        }
        if (sort === "unsupported") {
          return compareNumbers(leftScores.unsupported, rightScores.unsupported, "asc");
        }
        if (sort === "cost") {
          return left.cost_difference - right.cost_difference;
        }
        if (sort === "latency") {
          return left.latency_difference_ms - right.latency_difference_ms;
        }
        return left.title.localeCompare(right.title);
      });
  }, [comparisons, filter, query, sort]);

  const visibleComparisons = filteredComparisons.slice(0, visibleCount);
  const remainingCount = filteredComparisons.length - visibleComparisons.length;

  return (
    <div className="mt-6 space-y-5">
      <SummaryHeader comparisons={comparisons} />

      <section className="rounded-lg border border-border bg-card p-4">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_auto] lg:items-center">
          <label className="relative block">
            <span className="sr-only">Search comparisons</span>
            <Search
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search title or input"
              className="h-10 w-full rounded-md border border-border bg-background pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm lg:w-64">
            <span className="text-xs text-muted-foreground">Sort by</span>
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as SortKey)}
              className="h-10 rounded-md border border-border bg-background px-3 text-sm outline-none transition-colors focus:border-primary"
            >
              {sortOptions.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {quickFilters.map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setFilter(option.key)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                filter === option.key
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background hover:bg-muted",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      {filteredComparisons.length === 0 ? (
        <section className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
          <p>No comparison results match the current filters.</p>
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setFilter("all");
              setSort("accuracy");
            }}
            className="mt-3 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            Clear filters
          </button>
        </section>
      ) : (
        <>
          <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <p>
              Showing {visibleComparisons.length} of {filteredComparisons.length}
            </p>
            <p>{comparisons.length} total comparisons</p>
          </div>

          <div className="space-y-3">
            {visibleComparisons.map((comparison) => (
              <ComparisonCard
                key={comparison.evaluation_case_id}
                comparison={comparison}
                expanded={expandedId === comparison.evaluation_case_id}
                onToggle={() =>
                  setExpandedId((current) =>
                    current === comparison.evaluation_case_id
                      ? null
                      : comparison.evaluation_case_id,
                  )
                }
              />
            ))}
          </div>

          {remainingCount > 0 && (
            <div className="flex justify-center">
              <button
                type="button"
                onClick={() => setVisibleCount((current) => current + pageSize)}
                className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted"
              >
                Show {Math.min(pageSize, remainingCount)} more
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
