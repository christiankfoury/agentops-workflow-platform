"use client";

import { Search } from "lucide-react";
import { useMemo, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { LocalDateTime } from "@/components/local-date-time";
import type { WorkflowRun } from "@/lib/types";

function formatWorkflow(value: string): string {
  if (value === "customer_feedback") return "Customer Feedback";
  if (value === "incident_log") return "Incident Log";
  return "Sales Report";
}

function formatMode(value: string): string {
  return value === "multi_agent" ? "Multi-Agent" : "Baseline";
}

function statusClass(status: string): string {
  if (status === "completed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300";
  }
  if (status === "failed" || status === "cancelled") {
    return "border-destructive/30 bg-destructive/10 text-destructive";
  }
  if (status === "waiting_for_human" || status === "retrying") {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300";
  }
  return "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300";
}

function searchableText(run: WorkflowRun): string {
  return [
    run.id,
    run.input_title,
    formatWorkflow(run.workflow_type),
    formatMode(run.run_mode),
    run.status,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function openRun(
  router: ReturnType<typeof useRouter>,
  runId: string,
): void {
  router.push(`/workflow-runs/${runId}`);
}

export function WorkflowRunsTable({ runs }: { runs: WorkflowRun[] }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const filteredRuns = useMemo(() => {
    if (!normalizedQuery) return runs;
    return runs.filter((run) => searchableText(run).includes(normalizedQuery));
  }, [normalizedQuery, runs]);

  function handleRowKeyDown(event: KeyboardEvent<HTMLTableRowElement>, runId: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openRun(router, runId);
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Run History</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Search by input title, workflow type, status, mode, or run ID.
          </p>
        </div>
        <label className="relative block w-full sm:max-w-sm">
          <span className="sr-only">Search workflow runs</span>
          <Search
            aria-hidden="true"
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search workflow runs..."
            className="w-full rounded-md border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-muted-foreground"
          />
        </label>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Input</th>
              <th className="px-4 py-3 text-left font-medium">Workflow</th>
              <th className="px-4 py-3 text-left font-medium">Mode</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-left font-medium">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredRuns.map((run) => (
              <tr
                key={run.id}
                role="link"
                tabIndex={0}
                aria-label={`Open workflow run ${run.input_title ?? run.id}`}
                onClick={() => openRun(router, run.id)}
                onKeyDown={(event) => handleRowKeyDown(event, run.id)}
                className="cursor-pointer transition-colors hover:bg-muted/50 focus:bg-muted/50 focus:outline-none"
              >
                <td className="px-4 py-3">
                  <p className="font-medium">
                    {run.input_title ?? "Untitled workflow input"}
                  </p>
                </td>
                <td className="px-4 py-3 font-medium">
                  {formatWorkflow(run.workflow_type)}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatMode(run.run_mode)}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusClass(
                      run.status,
                    )}`}
                  >
                    {run.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  <LocalDateTime value={run.created_at} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredRuns.length === 0 && (
          <div className="border-t border-border p-6 text-sm text-muted-foreground">
            No workflow runs match your search.
          </div>
        )}
      </div>
    </section>
  );
}
