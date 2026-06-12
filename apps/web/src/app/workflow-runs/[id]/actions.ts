"use server";

import { redirect } from "next/navigation";
import {
  cancelWorkflowRun,
  createEvaluationComparisonFromRun,
  runSalesAnalyst,
  runSalesBaseline,
  runSalesReviewer,
  runSalesWriter,
} from "@/lib/api";


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

export async function runBaselineAction(
  _previousState: RunAnalystState,
  formData: FormData,
): Promise<RunAnalystState> {
  const runId = formData.get("run_id");
  if (typeof runId !== "string" || runId.length === 0) {
    return { error: "Workflow run id is required." };
  }

  try {
    await runSalesBaseline(runId);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Failed to run baseline.",
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

export async function runWriterAction(
  _previousState: RunAnalystState,
  formData: FormData,
): Promise<RunAnalystState> {
  const runId = formData.get("run_id");
  if (typeof runId !== "string" || runId.length === 0) {
    return { error: "Workflow run id is required." };
  }

  try {
    await runSalesWriter(runId);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Failed to run writer.",
    };
  }

  redirect(`/workflow-runs/${runId}`);
}

export async function cancelWorkflowAction(
  _previousState: RunAnalystState,
  formData: FormData,
): Promise<RunAnalystState> {
  const runId = formData.get("run_id");
  if (typeof runId !== "string" || runId.length === 0) {
    return { error: "Workflow run id is required." };
  }

  try {
    await cancelWorkflowRun(runId);
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Failed to cancel workflow.",
    };
  }

  redirect(`/workflow-runs/${runId}`);
}

export async function createEvaluationComparisonAction(
  _previousState: RunAnalystState,
  formData: FormData,
): Promise<RunAnalystState> {
  const runId = formData.get("run_id");
  if (typeof runId !== "string" || runId.length === 0) {
    return { error: "Workflow run id is required." };
  }

  let comparisonUrl = "";
  try {
    const result = await createEvaluationComparisonFromRun(runId);
    comparisonUrl = result.comparison_url;
  } catch (error) {
    return {
      error:
        error instanceof Error
          ? error.message
          : "Failed to create evaluation comparison.",
    };
  }

  redirect(comparisonUrl);
}
