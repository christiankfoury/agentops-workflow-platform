import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { LocalDateTime } from "@/components/local-date-time";
import {
  getUploadedInput,
  getWorkflowRun,
  listAgentSteps,
  listHumanApprovals,
} from "@/lib/api";
import type { AgentStep, HumanApproval, WorkflowRun } from "@/lib/types";

function formatPercent(value: number | null): string {
  return value == null ? "-" : `${Math.round(value * 100)}%`;
}

function formatCost(value: number | null): string {
  return value == null ? "-" : `$${value.toFixed(6)}`;
}

function formatLatency(value: number | null): string {
  if (value == null) return "-";
  if (value < 1000) return `${value}ms`;
  return `${(value / 1000).toFixed(2)}s`;
}

function formatJson(value: unknown): string {
  if (value == null) return "Not recorded.";
  return JSON.stringify(value, null, 2);
}

function getLatestStep(steps: AgentStep[], agentType: string): AgentStep | undefined {
  return steps
    .filter((step) => step.agent_type === agentType && step.status === "completed")
    .at(-1);
}

function getLatestApproval(approvals: HumanApproval[]): HumanApproval | undefined {
  return [...approvals]
    .sort((left, right) => {
      const leftTime = left.resolved_at ?? left.created_at;
      const rightTime = right.resolved_at ?? right.created_at;
      return new Date(rightTime).getTime() - new Date(leftTime).getTime();
    })
    .at(0);
}

function MetricCard({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}

function TracePanel({
  title,
  summary,
  children,
  open = false,
}: {
  title: string;
  summary: string;
  children: string;
  open?: boolean;
}) {
  return (
    <details
      open={open}
      className="rounded-lg border border-border bg-card p-4"
    >
      <summary className="cursor-pointer list-none">
        <span className="font-medium">{title}</span>
        <span className="mt-1 block text-sm text-muted-foreground">{summary}</span>
      </summary>
      <pre className="mt-4 max-h-96 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
        {children}
      </pre>
    </details>
  );
}

function getHumanApprovalStatus(approval: HumanApproval | undefined): ReactNode {
  if (!approval) return "Not recorded";
  if (approval.resolved_at) {
    return (
      <>
        {approval.status} at <LocalDateTime value={approval.resolved_at} />
      </>
    );
  }
  return approval.status;
}

function getWriterOutput(step: AgentStep | undefined, run: WorkflowRun): string {
  const stepOutput = step?.output_json?.final_output;
  if (typeof stepOutput === "string" && stepOutput.length > 0) return stepOutput;
  return run.final_output ?? "Not recorded.";
}

function getAnalysisTraceLabel(workflowType: string): string {
  if (workflowType === "customer_feedback") return "Insight Output";
  if (workflowType === "incident_log") return "Root Cause Output";
  return "Analyst Output";
}

function getAnalysisTraceStep(
  steps: AgentStep[],
  workflowType: string,
): AgentStep | undefined {
  if (workflowType === "customer_feedback") return getLatestStep(steps, "insight");
  if (workflowType === "incident_log") return getLatestStep(steps, "root_cause");
  return getLatestStep(steps, "analyst");
}

export default async function FinalOutputPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const run = await getWorkflowRun(id);

  if (!run) notFound();

  const uploadedInput = run.input_id ? await getUploadedInput(run.input_id) : null;
  const agentSteps = await listAgentSteps(run.id);
  const approvals = (await listHumanApprovals()).filter(
    (approval) => approval.workflow_run_id === run.id,
  );
  const analysisStep = getAnalysisTraceStep(agentSteps, run.workflow_type);
  const reviewerStep = getLatestStep(agentSteps, "reviewer");
  const writerStep = getLatestStep(agentSteps, "writer");
  const latestApproval = getLatestApproval(approvals);
  const analysisLabel = getAnalysisTraceLabel(run.workflow_type);
  const usedHumanApprovedAnalysis = latestApproval?.status === "approved";

  const metrics = [
    { label: "Workflow Status", value: run.status },
    { label: "Quality Score", value: formatPercent(run.quality_score) },
    { label: "Total Cost", value: formatCost(run.total_cost) },
    { label: "Total Latency", value: formatLatency(run.latency_ms) },
    { label: "Retries", value: String(run.retry_count) },
    { label: "Human Approval", value: getHumanApprovalStatus(latestApproval) },
  ];

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            href={`/workflow-runs/${run.id}`}
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            Back to Workflow Run
          </Link>
          <h1 className="mt-4 text-2xl font-bold tracking-tight">
            Final Executive Summary
          </h1>
          <p className="font-mono text-sm text-muted-foreground">{run.id}</p>
        </div>
        <Link
          href="/workflow-runs"
          className="w-fit rounded-md border border-border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted"
        >
          All Runs
        </Link>
      </div>

      <section className="mt-6 rounded-lg border border-border bg-card p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Final Output</h2>
            <p className="text-sm text-muted-foreground">
              {usedHumanApprovedAnalysis
                ? "Writer output generated from the human-approved analysis."
                : "Writer output generated from reviewed workflow analysis."}
            </p>
          </div>
          <span className="w-fit rounded-full bg-muted px-2.5 py-1 text-xs font-medium">
            {run.workflow_type}
          </span>
        </div>
        <pre className="mt-4 whitespace-pre-wrap rounded-lg bg-muted/60 p-5 text-sm leading-7">
          {run.final_output ?? "No final output has been stored for this run."}
        </pre>
      </section>

      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} label={metric.label} value={metric.value} />
        ))}
      </section>

      <section className="mt-8">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="text-lg font-semibold">Workflow Trace</h2>
          <p className="text-sm text-muted-foreground">
            Expand each step to inspect the inputs and outputs behind the summary.
          </p>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <TracePanel
            title="Original Input"
            summary={uploadedInput?.title ?? "Missing uploaded input"}
            open
          >
            {uploadedInput?.raw_text ?? "Uploaded input not found."}
          </TracePanel>
          <TracePanel
            title={analysisLabel}
            summary={analysisStep?.agent_name ?? `No completed ${analysisLabel.toLowerCase()}`}
            open
          >
            {formatJson(analysisStep?.output_json)}
          </TracePanel>
          <TracePanel
            title="Reviewer Feedback"
            summary={reviewerStep?.agent_name ?? "No completed reviewer step"}
          >
            {formatJson(reviewerStep?.output_json)}
          </TracePanel>
          <TracePanel
            title="Human Feedback"
            summary={latestApproval ? latestApproval.status : "No human approval record"}
          >
            {formatJson({
              status: latestApproval?.status,
              reviewer_score: latestApproval?.reviewer_score,
              issues: latestApproval?.issues_json,
              human_feedback: latestApproval?.human_feedback,
              edited_analysis: latestApproval?.edited_analysis_json,
              resolved_at: latestApproval?.resolved_at,
            })}
          </TracePanel>
          <TracePanel
            title="Writer Output"
            summary={writerStep?.agent_name ?? "Stored final output"}
          >
            {getWriterOutput(writerStep, run)}
          </TracePanel>
        </div>
      </section>
    </div>
  );
}
