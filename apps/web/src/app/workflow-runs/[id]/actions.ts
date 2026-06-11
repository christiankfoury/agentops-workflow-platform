"use server";

import { redirect } from "next/navigation";
import { runSalesAnalyst, runSalesReviewer } from "@/lib/api";


export interface RunAnalystState {
  error: string | null;
}


export async function runAnalystAction(
  _previousState: RunAnalystState,
  formData: FormData,
): Promise<RunAnalystState> {
  const runId = formData.get("run_id");
  if (typeof runId !== "string" || runId.length === 0) {
    return { error: "Workflow run id is required." };
  }

  try {
    await runSalesAnalyst(runId);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Failed to run analyst.",
    };
  }

  redirect(`/workflow-runs/${runId}`);
}

export async function runReviewerAction(
  _previousState: RunAnalystState,
  formData: FormData,
): Promise<RunAnalystState> {
  const runId = formData.get("run_id");
  if (typeof runId !== "string" || runId.length === 0) {
    return { error: "Workflow run id is required." };
  }

  try {
    await runSalesReviewer(runId);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Failed to run reviewer.",
    };
  }

  redirect(`/workflow-runs/${runId}`);
}
