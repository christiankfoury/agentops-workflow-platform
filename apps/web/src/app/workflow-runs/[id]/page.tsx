import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { ArrowLeft, ArrowRight, ChevronDown } from "lucide-react";
import { LocalDateTime } from "@/components/local-date-time";
import {
  getUploadedInput,
  getWorkflowRun,
  listAgentSteps,
  listWorkflowEvents,
  listHumanApprovals,
} from "@/lib/api";
import type { AgentStep, WorkflowEvent } from "@/lib/types";
import { CancelWorkflowForm } from "./cancel-workflow-form";
import { CreateEvaluationComparisonForm } from "./create-evaluation-comparison-form";
import { RunAnalystForm } from "./run-analyst-form";
import { RunBaselineForm } from "./run-baseline-form";
import { RunClassifierForm } from "./run-classifier-form";
import { RunInsightForm } from "./run-insight-form";
import { RunReviewerForm } from "./run-reviewer-form";
import { RunRootCauseForm } from "./run-root-cause-form";
import { RunTimelineForm } from "./run-timeline-form";
import { RunWriterForm } from "./run-writer-form";

function formatLatency(value: number | null): string {
  if (value == null) return "-";
  if (value < 1000) return `${value}ms`;
  return `${(value / 1000).toFixed(2)}s`;
}

function formatCost(value: number | null): string {
  return value != null ? `$${value.toFixed(6)}` : "-";
}

function formatQuality(value: number | null): string {
  return value != null ? `${Math.round(value * 100)}%` : "-";
}

