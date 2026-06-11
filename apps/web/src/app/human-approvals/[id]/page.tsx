import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getHumanApproval,
  getUploadedInput,
  getWorkflowRun,
  listAgentSteps,
} from "@/lib/api";
import type { AgentStep, HumanApproval } from "@/lib/types";
import {
  approveAction,
  editAction,
  rejectAction,
  requestRetryAction,
} from "./actions";

function formatJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function getRecommendedAction(approval: HumanApproval): string {
  if (approval.status !== "pending") return "Resolved";
  const hasHighSeverityIssue = (approval.issues_json ?? []).some(
    (issue) =>
      typeof issue === "object" &&
      issue !== null &&
      "severity" in issue &&
      issue.severity === "high",
  );
  if (hasHighSeverityIssue) return "Request Retry";
  if (approval.reviewer_score != null && approval.reviewer_score >= 0.85) {
    return "Approve";
  }
  return "Review Manually";
}

function getLatestStep(steps: AgentStep[], agentType: string): AgentStep | undefined {
  return steps.filter((step) => step.agent_type === agentType).at(-1);
}

export default async function HumanApprovalDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const approval = await getHumanApproval(id);

  if (!approval) notFound();

  const run = await getWorkflowRun(approval.workflow_run_id);
  if (!run) notFound();

  const [uploadedInput, agentSteps] = await Promise.all([
    run.input_id ? getUploadedInput(run.input_id) : Promise.resolve(null),
    listAgentSteps(run.id),
  ]);
  const analystStep = getLatestStep(agentSteps, "analyst");
  const reviewerStep = getLatestStep(agentSteps, "reviewer");
  const isPending = approval.status === "pending";

  return (
    <div>
      <Link
        href="/human-approvals"
        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        Back to Human Approvals
      </Link>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Human Approval</h1>
          <p className="font-mono text-sm text-muted-foreground">{approval.id}</p>
        </div>
        <span className="w-fit rounded-full bg-muted px-3 py-1 text-sm font-medium">
          {approval.status}
        </span>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Workflow Type</p>
          <p className="mt-1 font-medium">{run.workflow_type}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Workflow Status</p>
          <p className="mt-1 font-medium">{run.status}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Reviewer Score</p>
          <p className="mt-1 font-medium">{approval.reviewer_score ?? "-"}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Recommended Action</p>
          <p className="mt-1 font-medium">{getRecommendedAction(approval)}</p>
        </div>
      </div>

      {uploadedInput && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold">Original Input</h2>
          <div className="mt-2 rounded-lg border border-border bg-card p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
              <p className="font-medium">{uploadedInput.title}</p>
              {uploadedInput.file_name && (
                <p className="text-xs text-muted-foreground">
                  {uploadedInput.file_name}
                </p>
              )}
            </div>
            <pre className="mt-4 max-h-80 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
              {uploadedInput.raw_text}
            </pre>
          </div>
        </section>
      )}

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Analyst Output</h2>
        <pre className="mt-2 max-h-96 overflow-auto rounded-lg border border-border bg-muted p-4 text-sm whitespace-pre-wrap">
          {formatJson(analystStep?.output_json)}
        </pre>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Reviewer Issues</h2>
        <pre className="mt-2 max-h-80 overflow-auto rounded-lg border border-border bg-muted p-4 text-sm whitespace-pre-wrap">
          {formatJson(approval.issues_json)}
        </pre>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Reviewer Output</h2>
        <pre className="mt-2 max-h-80 overflow-auto rounded-lg border border-border bg-muted p-4 text-sm whitespace-pre-wrap">
          {formatJson(reviewerStep?.output_json)}
        </pre>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Edit Analysis</h2>
        <form action={editAction} className="mt-2 rounded-lg border border-border bg-card p-4">
          <input type="hidden" name="approval_id" value={approval.id} />
          <label className="block text-sm font-medium" htmlFor="human_feedback">
            Human Feedback
          </label>
          <textarea
            id="human_feedback"
            name="human_feedback"
            defaultValue={approval.human_feedback ?? ""}
            disabled={!isPending}
            className="mt-2 min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-60"
          />
          <label
            className="mt-4 block text-sm font-medium"
            htmlFor="edited_analysis_json"
          >
            Edited Analysis JSON
          </label>
          <textarea
            id="edited_analysis_json"
            name="edited_analysis_json"
            defaultValue={
              approval.edited_analysis_json
                ? formatJson(approval.edited_analysis_json)
                : ""
            }
            disabled={!isPending}
            className="mt-2 min-h-40 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!isPending}
            className="mt-4 rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
          >
            Save Edits
          </button>
        </form>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Actions</h2>
        <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <form action={approveAction} className="rounded-lg border border-border bg-card p-4">
            <input type="hidden" name="approval_id" value={approval.id} />
            <input
              type="hidden"
              name="human_feedback"
              value={approval.human_feedback ?? ""}
            />
            <button
              type="submit"
              disabled={!isPending}
              className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Approve
            </button>
          </form>
          <form
            action={requestRetryAction}
            className="rounded-lg border border-border bg-card p-4"
          >
            <input type="hidden" name="approval_id" value={approval.id} />
            <input
              type="hidden"
              name="human_feedback"
              value={approval.human_feedback ?? ""}
            />
            <button
              type="submit"
              disabled={!isPending}
              className="w-full rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
            >
              Request Retry
            </button>
          </form>
          <form action={rejectAction} className="rounded-lg border border-border bg-card p-4">
            <input type="hidden" name="approval_id" value={approval.id} />
            <input
              type="hidden"
              name="human_feedback"
              value={approval.human_feedback ?? ""}
            />
            <button
              type="submit"
              disabled={!isPending}
              className="w-full rounded-md border border-destructive/40 px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Reject Workflow
            </button>
          </form>
        </div>
      </section>

      <div className="mt-6">
        <Link
          href={`/workflow-runs/${run.id}`}
          className="text-sm text-primary underline hover:opacity-80"
        >
          View Workflow Run
        </Link>
      </div>
    </div>
  );
}
