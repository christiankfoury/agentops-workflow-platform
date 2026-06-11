import { redirect } from "next/navigation";
import { createUploadedInput, createWorkflowRun } from "@/lib/api";
import type { RunMode } from "@/lib/types";

const allowedFileExtensions = [".txt", ".md"];
const maxUploadBytes = 250 * 1024;

function cleanOptional(value: FormDataEntryValue | null): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

async function readInputText(formData: FormData): Promise<{
  rawText: string;
  fileName: string | null;
  fileType: string | null;
  fileSize: number | null;
}> {
  const file = formData.get("input_file");
  if (file instanceof File && file.size > 0) {
    if (file.size > maxUploadBytes) {
      throw new Error("Uploaded file must be 250 KB or smaller.");
    }

    const fileName = file.name;
    const lowerFileName = fileName.toLowerCase();
    const isAllowed = allowedFileExtensions.some((extension) =>
      lowerFileName.endsWith(extension),
    );

    if (!isAllowed) {
      throw new Error("Only .txt and .md uploads are supported.");
    }

    const rawText = (await file.text()).trim();
    if (rawText.length === 0) {
      throw new Error("Uploaded file is empty.");
    }

    return {
      rawText,
      fileName,
      fileType: file.type || null,
      fileSize: file.size,
    };
  }

  const pastedText = cleanOptional(formData.get("raw_text"));
  if (pastedText === null) {
    throw new Error("Paste sales report text or upload a .txt/.md file.");
  }

  return {
    rawText: pastedText,
    fileName: null,
    fileType: null,
    fileSize: null,
  };
}

async function handleCreate(formData: FormData) {
  "use server";

  const title = cleanOptional(formData.get("title"));
  if (title === null) {
    throw new Error("Input title is required.");
  }

  const input = await readInputText(formData);
  const uploadedInput = await createUploadedInput({
    title,
    input_type: "sales_report",
    raw_text: input.rawText,
    notes: cleanOptional(formData.get("notes")),
    file_name: input.fileName,
    file_type: input.fileType,
    file_size: input.fileSize,
  });

  const run = await createWorkflowRun({
    workflow_type: "sales_report",
    run_mode: formData.get("run_mode") as RunMode,
    input_id: uploadedInput.id,
  });

  redirect(`/workflow-runs/${run.id}`);
}

export default function NewWorkflowPage() {
  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold tracking-tight">New Sales Workflow</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Store a sales report input for the upcoming agent pipeline.
      </p>

      <form action={handleCreate} className="mt-6 space-y-5">
        <div>
          <label htmlFor="title" className="block text-sm font-medium">
            Input Title
          </label>
          <input
            id="title"
            name="title"
            type="text"
            required
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Q1 Sales Report"
          />
        </div>

        <div>
          <label htmlFor="raw_text" className="block text-sm font-medium">
            Sales Report Text
          </label>
          <textarea
            id="raw_text"
            name="raw_text"
            rows={10}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Paste revenue, regional performance, churn notes, pipeline updates..."
          />
        </div>

        <div>
          <label htmlFor="input_file" className="block text-sm font-medium">
            Upload Text File
          </label>
          <input
            id="input_file"
            name="input_file"
            type="file"
            accept=".txt,.md,text/plain,text/markdown"
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-1.5 file:text-sm"
          />
        </div>

        <div>
          <label htmlFor="notes" className="block text-sm font-medium">
            Notes
          </label>
          <textarea
            id="notes"
            name="notes"
            rows={3}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Optional context for this run"
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
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="multi_agent">Multi-Agent</option>
            <option value="baseline">Baseline</option>
          </select>
        </div>

        <button
          type="submit"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Create Workflow Run
        </button>
      </form>
    </div>
  );
}
