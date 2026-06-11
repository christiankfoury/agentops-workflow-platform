import Link from "next/link";
import { getHumanFeedbackSummary, listWorkflowRuns } from "@/lib/api";
import type { HumanFeedbackSummary } from "@/lib/types";

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
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

export default async function Home() {
  let runCount = 0;
  let feedbackSummary = emptyFeedbackSummary();
  try {
    const [runs, summary] = await Promise.all([
      listWorkflowRuns(),
      getHumanFeedbackSummary(),
    ]);
    runCount = runs.length;
    feedbackSummary = summary;
  } catch {
    // API may not be running; keep dashboard metrics empty.
  }

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight">
        AgentOps Workflow Platform
      </h1>
      <p className="mt-2 text-muted-foreground">
        Enterprise multi-agent workflow platform.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-6">
          <p className="text-sm text-muted-foreground">Total Workflow Runs</p>
          <p className="mt-1 text-4xl font-bold">{runCount}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <p className="text-sm text-muted-foreground">Human Approval Rate</p>
          <p className="mt-1 text-4xl font-bold">
            {formatPercent(feedbackSummary.approval_rate)}
          </p>
        </div>
      </div>

      <section className="mt-8">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Human Feedback Loop</h2>
            <p className="text-sm text-muted-foreground">
              Reviewer flags, human edits, and approval decisions captured from review history.
            </p>
          </div>
          <Link
            href="/human-approvals"
            className="text-sm text-primary underline hover:opacity-80"
          >
            View approvals
          </Link>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Approvals with Feedback</p>
            <p className="mt-1 text-2xl font-semibold">
              {feedbackSummary.approvals_with_feedback}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Approvals with Edits</p>
            <p className="mt-1 text-2xl font-semibold">
              {feedbackSummary.approvals_with_edits}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">Retry Request Rate</p>
            <p className="mt-1 text-2xl font-semibold">
              {formatPercent(feedbackSummary.retry_request_rate)}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="text-sm font-semibold">Common Reviewer Issues</h3>
            <div className="mt-3 space-y-3">
              {feedbackSummary.common_reviewer_issues.length === 0 ? (
                <p className="text-sm text-muted-foreground">No reviewer issues yet.</p>
              ) : (
                feedbackSummary.common_reviewer_issues.map((issue) => (
                  <div key={`${issue.label}-${issue.severity ?? "none"}`}>
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium">{issue.label}</p>
                      <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs">
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

          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="text-sm font-semibold">Common Human Edits</h3>
            <div className="mt-3 space-y-3">
              {feedbackSummary.common_human_edits.length === 0 ? (
                <p className="text-sm text-muted-foreground">No human edits yet.</p>
              ) : (
                feedbackSummary.common_human_edits.map((edit) => (
                  <div key={edit.field}>
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium">{edit.field}</p>
                      <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs">
                        {edit.count}
                      </span>
                    </div>
                    {edit.examples[0] && (
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                        {edit.examples[0]}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="text-sm font-semibold">Approval Trend</h3>
            <div className="mt-3 space-y-2">
              {feedbackSummary.approval_trend.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No resolved approvals yet.
                </p>
              ) : (
                feedbackSummary.approval_trend.slice(-5).map((point) => (
                  <div
                    key={point.date}
                    className="grid grid-cols-[1fr_auto] gap-3 text-sm"
                  >
                    <span className="text-muted-foreground">{point.date}</span>
                    <span className="font-medium">
                      {point.approved}/{point.total} approved
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      <div className="mt-8 flex gap-3">
        <Link
          href="/workflow-runs"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          View Runs
        </Link>
        <Link
          href="/workflow-runs/new"
          className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
        >
          New Workflow
        </Link>
      </div>
    </div>
  );
}
