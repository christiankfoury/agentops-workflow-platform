"use server";

import { redirect } from "next/navigation";
import { createUploadedInput, createWorkflowRun, detectWorkflowType } from "@/lib/api";
import type { RunMode, WorkflowType } from "@/lib/types";

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

function isWorkflowType(value: FormDataEntryValue | null): value is WorkflowType {
  return (
    value === "sales_report" ||
    value === "customer_feedback" ||
    value === "incident_log"
  );
}

function formatWorkflowType(value: WorkflowType): string {
  if (value === "customer_feedback") return "Customer Feedback";
  if (value === "incident_log") return "Incident Log";
  return "Sales Report";
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
      error: "Paste input text or upload a .txt/.md file.",
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

export async function createWorkflow(
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

  const selectedWorkflowType = formData.get("workflow_type");
  if (!isWorkflowType(selectedWorkflowType)) {
    return { error: "Choose a valid workflow type." };
  }

  const input = await readInputText(formData);
  if (!input.ok) {
    return { error: input.error };
  }

  const notes = cleanOptional(formData.get("notes"));
  let workflowType: WorkflowType = selectedWorkflowType;
  if (formData.get("auto_detect_workflow") === "on") {
    try {
      const detection = await detectWorkflowType({
        title,
        raw_text: input.rawText,
        notes,
      });
      if (detection.recommended_action === "confirm") {
        return {
          error: `Router suggests ${formatWorkflowType(detection.workflow_type)} with ${Math.round(
            detection.confidence * 100,
          )}% confidence. Confirm by selecting that workflow type manually.`,
        };
      }
      if (detection.recommended_action === "manual_required") {
        return {
          error: `Router confidence is ${Math.round(
            detection.confidence * 100,
          )}%. Select a workflow type manually.`,
        };
      }
      workflowType = detection.workflow_type;
    } catch (error) {
      return {
        error:
          error instanceof Error
            ? error.message
            : "Failed to auto-detect workflow type.",
      };
    }
  }

  const uploadedInput = await createUploadedInput({
    title,
    input_type: workflowType,
    raw_text: input.rawText,
    notes,
    file_name: input.fileName,
    file_type: input.fileType,
    file_size: input.fileSize,
  });

  const run = await createWorkflowRun({
    workflow_type: workflowType,
    run_mode: runMode,
    input_id: uploadedInput.id,
  });

  redirect(`/workflow-runs/${run.id}`);
}
