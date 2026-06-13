"use client";

import { Search } from "lucide-react";
import { useMemo, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { LocalDateTime } from "@/components/local-date-time";
import type { HumanApproval, WorkflowRun } from "@/lib/types";

export interface HumanApprovalTableRow {
  approval: HumanApproval;
  displayStatus: string;
  run: WorkflowRun | null;
}

function statusClass(status: string): string {
  if (status === "blocked") {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300";
  }
  if (status === "approved") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300";
  }
  if (status === "rejected") {
    return "border-destructive/30 bg-destructive/10 text-destructive";
  }
  if (status === "retry_requested") {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300";
  }
  return "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300";
}

function formatWorkflow(value: string | undefined): string {
  if (value === "customer_feedback") return "Customer Feedback";
  if (value === "incident_log") return "Incident Log";
  if (value === "sales_report") return "Sales Report";
  return "Unknown";
}

function formatStatus(value: string): string {
  if (value === "retry_requested") return "Retry requested";
  if (value === "waiting_for_human") return "Waiting for human approval";
  return value.replaceAll("_", " ");
}

function scoreLabel(value: number | null): string {
  if (value == null) return "-";
  return `${Math.round(value * 100)}%`;
}

function approvalTitle(row: HumanApprovalTableRow): string {
  return row.run?.input_title
    ? `Approval for ${row.run.input_title}`
    : `Approval for ${formatWorkflow(row.run?.workflow_type)} workflow`;
}

function searchableText(row: HumanApprovalTableRow): string {
  return [
    approvalTitle(row),
    formatWorkflow(row.run?.workflow_type),
    row.displayStatus,
    scoreLabel(row.approval.reviewer_score),
    row.approval.human_feedback,
    row.approval.edited_analysis_json ? "edited" : null,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function openApproval(
  router: ReturnType<typeof useRouter>,
  approvalId: string,
): void {
  router.push(`/human-approvals/${approvalId}`);
}

export function HumanApprovalsTable({ rows }: { rows: HumanApprovalTableRow[] }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const filteredRows = useMemo(() => {
    if (!normalizedQuery) return rows;
    return rows.filter((row) => searchableText(row).includes(normalizedQuery));
  }, [normalizedQuery, rows]);

  function handleRowKeyDown(
    event: KeyboardEvent<HTMLTableRowElement>,
    approvalId: string,
  ) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openApproval(router, approvalId);
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Approval Queue</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Search by workflow title, type, status, score, or edit state.
          </p>
        </div>
        <label className="relative block w-full sm:max-w-sm">
          <span className="sr-only">Search human approvals</span>
          <Search
            aria-hidden="true"
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search human approvals..."
            className="w-full rounded-md border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-muted-foreground"
          />
        </label>
      </div>

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Approval</th>
              <th className="px-4 py-3 text-left font-medium">Workflow</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-left font-medium">Reviewer Score</th>
              <th className="px-4 py-3 text-left font-medium">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredRows.map((row) => (
              <tr
                key={row.approval.id}
                role="link"
                tabIndex={0}
                aria-label={`Open ${approvalTitle(row)}`}
                onClick={() => openApproval(router, row.approval.id)}
                onKeyDown={(event) => handleRowKeyDown(event, row.approval.id)}
                className="cursor-pointer transition-colors hover:bg-muted/50 focus:bg-muted/50 focus:outline-none"
              >
                <td className="px-4 py-3">
                  <p className="font-medium">{approvalTitle(row)}</p>
                  {row.approval.edited_analysis_json && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Includes human-edited analysis
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 font-medium">
                  {formatWorkflow(row.run?.workflow_type)}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${statusClass(
                      row.displayStatus,
                    )}`}
                  >
                    {formatStatus(row.displayStatus)}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {scoreLabel(row.approval.reviewer_score)}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  <LocalDateTime value={row.approval.created_at} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredRows.length === 0 && (
          <div className="border-t border-border p-6 text-sm text-muted-foreground">
            No human approvals match your search.
          </div>
        )}
      </div>
    </section>
  );
}
