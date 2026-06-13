"use server";

import { redirect } from "next/navigation";
import { createCorrectedEvaluationComparisonRun } from "@/lib/api";

export interface CorrectedRunState {
  error: string | null;
}

export async function createCorrectedRunAction(
  _previousState: CorrectedRunState,
  formData: FormData,
): Promise<CorrectedRunState> {
  const evaluationCaseId = formData.get("evaluation_case_id");
  if (typeof evaluationCaseId !== "string" || evaluationCaseId.length === 0) {
    return { error: "Evaluation case id is required." };
  }

  let comparisonUrl = "";
  try {
    const result = await createCorrectedEvaluationComparisonRun(evaluationCaseId);
    comparisonUrl = result.comparison_url;
  } catch (error) {
    return {
      error:
        error instanceof Error
          ? error.message
          : "Failed to create corrected run.",
    };
  }

  redirect(comparisonUrl);
}
