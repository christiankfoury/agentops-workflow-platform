import Link from "next/link";
import { getEvaluationSummary, listWorkflowRuns } from "@/lib/api";
import type { DemoSeedTarget, EvaluationMetricsSummary, WorkflowType } from "@/lib/types";
import { seedDemoAction } from "./actions";

const workflowLabels: Record<WorkflowType, string> = {
  sales_report: "Sales",
  customer_feedback: "Feedback",
  incident_log: "Incident",
};

const demoCards: {
  target: DemoSeedTarget;
  title: string;
  workflowType?: WorkflowType;
  primaryMetric: string;
  destination: string;
}[] = [
  {
    target: "sales-report",
    title: "Run Demo Sales Workflow",
    workflowType: "sales_report",
    primaryMetric: "executive summaries",
    destination: "/workflow-comparison",
  },
  {
    target: "customer-feedback",
    title: "Run Demo Feedback Workflow",
    workflowType: "customer_feedback",
    primaryMetric: "product insights",
    destination: "/workflow-comparison",
  },
  {
    target: "incident-log",
    title: "Run Demo Incident Workflow",
    workflowType: "incident_log",
    primaryMetric: "post-incident reports",
    destination: "/workflow-comparison",
  },
  {
    target: "full-evaluation",
    title: "Run Full Evaluation",
    primaryMetric: "all workflows",
    destination: "/evaluation",
  },
];

const guidedStories = [
  {
    title: "Reviewer issue correction path",
    href: "/workflow-comparison?search=%5BDemo%5D%20Reviewer%20issue%20correction%20path",
    description:
      "Open the action-ready case where a reviewer issue can create a corrected multi-agent run.",
  },
  {
    title: "Remediation impact showcase",
    href: "/workflow-comparison?search=%5BDemo%5D%20Remediation%20impact%20showcase",
    description:
      "Open the impact-ready case where corrected-vs-previous run metrics are visible.",
  },
];

function emptySummaries(): EvaluationMetricsSummary[] {
  return [];
}

function countRunsForWorkflow(
  summaries: EvaluationMetricsSummary[],
  workflowType?: WorkflowType,
): number {
  if (!workflowType) {
    return summaries.reduce((total, summary) => total + summary.run_count, 0);
  }
  return summaries
    .filter((summary) => summary.workflow_type === workflowType)
    .reduce((total, summary) => total + summary.run_count, 0);
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function averageAccuracy(
  summaries: EvaluationMetricsSummary[],
  workflowType?: WorkflowType,
): string {
  const relevant = summaries.filter(
    (summary) =>
      summary.run_count > 0 &&
      summary.run_mode === "multi_agent" &&
      (!workflowType || summary.workflow_type === workflowType),
  );
  if (relevant.length === 0) return "0%";
  const average =
    relevant.reduce((total, summary) => total + summary.factual_accuracy, 0) /
    relevant.length;
  return formatPercent(average);
}

export default async function DemoPage() {
  let summaries = emptySummaries();
  let totalWorkflowRuns = 0;
  try {
    const [evaluationSummaries, workflowRuns] = await Promise.all([
      getEvaluationSummary(),
      listWorkflowRuns(),
    ]);
    summaries = evaluationSummaries;
    totalWorkflowRuns = workflowRuns.length;
  } catch {
    // API may be unavailable during static smoke checks.
  }

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Demo Mode</h1>
          <p className="mt-2 text-muted-foreground">
            Seed polished demo workflows and evaluation results for a live walkthrough.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/workflow-comparison"
            className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
          >
            Compare
          </Link>
          <Link
            href="/evaluation"
            className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
          >
            Evaluation
          </Link>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Workflow Runs</p>
          <p className="mt-1 text-2xl font-semibold">{totalWorkflowRuns}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Evaluation Results</p>
          <p className="mt-1 text-2xl font-semibold">
            {summaries.reduce((total, summary) => total + summary.run_count, 0)}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Multi-Agent Accuracy</p>
          <p className="mt-1 text-2xl font-semibold">
            {averageAccuracy(summaries)}
          </p>
        </div>
      </div>

      <section className="mt-8 rounded-lg border border-border bg-card p-5">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Guided comparison stories</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              After seeding the full evaluation demo, use these paths to show
              reviewer correction and remediation impact.
            </p>
          </div>
          <Link
            href="/workflow-comparison"
            className="mt-3 w-fit rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent sm:mt-0"
          >
            Open Compare
          </Link>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {guidedStories.map((story) => (
            <Link
              key={story.href}
              href={story.href}
              className="rounded-md border border-border bg-background p-4 transition-colors hover:bg-accent"
            >
              <span className="text-sm font-medium">{story.title}</span>
              <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                {story.description}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
        {demoCards.map((card) => (
          <form
            key={card.target}
            action={seedDemoAction}
            className="rounded-lg border border-border bg-card p-5"
          >
            <input type="hidden" name="target" value={card.target} />
            <div className="flex min-h-44 flex-col justify-between gap-5">
              <div>
                <p className="text-xs text-muted-foreground">
                  {card.workflowType
                    ? workflowLabels[card.workflowType]
                    : "Portfolio demo"}
                </p>
                <h2 className="mt-2 text-lg font-semibold">{card.title}</h2>
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Seeded Runs</p>
                    <p className="mt-1 font-medium">
                      {countRunsForWorkflow(summaries, card.workflowType)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Accuracy</p>
                    <p className="mt-1 font-medium">
                      {averageAccuracy(summaries, card.workflowType)}
                    </p>
                  </div>
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  {card.primaryMetric}
                </p>
              </div>
              <div className="flex items-center justify-between gap-3">
                <Link
                  href={card.destination}
                  className="text-sm text-primary underline hover:opacity-80"
                >
                  View output
                </Link>
                <button
                  type="submit"
                  className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  Run
                </button>
              </div>
            </div>
          </form>
        ))}
      </div>
    </div>
  );
}
