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
  actionLabel: string;
  destination: string;
}[] = [
  {
    target: "sales-report",
    title: "Sales Workflow Demo",
    workflowType: "sales_report",
    primaryMetric: "Compare baseline vs reviewed executive summaries.",
    actionLabel: "Load Sales Demo",
    destination: "/workflow-comparison?search=Sales",
  },
  {
    target: "customer-feedback",
    title: "Feedback Workflow Demo",
    workflowType: "customer_feedback",
    primaryMetric: "Show product recommendations with human approval.",
    actionLabel: "Load Feedback Demo",
    destination: "/workflow-comparison?search=Feedback",
  },
  {
    target: "incident-log",
    title: "Incident Workflow Demo",
    workflowType: "incident_log",
    primaryMetric: "Inspect incident analysis and final report flow.",
    actionLabel: "Load Incident Demo",
    destination: "/workflow-comparison?search=Incident",
  },
  {
    target: "full-evaluation",
    title: "Full Portfolio Demo",
    primaryMetric: "Populate all dashboards for a portfolio walkthrough.",
    actionLabel: "Load Full Demo",
    destination: "/evaluation",
  },
];

const guidedStories = [
  {
    title: "Reviewer issue correction path",
    href: "/workflow-comparison?search=%5BDemo%5D%20Reviewer%20issue%20correction%20path",
    description:
      "Proves the reviewer can catch weak outputs and turn issues into a corrected multi-agent run.",
  },
  {
    title: "Remediation impact showcase",
    href: "/workflow-comparison?search=%5BDemo%5D%20Remediation%20impact%20showcase",
    description:
      "Shows corrected-vs-previous impact with measurable changes in quality and trust metrics.",
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

function evaluationResultLabel(workflowType?: WorkflowType): string {
  return workflowType ? "Evaluation Results" : "Total Evaluation Results";
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
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <h2 className="text-lg font-semibold">What these demo actions do</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              These controls load repeatable demo datasets: workflow runs,
              agent traces, reviewer outcomes, final reports, and stored
              evaluation results. They prepare the product for a predictable
              walkthrough; manual workflow intake still starts from New Workflow.
            </p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              The accuracy values come from completed multi-agent evaluation
              results returned by the evaluation summary API. For seeded demos,
              those records are deterministic demo data, so the numbers stay
              stable across presentations.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="border-l border-border pl-3">
                <p className="text-xs font-semibold uppercase text-muted-foreground">
                  1. Seed
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Load one focused workflow dataset or the full portfolio.
                </p>
              </div>
              <div className="border-l border-border pl-3">
                <p className="text-xs font-semibold uppercase text-muted-foreground">
                  2. Inspect
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Open filtered comparisons, final outputs, cost, trend, and
                  trace dashboards.
                </p>
              </div>
              <div className="border-l border-border pl-3">
                <p className="text-xs font-semibold uppercase text-muted-foreground">
                  3. Demo
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Use the guided stories to show review, correction, and
                  remediation impact.
                </p>
              </div>
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Guided stories</h2>
              <Link
                href="/workflow-comparison"
                className="rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
              >
                Open Compare
              </Link>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Use these after seeding the full evaluation demo.
            </p>
            <div className="mt-3 space-y-2">
              {guidedStories.map((story) => (
                <Link
                  key={story.href}
                  href={story.href}
                  className="block rounded-md border border-border bg-background p-3 transition-colors hover:bg-accent"
                >
                  <span className="text-sm font-medium">{story.title}</span>
                  <span className="mt-1 block text-sm text-muted-foreground">
                    {story.description}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="mt-8">
        <h2 className="text-lg font-semibold">Demo data loaders</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Seed one focused workflow or load the full dataset for portfolio-wide
          dashboards.
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Accuracy is factual accuracy across completed multi-agent evaluation
          results.
        </p>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        {demoCards.map((card) => (
          <form
            key={card.target}
            action={seedDemoAction}
            className="rounded-lg border border-border bg-card p-4"
          >
            <input type="hidden" name="target" value={card.target} />
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground">
                    {card.workflowType
                      ? workflowLabels[card.workflowType]
                      : "Portfolio demo"}
                  </p>
                  <h2 className="mt-2 text-lg font-semibold">{card.title}</h2>
                  <p className="mt-4 text-sm text-muted-foreground">
                    {card.primaryMetric}
                  </p>
                </div>
                <button
                  type="submit"
                  className="w-fit rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  {card.actionLabel}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3 rounded-md bg-muted p-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">
                    {evaluationResultLabel(card.workflowType)}
                  </p>
                  <p className="mt-1 font-medium">
                    {countRunsForWorkflow(summaries, card.workflowType)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">
                    Multi-agent Accuracy
                  </p>
                  <p className="mt-1 font-medium">
                    {averageAccuracy(summaries, card.workflowType)}
                  </p>
                </div>
              </div>
              <div>
                <Link
                  href={card.destination}
                  className="text-sm text-primary underline hover:opacity-80"
                >
                  Open existing output
                </Link>
              </div>
            </div>
          </form>
        ))}
      </div>
    </div>
  );
}
