import Link from "next/link";
import { notFound } from "next/navigation";
import { getUploadedInput, getWorkflowRun, listAgentSteps } from "@/lib/api";
import { runAnalystAction } from "./actions";

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
  const analystStep = agentSteps.find((step) => step.agent_type === "analyst");
  const canRunAnalyst =
    run.status === "created" &&
    run.workflow_type === "sales_report" &&
    run.run_mode === "multi_agent" &&
    uploadedInput !== null;

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
        <form action={runAnalystAction} className="mt-4">
          <input type="hidden" name="run_id" value={run.id} />
          <button
            type="submit"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Run Analyst
          </button>
        </form>
      )}

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

      {analystStep && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold">Analyst Output</h2>
          <div className="mt-2 rounded-lg border border-border bg-card p-4">
            <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
              <p>
                <span className="text-muted-foreground">Status:</span>{" "}
                {analystStep.status}
              </p>
              <p>
                <span className="text-muted-foreground">Model:</span>{" "}
                {analystStep.model ?? "-"}
              </p>
              <p>
                <span className="text-muted-foreground">Tokens:</span>{" "}
                {analystStep.total_tokens ?? "-"}
              </p>
            </div>
            {analystStep.error_message && (
              <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm">
                {analystStep.error_message}
              </p>
            )}
            {analystStep.output_json && (
              <pre className="mt-4 max-h-96 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
                {JSON.stringify(analystStep.output_json, null, 2)}
              </pre>
            )}
          </div>
        </section>
      )}

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
