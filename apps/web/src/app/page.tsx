import {
  Activity,
  CheckCircle2,
  Database,
  GitCompare,
  ShieldCheck,
  Users,
} from "lucide-react";
import Link from "next/link";
import {
  getEvaluationSummary,
  getHumanFeedbackSummary,
  listWorkflowRuns,
} from "@/lib/api";
import type {
  EvaluationMetricsSummary,
  HumanFeedbackSummary,
  WorkflowRun,
} from "@/lib/types";

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatWorkflowLabel(value: string): string {
  if (value === "customer_feedback") return "Customer Feedback";
  if (value === "incident_log") return "Incident Log";
  return "Sales Report";
}

function emptyFeedbackSummary(): HumanFeedbackSummary {
  return {
    total_approvals: 0,
    resolved_approvals: 0,
    approvals_with_feedback: 0,
    approvals_with_edits: 0,
    approval_rate: 0,
    retry_request_rate: 0,
    rejection_rate: 0,
    common_reviewer_issues: [],
    common_human_edits: [],
    approval_trend: [],
  };
}

function topMultiAgentSummary(
  summaries: EvaluationMetricsSummary[],
): EvaluationMetricsSummary | undefined {
  return summaries
    .filter((summary) => summary.run_mode === "multi_agent" && summary.run_count > 0)
    .sort((left, right) => right.factual_accuracy - left.factual_accuracy)
    .at(0);
}

function workflowCounts(runs: WorkflowRun[]) {
  return {
    total: runs.length,
    completed: runs.filter((run) => run.status === "completed").length,
    waiting: runs.filter((run) => run.status === "waiting_for_human").length,
    active: runs.filter((run) =>
      ["created", "running", "reviewer_running", "writer_running", "retrying"].includes(
        run.status,
      ),
    ).length,
  };
}

function MetricCard({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: "neutral" | "blue" | "emerald" | "amber";
}) {
  const toneClass = {
    neutral: "border-border",
    blue: "border-blue-200 bg-blue-50/50 dark:border-blue-900/60 dark:bg-blue-950/20",
    emerald:
      "border-emerald-200 bg-emerald-50/50 dark:border-emerald-900/60 dark:bg-emerald-950/20",
    amber:
      "border-amber-200 bg-amber-50/50 dark:border-amber-900/60 dark:bg-amber-950/20",
  }[tone];

  return (
    <section className={`rounded-lg border bg-card p-5 ${toneClass}`}>
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-sm text-muted-foreground">{detail}</p>
    </section>
  );
}

function QuickLink({
  href,
  label,
  description,
  icon: Icon,
}: {
  href: string;
  label: string;
  description: string;
  icon: typeof Activity;
}) {
  return (
    <Link
      href={href}
      className="group rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent"
    >
      <div className="flex items-start gap-3">
        <span className="rounded-md border border-border bg-background p-2">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <span>
          <span className="block font-medium group-hover:text-foreground">{label}</span>
          <span className="mt-1 block text-sm text-muted-foreground">
            {description}
          </span>
        </span>
      </div>
    </Link>
  );
}

