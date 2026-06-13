"use client";

import { Sparkles } from "lucide-react";
import { useActionState, useState } from "react";
import type { ChangeEvent } from "react";
import { createWorkflow } from "./actions";

const initialState = { error: null };
const previewColumns = ["customer_id", "date", "rating", "feedback", "source"];

function parseCsvLine(line: string): string[] {
  const values: string[] = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      values.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current.trim());
  return values;
}

function parseCsvPreview(value: string): Record<string, string>[] {
  const lines = value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 2) return [];
  const headers = parseCsvLine(lines[0]).map((header) => header.toLowerCase());
  return lines.slice(1, 6).map((line) => {
    const values = parseCsvLine(line);
    return Object.fromEntries(
      headers.map((header, index) => [header, values[index] ?? ""]),
    );
  });
}

export function NewWorkflowForm() {
  const [state, formAction, pending] = useActionState(
    createWorkflow,
    initialState,
  );
  const [csvPreviewRows, setCsvPreviewRows] = useState<Record<string, string>[]>([]);
  const [csvPreviewError, setCsvPreviewError] = useState<string | null>(null);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    setCsvPreviewRows([]);
    setCsvPreviewError(null);
    if (!file || !file.name.toLowerCase().endsWith(".csv")) return;

    const text = await file.text();
    const rows = parseCsvPreview(text);
    if (rows.length === 0) {
      setCsvPreviewError("CSV preview is unavailable.");
      return;
    }
    if (!Object.keys(rows[0]).includes("feedback")) {
      setCsvPreviewError("CSV must include a feedback column.");
      return;
    }
    setCsvPreviewRows(rows);
  }

  return (
    <form
      action={formAction}
      className="rounded-lg border border-border bg-card p-5 shadow-sm"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Workflow details</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Paste source text or attach a supported text file.
          </p>
        </div>
        <span className="w-fit rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
          .txt .md .csv
        </span>
      </div>

      <div className="mt-6 space-y-6">
        <section className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-[minmax(0,1fr)_15rem]">
            <div>
              <label htmlFor="title" className="block text-sm font-medium">
                Input Title
              </label>
              <input
                id="title"
                name="title"
                type="text"
                required
                className="mt-1 h-11 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Q1 Sales Report"
              />
            </div>

            <div>
              <label htmlFor="run_mode" className="block text-sm font-medium">
                Run Mode
              </label>
              <select
                id="run_mode"
                name="run_mode"
                required
                className="mt-1 h-11 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="multi_agent">Multi-Agent</option>
                <option value="baseline">Baseline</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="raw_text" className="block text-sm font-medium">
              Input Text
            </label>
            <textarea
              id="raw_text"
              name="raw_text"
              rows={12}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-3 text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Paste a sales report, customer feedback, or incident log..."
            />
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="input_file" className="block text-sm font-medium">
              Upload Text File
            </label>
            <input
              id="input_file"
              name="input_file"
              type="file"
              accept=".txt,.md,.csv,text/plain,text/markdown,text/csv"
              onChange={handleFileChange}
              className="mt-1 h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-1.5 file:text-sm"
            />
          </div>

          <label className="flex min-h-11 items-center gap-3 self-end rounded-md border border-border bg-muted/40 px-3 py-2 text-sm">
            <input
              type="checkbox"
              name="auto_detect_workflow"
              className="h-4 w-4 rounded border-input"
            />
            <Sparkles className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>Auto-detect workflow type</span>
          </label>
        </section>

        {(csvPreviewRows.length > 0 || csvPreviewError) && (
          <section className="rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold">CSV Preview</h2>
            {csvPreviewError ? (
              <p className="mt-2 text-sm text-destructive">{csvPreviewError}</p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-muted-foreground">
                    <tr>
                      {previewColumns.map((column) => (
                        <th key={column} className="px-2 py-2 font-medium">
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {csvPreviewRows.map((row, index) => (
                      <tr key={`${row.feedback}-${index}`}>
                        {previewColumns.map((column) => (
                          <td
                            key={column}
                            className="max-w-64 px-2 py-2 align-top"
                          >
                            {row[column] || "-"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        <section className="grid grid-cols-1 gap-4 md:grid-cols-[15rem_minmax(0,1fr)]">
          <div>
            <label htmlFor="workflow_type" className="block text-sm font-medium">
              Workflow Type
            </label>
            <select
              id="workflow_type"
              name="workflow_type"
              required
              className="mt-1 h-11 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="sales_report">Sales Report</option>
              <option value="customer_feedback">Customer Feedback</option>
              <option value="incident_log">Incident Log</option>
            </select>
          </div>

          <div>
            <label htmlFor="notes" className="block text-sm font-medium">
              Notes
            </label>
            <textarea
              id="notes"
              name="notes"
              rows={3}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm leading-6 focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Optional context for this run"
            />
          </div>
        </section>

        {state.error && (
          <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {state.error}
          </p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-11 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
        >
          {pending ? "Creating..." : "Create Workflow Run"}
        </button>
      </div>
    </form>
  );
}
