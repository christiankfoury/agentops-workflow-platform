import Link from "next/link";
import { notFound } from "next/navigation";
import { getUploadedInput, getWorkflowRun, listAgentSteps } from "@/lib/api";
import type { AgentStep } from "@/lib/types";
import { RunAnalystForm } from "./run-analyst-form";
import { RunReviewerForm } from "./run-reviewer-form";

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

function formatLatency(value: number | null): string {
  if (value == null) return "-";
  if (value < 1000) return `${value}ms`;
  return `${(value / 1000).toFixed(2)}s`;
}

function formatCost(value: number | null): string {
  return value != null ? `$${value.toFixed(6)}` : "-";
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

function AgentStepTimeline({ steps }: { steps: AgentStep[] }) {
  return (
    <section className="mt-6">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <h2 className="text-lg font-semibold">Agent Step Timeline</h2>
        <p className="text-sm text-muted-foreground">
          {steps.length} {steps.length === 1 ? "step" : "steps"}
        </p>
      </div>

      {steps.length === 0 ? (
        <div className="mt-3 rounded-lg border border-dashed border-border p-5 text-sm text-muted-foreground">
          No agent steps have been recorded for this workflow run yet.
        </div>
      ) : (
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
                      {step.agent_type}
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

                <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <dt className="text-xs text-muted-foreground">Started</dt>
                    <dd className="mt-1 font-medium">
                      {formatDateTime(step.created_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Completed</dt>
                    <dd className="mt-1 font-medium">
                      {formatDateTime(step.completed_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Latency</dt>
                    <dd className="mt-1 font-medium">
                      {formatLatency(step.latency_ms)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Model</dt>
                    <dd className="mt-1 font-medium">{step.model ?? "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Tokens</dt>
                    <dd className="mt-1 font-medium">{formatTokens(step)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Cost</dt>
                    <dd className="mt-1 font-medium">
                      {formatCost(step.cost)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Retry Count</dt>
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

                {step.error_message && (
                  <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                    {step.error_message}
                  </p>
                )}

                <div className="mt-4">
                  <p className="text-xs font-medium text-muted-foreground">
                    Output Preview
                  </p>
                  <pre className="mt-2 max-h-80 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
                    {getOutputPreview(step)}
                  </pre>
                </div>
              </article>
            </li>
          ))}
        </ol>
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
  const latestCompletedAnalystStep = agentSteps
    .filter((step) => step.agent_type === "analyst" && step.status === "completed")
    .at(-1);
  const canRunAnalyst =
    (run.status === "created" || run.status === "retrying") &&
    run.workflow_type === "sales_report" &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null;
  const canRunReviewer =
    run.status === "reviewer_running" &&
    run.workflow_type === "sales_report" &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null &&
    latestCompletedAnalystStep !== undefined &&
    !agentSteps.some(
      (step) =>
        step.agent_type === "reviewer" &&
        (step.status === "running" || step.status === "completed") &&
        step.input_json?.analyst_step_id === latestCompletedAnalystStep.id,
    );

  const fields = [
    { label: "Status", value: run.status },
    { label: "Type", value: run.workflow_type },
    { label: "Mode", value: run.run_mode },
    { label: "Retry Count", value: String(run.retry_count) },
    {
      label: "Quality Score",
      value: run.quality_score != null ? String(run.quality_score) : "—",
    },
    {
      label: "Total Cost",
      value: run.total_cost != null ? `$${run.total_cost.toFixed(6)}` : "—",
    },
    {
      label: "Total Tokens",
      value: run.total_tokens != null ? String(run.total_tokens) : "—",
    },
    {
      label: "Latency",
      value: run.latency_ms != null ? `${run.latency_ms}ms` : "—",
    },
    { label: "Created", value: new Date(run.created_at).toLocaleString() },
    {
      label: "Completed",
      value: run.completed_at
        ? new Date(run.completed_at).toLocaleString()
        : "—",
    },
  ];

  return (
    <div>
      <Link
        href="/workflow-runs"
        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        ← Workflow Runs
      </Link>

      <h1 className="mt-4 text-2xl font-bold tracking-tight">Workflow Run</h1>
      <p className="font-mono text-sm text-muted-foreground">{run.id}</p>

      {canRunAnalyst && (
        <RunAnalystForm runId={run.id} />
      )}

      {canRunReviewer && <RunReviewerForm runId={run.id} />}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {fields.map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg border border-border bg-card p-4"
          >
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="mt-1 font-medium">{value}</p>
          </div>
        ))}
      </div>

      {uploadedInput && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold">Input</h2>
          <div className="mt-2 rounded-lg border border-border bg-card p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
              <div>
                <p className="font-medium">{uploadedInput.title}</p>
                {uploadedInput.notes && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    {uploadedInput.notes}
                  </p>
                )}
              </div>
              {uploadedInput.file_name && (
                <p className="text-xs text-muted-foreground">
                  {uploadedInput.file_name}
                </p>
              )}
            </div>
            <pre className="mt-4 max-h-96 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
              {uploadedInput.raw_text}
            </pre>
          </div>
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

      <AgentStepTimeline steps={agentSteps} />

      {run.final_output && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold">Final Output</h2>
          <pre className="mt-2 rounded-lg border border-border bg-muted p-4 text-sm whitespace-pre-wrap">
            {run.final_output}
          </pre>
        </div>
      )}
    </div>
  );
}