export default async function Home() {
  let runs: WorkflowRun[] = [];
  let feedbackSummary = emptyFeedbackSummary();
  let evaluationSummaries: EvaluationMetricsSummary[] = [];
  let apiError = false;

  try {
    const [workflowRuns, summary, evaluations] = await Promise.all([
      listWorkflowRuns(),
      getHumanFeedbackSummary(),
      getEvaluationSummary(),
    ]);
    runs = workflowRuns;
    feedbackSummary = summary;
    evaluationSummaries = evaluations;
  } catch {
    apiError = true;
  }

  const counts = workflowCounts(runs);
  const bestSummary = topMultiAgentSummary(evaluationSummaries);
  const hasData = counts.total > 0 || evaluationSummaries.some((item) => item.run_count > 0);

  return (
    <div className="space-y-8">
      <section className="rounded-lg border border-border bg-card p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-medium uppercase text-muted-foreground">
              Portfolio demo console
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
              AgentOps Workflow Platform
            </h1>
            <p className="mt-3 text-base leading-7 text-muted-foreground">
              Multi-agent business workflows with deterministic evaluation,
              reviewer gates, human approval, traceability, and cost visibility.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/demo"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Run Demo
            </Link>
            <Link
              href="/workflow-comparison"
              className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
            >
              Compare Outputs
            </Link>
          </div>
        </div>
      </section>

      {apiError && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          API data is unavailable, so the dashboard is showing empty operational
          metrics. Start the API or use Demo Mode to seed data.
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Workflow Runs"
          value={String(counts.total)}
          detail={`${counts.completed} completed, ${counts.active} active`}
          tone="blue"
        />
        <MetricCard
          label="Waiting For Review"
          value={String(counts.waiting)}
          detail="Runs paused for human approval"
          tone="amber"
        />
        <MetricCard
          label="Human Approval Rate"
          value={formatPercent(feedbackSummary.approval_rate)}
          detail={`${feedbackSummary.resolved_approvals} resolved decisions`}
          tone="emerald"
        />
        <MetricCard
          label="Best Multi-Agent Accuracy"
          value={bestSummary ? formatPercent(bestSummary.factual_accuracy) : "0%"}
          detail={
            bestSummary
              ? formatWorkflowLabel(bestSummary.workflow_type)
              : "Run evaluations to populate"
          }
        />
      </section>

      {!hasData && (
        <section className="rounded-lg border border-dashed border-border p-6">
          <h2 className="font-semibold">No demo data yet</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Seed the demo dataset to populate workflow runs, reviewer issues,
            evaluation comparisons, cost charts, and approval history.
          </p>
          <Link
            href="/demo"
            className="mt-4 inline-flex rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
          >
            Open Demo Mode
          </Link>
        </section>
      )}

      <section>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Recruiter Demo Path</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              The core screens show agent execution, review gates, quality
              improvement, and operating cost.
            </p>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <QuickLink
            href="/workflow-runs"
            label="Workflow Runs"
            description="Inspect current state, retries, approvals, and final output."
            icon={Activity}
          />
          <QuickLink
            href="/human-approvals"
            label="Human Review"
            description="Review flagged outputs and edit structured analysis."
            icon={Users}
          />
          <QuickLink
            href="/workflow-comparison"
            label="Baseline Comparison"
            description="Compare baseline and multi-agent outputs side by side."
            icon={GitCompare}
          />
          <QuickLink
            href="/evaluation"
            label="Evaluation Metrics"
            description="Track factual accuracy, unsupported claims, and completeness."
            icon={CheckCircle2}
          />
          <QuickLink
            href="/costs"
            label="Cost Dashboard"
            description="Monitor spend, tokens, retries, and expensive runs."
            icon={Database}
          />
          <QuickLink
            href="/failures"
            label="Failure Explorer"
            description="Surface low scores, schema issues, and rejected outputs."
            icon={ShieldCheck}
          />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-lg font-semibold">Workflow Coverage</h2>
          <div className="mt-4 space-y-3 text-sm">
            {["sales_report", "customer_feedback", "incident_log"].map((workflow) => {
              const count = runs.filter((run) => run.workflow_type === workflow).length;
              return (
                <div key={workflow} className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">
                    {formatWorkflowLabel(workflow)}
                  </span>
                  <span className="font-medium">{count} runs</span>
                </div>
              );
            })}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-lg font-semibold">Reviewer Signals</h2>
          <div className="mt-4 space-y-3">
            {feedbackSummary.common_reviewer_issues.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No reviewer issues have been recorded.
              </p>
            ) : (
              feedbackSummary.common_reviewer_issues.slice(0, 3).map((issue) => (
                <div key={`${issue.label}-${issue.severity ?? "none"}`}>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium">{issue.label}</span>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                      {issue.count}
                    </span>
                  </div>
                  {issue.severity && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Severity: {issue.severity}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-lg font-semibold">Human Feedback Loop</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">With feedback</dt>
              <dd className="mt-1 text-xl font-semibold">
                {feedbackSummary.approvals_with_feedback}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">With edits</dt>
              <dd className="mt-1 text-xl font-semibold">
                {feedbackSummary.approvals_with_edits}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Retry rate</dt>
              <dd className="mt-1 text-xl font-semibold">
                {formatPercent(feedbackSummary.retry_request_rate)}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Rejection rate</dt>
              <dd className="mt-1 text-xl font-semibold">
                {formatPercent(feedbackSummary.rejection_rate)}
              </dd>
            </div>
          </dl>
        </div>
      </section>
    </div>
  );
}
