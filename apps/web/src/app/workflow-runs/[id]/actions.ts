"use server";

import { redirect } from "next/navigation";
import { runSalesAnalyst } from "@/lib/api";


export async function runAnalystAction(formData: FormData) {
  const runId = formData.get("run_id");
  if (typeof runId !== "string" || runId.length === 0) {
    throw new Error("Workflow run id is required.");
  }

  await runSalesAnalyst(runId);
  redirect(`/workflow-runs/${runId}`);
}
