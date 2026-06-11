"use server";

import { redirect } from "next/navigation";
import { createUploadedInput, createWorkflowRun } from "@/lib/api";
import type { RunMode } from "@/lib/types";

export interface CreateWorkflowFormState {
  error: string | null;
}

const allowedFileExtensions = [".txt", ".md"];
const maxUploadBytes = 250 * 1024;

function cleanOptional(value: FormDataEntryValue | null): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function isRunMode(value: FormDataEntryValue | null): value is RunMode {
  return value === "multi_agent" || value === "baseline";
}

async function readInputText(formData: FormData): Promise<
  | {
      ok: true;
      rawText: string;
      fileName: string | null;
      fileType: string | null;
      fileSize: number | null;
    }
  | { ok: false; error: string }
> {
  const file = formData.get("input_file");
  if (file instanceof File && file.size > 0) {
    if (file.size > maxUploadBytes) {
      return { ok: false, error: "Uploaded file must be 250 KB or smaller." };
    }

    const fileName = file.name;
    const lowerFileName = fileName.toLowerCase();
    const isAllowed = allowedFileExtensions.some((extension) =>
      lowerFileName.endsWith(extension),
    );

    if (!isAllowed) {
      return { ok: false, error: "Only .txt and .md uploads are supported." };
    }

    const rawText = (await file.text()).trim();
    if (rawText.length === 0) {
      return { ok: false, error: "Uploaded file is empty." };
    }

    return {
      ok: true,
      rawText,
      fileName,
      fileType: file.type || null,
      fileSize: file.size,
    };
  }

  const pastedText = cleanOptional(formData.get("raw_text"));
  if (pastedText === null) {
    return {
      ok: false,
      error: "Paste sales report text or upload a .txt/.md file.",
    };
  }

  return {
    ok: true,
    rawText: pastedText,
    fileName: null,
    fileType: null,
    fileSize: null,
  };
}

export async function createSalesWorkflow(
  _previousState: CreateWorkflowFormState,
  formData: FormData,
): Promise<CreateWorkflowFormState> {
  const title = cleanOptional(formData.get("title"));
  if (title === null) {
    return { error: "Input title is required." };
  }

  const runMode = formData.get("run_mode");
  if (!isRunMode(runMode)) {
    return { error: "Choose a valid run mode." };
  }

  const input = await readInputText(formData);
  if (!input.ok) {
    return { error: input.error };
  }

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
    run_mode: runMode,
    input_id: uploadedInput.id,
  });

  redirect(`/workflow-runs/${run.id}`);
}