function formatWorkflowType(value: string): string {
  const labels: Record<string, string> = {
    sales_report: "Sales report",
    customer_feedback: "Customer feedback",
    incident_log: "Incident log",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function formatRunMode(value: string): string {
  const labels: Record<string, string> = {
    multi_agent: "Multi-agent",
    baseline: "Baseline",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function formatRunStatus(value: string): string {
  const labels: Record<string, string> = {
    created: "Created",
    running: "Running",
    routing: "Routing",
    analyst_running: "Analyst running",
    reviewer_running: "Reviewer running",
    retrying: "Retrying",
    waiting_for_human: "Waiting for human approval",
    writer_running: "Writer running",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function formatTokens(step: AgentStep): string {
  if (step.total_tokens != null) return step.total_tokens.toLocaleString();
  if (step.tokens_input != null || step.tokens_output != null) {
    return `${step.tokens_input ?? 0} in / ${step.tokens_output ?? 0} out`;
  }
  return "-";
}

function getStatusClass(status: AgentStep["status"]): string {
  switch (status) {
    case "completed":
      return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300";
    case "running":
      return "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300";
    case "failed":
      return "border-destructive/30 bg-destructive/10 text-destructive";
    default:
      return "border-border bg-muted text-muted-foreground";
  }
}

function getOutputPreview(step: AgentStep): string {
  if (step.output_json) return JSON.stringify(step.output_json, null, 2);
  if (step.error_message) return step.error_message;
  return "No output recorded yet.";
}

function formatEventType(value: WorkflowEvent["event_type"]): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getEventClass(eventType: WorkflowEvent["event_type"]): string {
  if (eventType.endsWith("failed") || eventType === "human_rejected") {
    return "border-destructive/30 bg-destructive/10 text-destructive";
  }
  if (eventType === "workflow_cancelled") {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300";
  }
  if (
    eventType === "workflow_completed" ||
    eventType === "agent_completed" ||
    eventType === "human_approved"
  ) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300";
  }
  if (
    eventType === "retry_triggered" ||
    eventType === "reviewer_rejected_output" ||
    eventType === "human_approval_required" ||
    eventType === "human_requested_retry"
  ) {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300";
  }
  return "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300";
}

function getRecoveryMessages(runStatus: string, steps: AgentStep[], events: WorkflowEvent[]) {
  const messages = [
    ...steps
      .filter((step) => step.status === "failed" && step.error_message)
      .map((step) => `${step.agent_name}: ${step.error_message}`),
    ...events
      .filter((event) => event.error_message)
      .map((event) => `${formatEventType(event.event_type)}: ${event.error_message}`),
  ];

  if (runStatus === "cancelled" && messages.length === 0) {
    messages.push("Workflow was cancelled before it completed.");
  }
  if (runStatus === "failed" && messages.length === 0) {
    messages.push("Workflow failed. Check the event timeline and agent steps for details.");
  }
  return Array.from(new Set(messages));
}

function getStructuredPromotionAgentType(workflowType: string): string {
  if (workflowType === "customer_feedback") return "insight";
  if (workflowType === "incident_log") return "root_cause";
  return "analyst";
}

function hasHumanApprovedEvent(events: WorkflowEvent[]): boolean {
  return events.some((event) => event.event_type === "human_approved");
}

function hasEvent(events: WorkflowEvent[], eventType: WorkflowEvent["event_type"]): boolean {
  return events.some((event) => event.event_type === eventType);
}

type LineageStage = {
  agentType?: string;
  eventType?: string;
  label: string;
};

function getWorkflowLineage(workflowType: string): LineageStage[] {
  if (workflowType === "customer_feedback") {
    return [
      { label: "Classifier", agentType: "classifier" },
      { label: "Insight Agent", agentType: "insight" },
      { label: "Reviewer", agentType: "reviewer" },
      { label: "Human Approval", eventType: "human_approved" },
      { label: "Writer", agentType: "writer" },
    ];
  }
  if (workflowType === "incident_log") {
    return [
      { label: "Timeline", agentType: "timeline" },
      { label: "Root Cause", agentType: "root_cause" },
      { label: "Reviewer", agentType: "reviewer" },
      { label: "Human Approval", eventType: "human_approved" },
      { label: "Writer", agentType: "writer" },
    ];
  }
  return [
    { label: "Analyst", agentType: "analyst" },
    { label: "Reviewer", agentType: "reviewer" },
    { label: "Human Approval", eventType: "human_approved" },
    { label: "Writer", agentType: "writer" },
  ];
}

function getAgentContribution(step: AgentStep): string {
  const output = step.output_json ?? {};
  if (step.agent_type === "classifier") {
    const themes = Array.isArray(output.themes) ? output.themes.length : 0;
    const bugReports = Array.isArray(output.bug_reports)
      ? output.bug_reports.length
      : 0;
    return `Grouped source feedback into ${themes} theme${themes === 1 ? "" : "s"} and ${bugReports} bug report${bugReports === 1 ? "" : "s"}.`;
  }
  if (step.agent_type === "insight") {
    const recommendations = Array.isArray(output.recommendations)
      ? output.recommendations.length
      : 0;
    return `Generated ${recommendations} evidence-backed recommendation${recommendations === 1 ? "" : "s"} for product review.`;
  }
  if (step.agent_type === "reviewer") {
    const issues = Array.isArray(output.issues) ? output.issues.length : 0;
    const approved = output.approved === true ? "approved" : "reviewed";
    return `Reviewer ${approved} factual support with ${issues} blocking issue${issues === 1 ? "" : "s"}.`;
  }
  if (step.agent_type === "writer") {
    return "Produced the final business report from reviewed workflow analysis.";
  }
  if (step.agent_type === "analyst") {
    return "Extracted structured findings, risks, recommendations, and evidence.";
  }
  if (step.agent_type === "baseline") {
    return "Generated the single-agent baseline output for comparison.";
  }
  if (step.agent_type === "timeline") {
    const timeline = Array.isArray(output.timeline) ? output.timeline.length : 0;
    const ambiguous = Array.isArray(output.ambiguous_events)
      ? output.ambiguous_events.length
      : 0;
    return `Extracted ${timeline} timestamped incident event${timeline === 1 ? "" : "s"} with source evidence${ambiguous > 0 ? ` and flagged ${ambiguous} ambiguous event${ambiguous === 1 ? "" : "s"}` : ""}.`;
  }
  if (step.agent_type === "root_cause") {
    const facts = Array.isArray(output.confirmed_facts)
      ? output.confirmed_facts.length
      : 0;
    const causes = Array.isArray(output.likely_causes)
      ? output.likely_causes.length
      : 0;
    const unknowns = Array.isArray(output.unknowns) ? output.unknowns.length : 0;
    const actions = Array.isArray(output.follow_up_actions)
      ? output.follow_up_actions.length
      : 0;
    return `Separated ${facts} confirmed fact${facts === 1 ? "" : "s"}, ${causes} likely cause${causes === 1 ? "" : "s"}, ${unknowns} unknown${unknowns === 1 ? "" : "s"}, and ${actions} follow-up action${actions === 1 ? "" : "s"}.`;
  }
  return "Completed this workflow step and recorded trace data.";
}

function inputIncludesExpectedThemes(rawText: string): boolean {
  return rawText.toLowerCase().includes("expected themes:");
}

function MetricCell({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}

function MetricGroup({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <p className="text-xs font-semibold text-muted-foreground">{title}</p>
      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
        {children}
      </div>
    </div>
  );
}

function ExpandAffordance({ label = "Expand details" }: { label?: string }) {
  return (
    <span className="inline-flex w-fit items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium transition-colors group-open:bg-muted group-hover:bg-muted">
      {label}
      <ChevronDown
        aria-hidden="true"
        className="h-4 w-4 transition-transform group-open:rotate-180"
      />
    </span>
  );
}

function RecoverySummary({
  status,
  messages,
}: {
  status: string;
  messages: string[];
}) {
  if (status !== "failed" && status !== "cancelled" && messages.length === 0) {
    return null;
  }

  return (
    <section className="mt-6 rounded-lg border border-destructive/30 bg-destructive/10 p-4">
      <h2 className="text-lg font-semibold">
        {status === "cancelled" ? "Workflow Cancelled" : "Workflow Needs Attention"}
      </h2>
      <ul className="mt-3 space-y-2 text-sm text-destructive">
        {messages.map((message) => (
          <li key={message}>{message}</li>
        ))}
      </ul>
    </section>
  );
}

function WorkflowLineage({
  agentSteps,
  events,
  status,
  workflowType,
}: {
  agentSteps: AgentStep[];
  events: WorkflowEvent[];
  status: string;
  workflowType: string;
}) {
  const steps = getWorkflowLineage(workflowType);
  const completedStageKeys = new Set(
    steps
      .filter((step) =>
        step.agentType
          ? agentSteps.some(
              (agentStep) =>
                agentStep.agent_type === step.agentType &&
                agentStep.status === "completed",
            )
          : step.eventType
            ? hasEvent(events, step.eventType as WorkflowEvent["event_type"])
            : false,
      )
      .map((step) => step.label),
  );
  const failedAgentTypes = new Set(
    agentSteps
      .filter((step) => step.status === "failed")
      .map((step) => step.agent_type),
  );
  const firstIncompleteIndex = steps.findIndex(
    (step) => !completedStageKeys.has(step.label),
  );

  return (
    <section className="mt-4 rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <h2 className="text-sm font-semibold">Workflow Lineage</h2>
        <ol className="flex flex-wrap items-center gap-2">
          {steps.map((step, index) => {
            const isComplete = completedStageKeys.has(step.label);
            const isFailed =
              step.agentType !== undefined && failedAgentTypes.has(step.agentType);
            const isCurrent =
              !isComplete &&
              !isFailed &&
              index === firstIncompleteIndex &&
              !["cancelled", "completed", "failed"].includes(status);
            const tone = isComplete
              ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200"
              : isFailed
                ? "border-destructive/30 bg-destructive/10 text-destructive"
                : isCurrent
                  ? "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-200"
                  : "border-border bg-muted text-muted-foreground";
            const stepStatus = isComplete
              ? "Complete"
              : isFailed
                ? "Failed"
                : isCurrent
                  ? "Current"
                  : "Pending";

            return (
              <li key={step.label} className="flex items-center gap-2">
                <span
                  className={`rounded-full border px-3 py-1.5 text-sm font-medium ${tone}`}
                >
                  {step.label} <span className="text-xs">{stepStatus}</span>
                </span>
                {index < steps.length - 1 && (
                  <span
                    aria-hidden="true"
                    className="hidden h-7 w-7 items-center justify-center rounded-full border border-border bg-background text-sm font-semibold text-muted-foreground sm:inline-flex"
                  >
                    <ArrowRight size={14} strokeWidth={2.25} />
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

function CompletedRunSummary({
  canCreateEvaluationComparison,
  runId,
  status,
}: {
  canCreateEvaluationComparison: boolean;
  runId: string;
  status: string;
}) {
  const isCompleted = status === "completed";

  return (
    <section className="mt-6 rounded-lg border border-border bg-card p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">
            Run outcome
          </p>
          <h2 className="mt-2 text-xl font-semibold">
            {isCompleted
              ? "Workflow completed. Final report is ready."
              : `Workflow is ${formatRunStatus(status).toLowerCase()}.`}
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            Review the business output first, then expand source input, event
            logs, and agent JSON when you need trace details.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row lg:justify-end">
          {isCompleted && (
            <Link
              href={`/workflow-runs/${runId}/final-output`}
              className="rounded-md bg-primary px-4 py-2 text-center text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              View Final Output
            </Link>
          )}
          {canCreateEvaluationComparison && (
            <CreateEvaluationComparisonForm compact runId={runId} />
          )}
        </div>
      </div>
    </section>
  );
}

function CompactMetricStrip({
  completedAt,
  createdAt,
  latency,
  mode,
  qualityScore,
  retryCount,
  status,
  tokens,
  totalCost,
  type,
}: {
  completedAt: string | null;
  createdAt: string;
  latency: number | null;
  mode: string;
  qualityScore: number | null;
  retryCount: number;
  status: string;
  tokens: number | null;
  totalCost: number | null;
  type: string;
}) {
  return (
    <section className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_1fr_1.2fr]">
      <MetricGroup title="Run">
        <MetricCell label="Status" value={formatRunStatus(status)} />
        <MetricCell label="Workflow" value={formatWorkflowType(type)} />
        <MetricCell label="Mode" value={formatRunMode(mode)} />
        <MetricCell label="Retries" value={String(retryCount)} />
      </MetricGroup>
      <MetricGroup title="Performance">
        <MetricCell label="Quality" value={formatQuality(qualityScore)} />
        <MetricCell label="Latency" value={formatLatency(latency)} />
        <MetricCell label="Cost" value={formatCost(totalCost)} />
        <MetricCell
          label="Tokens"
          value={tokens != null ? tokens.toLocaleString() : "-"}
        />
      </MetricGroup>
      <MetricGroup title="Timing">
        <MetricCell label="Created" value={<LocalDateTime value={createdAt} />} />
        <MetricCell
          label="Completed"
          value={completedAt ? <LocalDateTime value={completedAt} /> : "-"}
        />
      </MetricGroup>
    </section>
  );
}

function OutcomeSummary({
  agentSteps,
  events,
  hasFinalOutput,
  usedHumanApprovedAnalysis,
  workflowType,
}: {
  agentSteps: AgentStep[];
  events: WorkflowEvent[];
  hasFinalOutput: boolean;
  usedHumanApprovedAnalysis: boolean;
  workflowType: string;
}) {
  const reviewerStep = agentSteps
    .filter((step) => step.agent_type === "reviewer" && step.status === "completed")
    .at(-1);
  const reviewerOutput = reviewerStep?.output_json ?? {};
  const issues = Array.isArray(reviewerOutput.issues)
    ? reviewerOutput.issues.length
    : 0;
  const items = [
    hasFinalOutput ? "Final report generated" : "Final report not generated yet",
    usedHumanApprovedAnalysis
      ? "Writer used reviewed human-approved analysis"
      : "Writer approval trace not recorded",
    hasEvent(events, "human_approved")
      ? workflowType === "incident_log"
        ? "Human confirmed reviewer-approved incident analysis before final report generation"
        : "Human approval completed"
      : "Human approval pending or not required",
    issues === 0
      ? "Reviewer found no blocking issues"
      : `Reviewer found ${issues} issue${issues === 1 ? "" : "s"}`,
  ];

  return (
    <section className="mt-4 rounded-lg border border-border bg-card p-4">
      <h2 className="text-sm font-semibold">Outcome Summary</h2>
      <ul className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
        {items.map((item) => (
          <li key={item} className="rounded-md bg-muted px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function formatMetadata(metadata: WorkflowEvent["metadata_json"]): string {
  if (!metadata || Object.keys(metadata).length === 0) {
    return "No metadata recorded.";
  }
  return JSON.stringify(metadata, null, 2);
}

function getEventAgentName(
  event: WorkflowEvent,
  stepsById: Map<string, AgentStep>,
): string | null {
  if (event.agent_step_id) {
    const step = stepsById.get(event.agent_step_id);
    if (step) return step.agent_name;
  }
  const agentName = event.metadata_json?.agent_name;
  return typeof agentName === "string" ? agentName : null;
}

function WorkflowEventTimeline({
  events,
  steps,
}: {
  events: WorkflowEvent[];
  steps: AgentStep[];
}) {
  const stepsById = new Map(steps.map((step) => [step.id, step]));
  const hasAgentTrace = steps.length > 0;

  return (
    <section className="mt-6">
      {events.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-5">
          <h2 className="text-lg font-semibold">Observability Timeline</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {hasAgentTrace
              ? "No event log rows were recorded for this seeded or imported run. The agent step timeline below still shows the execution trace, costs, latency, prompt versions, and outputs."
              : "No workflow events have been recorded for this workflow run yet."}
          </p>
        </div>
      ) : (
        <details className="group rounded-lg border border-border bg-card p-4 transition-colors hover:border-muted-foreground/40">
          <summary className="cursor-pointer list-none rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Observability Timeline</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Expand to inspect workflow events, timestamps, and metadata.
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:items-end">
                <p className="text-sm text-muted-foreground">
                  {events.length} {events.length === 1 ? "event" : "events"}
                </p>
                <ExpandAffordance />
              </div>
            </div>
          </summary>
          <ol className="mt-4 space-y-4">
            {events.map((event, index) => {
              const agentName = getEventAgentName(event, stepsById);
              return (
                <li key={event.id} className="relative pl-8">
                  {index < events.length - 1 && (
                    <div className="absolute left-2 top-2 h-full w-px bg-border" />
                  )}
                  <div className="absolute left-0 top-2 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-background text-[10px] font-medium">
                    {index + 1}
                  </div>
                  <article className="rounded-lg border border-border bg-card p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="font-semibold">{event.message}</h3>
                        <p className="mt-1 text-sm text-muted-foreground">
                          <LocalDateTime value={event.created_at} />
                          {agentName ? ` - ${agentName}` : ""}
                        </p>
                      </div>
                      <span
                        className={`w-fit rounded-full border px-2.5 py-1 text-xs font-medium ${getEventClass(
                          event.event_type,
                        )}`}
                      >
                        {formatEventType(event.event_type)}
                      </span>
                    </div>

                    {event.error_message && (
                      <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                        {event.error_message}
                      </p>
                    )}

                    <details className="group mt-4">
                      <summary className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted">
                        Metadata
                        <ChevronDown
                          aria-hidden="true"
                          className="h-3.5 w-3.5 transition-transform group-open:rotate-180"
                        />
                      </summary>
                      <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
                        {formatMetadata(event.metadata_json)}
                      </pre>
                    </details>
                  </article>
                </li>
              );
            })}
          </ol>
        </details>
      )}
    </section>
  );
}

function AgentStepTimeline({ steps }: { steps: AgentStep[] }) {
  return (
    <section className="mt-6">
      {steps.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-5 text-sm text-muted-foreground">
          No agent steps have been recorded for this workflow run yet.
        </div>
      ) : (
        <details className="group rounded-lg border border-border bg-card p-4 transition-colors hover:border-muted-foreground/40">
          <summary className="cursor-pointer list-none rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Agent Step Timeline</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Expand to inspect per-agent cost, latency, prompt version, and JSON.
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:items-end">
                <p className="text-sm text-muted-foreground">
                  {steps.length} {steps.length === 1 ? "step" : "steps"}
                </p>
                <ExpandAffordance />
              </div>
            </div>
          </summary>
          <ol className="mt-4 space-y-4">
            {steps.map((step, index) => (
              <li key={step.id} className="relative pl-8">
                {index < steps.length - 1 && (
                  <div className="absolute left-2 top-2 h-full w-px bg-border" />
                )}
                <div className="absolute left-0 top-2 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-background text-[10px] font-medium">
                  {step.step_order}
                </div>
                <article className="rounded-lg border border-border bg-card p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h3 className="font-semibold">{step.agent_name}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {getAgentContribution(step)}
                      </p>
                    </div>
                    <span
                      className={`w-fit rounded-full border px-2.5 py-1 text-xs font-medium ${getStatusClass(
                        step.status,
                      )}`}
                    >
                      {step.status}
                    </span>
                  </div>

                  <dl className="mt-4 grid grid-cols-2 gap-3 text-sm lg:grid-cols-4">
                    <div>
                      <dt className="text-xs text-muted-foreground">Latency</dt>
                      <dd className="mt-1 font-medium">
                        {formatLatency(step.latency_ms)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Model</dt>
                      <dd className="mt-1 truncate font-medium">{step.model ?? "-"}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Tokens</dt>
                      <dd className="mt-1 font-medium">{formatTokens(step)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Cost</dt>
                      <dd className="mt-1 font-medium">{formatCost(step.cost)}</dd>
                    </div>
                  </dl>

                  {step.error_message && (
                    <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                      {step.error_message}
                    </p>
                  )}

                  <details className="group mt-4 rounded-md border border-border bg-muted p-3">
                    <summary className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted">
                      View agent JSON and prompt metadata
                      <ChevronDown
                        aria-hidden="true"
                        className="h-3.5 w-3.5 transition-transform group-open:rotate-180"
                      />
                    </summary>
                    <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="text-xs text-muted-foreground">Started</dt>
                        <dd className="mt-1 font-medium">
                          <LocalDateTime value={step.created_at} />
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">Completed</dt>
                        <dd className="mt-1 font-medium">
                          <LocalDateTime value={step.completed_at} />
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">
                          Retry Count
                        </dt>
                        <dd className="mt-1 font-medium">{step.retry_count}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-foreground">
                          Prompt Version
                        </dt>
                        <dd className="mt-1 truncate font-mono text-xs">
                          {step.prompt_version_id ?? "-"}
                        </dd>
                      </div>
                    </dl>
                    <pre className="mt-3 max-h-80 overflow-auto rounded-md bg-background p-3 text-sm whitespace-pre-wrap">
                      {getOutputPreview(step)}
                    </pre>
                  </details>
                </article>
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}

export default async function WorkflowRunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const run = await getWorkflowRun(id);

  if (!run) notFound();

  const uploadedInput = run.input_id ? await getUploadedInput(run.input_id) : null;
  const isMissingLinkedInput = run.input_id !== null && uploadedInput === null;
  const agentSteps = await listAgentSteps(run.id);
  const workflowEvents = await listWorkflowEvents(run.id);
  const recoveryMessages = getRecoveryMessages(run.status, agentSteps, workflowEvents);
  const humanApprovals =
    run.status === "waiting_for_human" ? await listHumanApprovals() : [];
  const pendingApproval = humanApprovals.find(
    (approval) =>
      approval.workflow_run_id === run.id && approval.status === "pending",
  );
  const latestCompletedAnalystStep = agentSteps
    .filter((step) => step.agent_type === "analyst" && step.status === "completed")
    .at(-1);
  const latestCompletedClassifierStep = agentSteps
    .filter(
      (step) => step.agent_type === "classifier" && step.status === "completed",
    )
    .at(-1);
  const latestCompletedInsightStep = agentSteps
    .filter((step) => step.agent_type === "insight" && step.status === "completed")
    .at(-1);
  const latestCompletedTimelineStep = agentSteps
    .filter((step) => step.agent_type === "timeline" && step.status === "completed")
    .at(-1);
  const latestCompletedRootCauseStep = agentSteps
    .filter((step) => step.agent_type === "root_cause" && step.status === "completed")
    .at(-1);
  const reviewerSourceStep =
    run.workflow_type === "customer_feedback"
      ? latestCompletedInsightStep
      : run.workflow_type === "incident_log"
        ? latestCompletedRootCauseStep
      : latestCompletedAnalystStep;
  const reviewerSourceInputKey =
    run.workflow_type === "customer_feedback"
      ? "insight_step_id"
      : run.workflow_type === "incident_log"
        ? "root_cause_step_id"
      : "analyst_step_id";
  const canRunAnalyst =
    (run.status === "created" || run.status === "retrying") &&
    run.workflow_type === "sales_report" &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null;
  const canRunBaseline =
    run.status === "created" &&
    run.run_mode === "baseline" &&
    uploadedInput !== null &&
    !agentSteps.some(
      (step) =>
        step.agent_type === "baseline" &&
        (step.status === "running" || step.status === "completed"),
    );
  const canRunClassifier =
    run.status === "created" &&
    run.workflow_type === "customer_feedback" &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null &&
    !agentSteps.some(
      (step) =>
        step.agent_type === "classifier" &&
        (step.status === "running" || step.status === "completed"),
    );
  const canRunInsight =
    run.status === "running" &&
    run.workflow_type === "customer_feedback" &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null &&
    latestCompletedClassifierStep !== undefined &&
    !agentSteps.some(
      (step) =>
        step.agent_type === "insight" &&
        (step.status === "running" || step.status === "completed"),
    );
  const canRunTimeline =
    run.status === "created" &&
    run.workflow_type === "incident_log" &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null &&
    !agentSteps.some(
      (step) =>
        step.agent_type === "timeline" &&
        (step.status === "running" || step.status === "completed"),
    );
  const canRunRootCause =
    run.status === "running" &&
    run.workflow_type === "incident_log" &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null &&
    latestCompletedTimelineStep !== undefined &&
    !agentSteps.some(
      (step) =>
        step.agent_type === "root_cause" &&
        (step.status === "running" || step.status === "completed"),
    );
  const canRunReviewer =
    run.status === "reviewer_running" &&
    (run.workflow_type === "sales_report" ||
      run.workflow_type === "customer_feedback" ||
      run.workflow_type === "incident_log") &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null &&
    reviewerSourceStep !== undefined &&
    !agentSteps.some(
      (step) =>
        step.agent_type === "reviewer" &&
        (step.status === "running" || step.status === "completed") &&
        step.input_json?.[reviewerSourceInputKey] === reviewerSourceStep.id,
    );
  const canRunWriter =
    run.status === "writer_running" &&
    (run.workflow_type === "sales_report" ||
      run.workflow_type === "customer_feedback" ||
      run.workflow_type === "incident_log") &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null &&
    !agentSteps.some(
      (step) =>
        step.agent_type === "writer" &&
        (step.status === "running" || step.status === "completed"),
    );
  const promotionAgentType = getStructuredPromotionAgentType(run.workflow_type);
  const hasPromotionStructuredStep = agentSteps.some(
    (step) =>
      step.agent_type === promotionAgentType &&
      step.status === "completed" &&
      step.output_json !== null,
  );
  const canCreateEvaluationComparison =
    run.status === "completed" &&
    uploadedInput !== null &&
    (run.run_mode === "baseline" ||
      (run.run_mode === "multi_agent" && hasPromotionStructuredStep));
  const canCancelWorkflow = !["completed", "failed", "cancelled"].includes(run.status);
  const usedHumanApprovedAnalysis =
    run.final_output !== null && hasHumanApprovedEvent(workflowEvents);
  const workflowTitle = uploadedInput?.title ?? run.input_title;

  return (
    <div>
      <Link
        href="/workflow-runs"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        Workflow Runs
      </Link>

      <h1 className="mt-4 text-2xl font-bold tracking-tight">
        {workflowTitle ? `Workflow Run of ${workflowTitle}` : "Workflow Run"}
      </h1>

      {canRunAnalyst && (
        <RunAnalystForm runId={run.id} />
      )}

      {canRunBaseline && <RunBaselineForm runId={run.id} />}

      {canRunClassifier && <RunClassifierForm runId={run.id} />}

      {canRunInsight && <RunInsightForm runId={run.id} />}

      {canRunTimeline && <RunTimelineForm runId={run.id} />}

      {canRunRootCause && <RunRootCauseForm runId={run.id} />}

      {canRunReviewer && <RunReviewerForm runId={run.id} />}

      {canRunWriter && <RunWriterForm runId={run.id} />}

      {pendingApproval && (
        <div className="mt-4">
          <Link
            href={`/human-approvals/${pendingApproval.id}`}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Review Approval
          </Link>
        </div>
      )}

      {canCancelWorkflow && <CancelWorkflowForm runId={run.id} />}

      <RecoverySummary status={run.status} messages={recoveryMessages} />

      <CompletedRunSummary
        canCreateEvaluationComparison={canCreateEvaluationComparison}
        runId={run.id}
        status={run.status}
      />

      <CompactMetricStrip
        completedAt={run.completed_at}
        createdAt={run.created_at}
        latency={run.latency_ms}
        mode={run.run_mode}
        qualityScore={run.quality_score}
        retryCount={run.retry_count}
        status={run.status}
        tokens={run.total_tokens}
        totalCost={run.total_cost}
        type={run.workflow_type}
      />

      <WorkflowLineage
        agentSteps={agentSteps}
        events={workflowEvents}
        status={run.status}
        workflowType={run.workflow_type}
      />

      <OutcomeSummary
        agentSteps={agentSteps}
        events={workflowEvents}
        hasFinalOutput={run.final_output !== null}
        usedHumanApprovedAnalysis={usedHumanApprovedAnalysis}
        workflowType={run.workflow_type}
      />

      {run.final_output && (
        <section className="mt-6 rounded-lg border border-border bg-card p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Final Output Preview</h2>
              {usedHumanApprovedAnalysis && (
                <p className="mt-1 text-sm text-muted-foreground">
                  Writer output generated after human approval, using the
                  reviewed analysis as the source of truth.
                </p>
              )}
            </div>
            <Link
              href={`/workflow-runs/${run.id}/final-output`}
              className="w-fit rounded-md border border-border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-muted"
            >
              Open full report
            </Link>
          </div>
          <pre className="mt-4 max-h-72 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
            {run.final_output}
          </pre>
        </section>
      )}

      {uploadedInput && (
        <section className="mt-6">
          {inputIncludesExpectedThemes(uploadedInput.raw_text) && (
            <p className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              Demo note: this stored input includes expected themes. That is
              useful for evaluation cases, but live recruiter demos are more
              trustworthy when the workflow input contains only source feedback.
            </p>
          )}
          <details className="group rounded-lg border border-border bg-card p-4 transition-colors hover:border-muted-foreground/40">
            <summary className="cursor-pointer list-none rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold">Source Input</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {uploadedInput.title}
                  </p>
                </div>
                <div className="flex flex-col gap-2 sm:items-end">
                  {uploadedInput.file_name && (
                    <p className="text-xs text-muted-foreground">
                      {uploadedInput.file_name}
                    </p>
                  )}
                  <ExpandAffordance label="View source" />
                </div>
              </div>
            </summary>
            {uploadedInput.notes && (
              <p className="mt-3 text-sm text-muted-foreground">
                {uploadedInput.notes}
              </p>
            )}
            <pre className="mt-4 max-h-96 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
              {uploadedInput.raw_text}
            </pre>
          </details>
        </section>
      )}

      {isMissingLinkedInput && (
        <section className="mt-6 rounded-lg border border-destructive/30 bg-destructive/10 p-4">
          <h2 className="text-lg font-semibold">Input Missing</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            This workflow references an uploaded input that could not be found.
            Agents cannot run until the input relationship is repaired.
          </p>
        </section>
      )}

      <WorkflowEventTimeline events={workflowEvents} steps={agentSteps} />

      <AgentStepTimeline steps={agentSteps} />
    </div>
  );
}
