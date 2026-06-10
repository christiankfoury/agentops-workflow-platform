import Link from "next/link";
import { notFound } from "next/navigation";
import { getWorkflowRun } from "@/lib/api";

export default async function WorkflowRunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const run = await getWorkflowRun(id);

  if (!run) notFound();

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
