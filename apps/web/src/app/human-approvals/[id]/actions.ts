"use server";

import { redirect } from "next/navigation";
import {
  approveHumanApproval,
  editHumanApproval,
  rejectHumanApproval,
  requestHumanApprovalRetry,
} from "@/lib/api";

function getApprovalId(formData: FormData): string {
  const approvalId = formData.get("approval_id");
  if (typeof approvalId !== "string" || approvalId.length === 0) {
    throw new Error("Human approval id is required.");
  }
  return approvalId;
}

function getFeedback(formData: FormData): string | null {
  const feedback = formData.get("human_feedback");
  if (typeof feedback !== "string") return null;
  const trimmed = feedback.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export async function approveAction(formData: FormData) {
  const approvalId = getApprovalId(formData);
  await approveHumanApproval(approvalId, { human_feedback: getFeedback(formData) });
  redirect(`/human-approvals/${approvalId}`);
}

export async function requestRetryAction(formData: FormData) {
  const approvalId = getApprovalId(formData);
  await requestHumanApprovalRetry(approvalId, {
    human_feedback: getFeedback(formData),
  });
  redirect(`/human-approvals/${approvalId}`);
}

export async function rejectAction(formData: FormData) {
  const approvalId = getApprovalId(formData);
  await rejectHumanApproval(approvalId, { human_feedback: getFeedback(formData) });
  redirect(`/human-approvals/${approvalId}`);
}

export async function editAction(formData: FormData) {
  const approvalId = getApprovalId(formData);
  const editedAnalysis = formData.get("edited_analysis_json");
  let editedAnalysisJson: Record<string, unknown> | null = null;

  if (typeof editedAnalysis === "string" && editedAnalysis.trim().length > 0) {
    editedAnalysisJson = JSON.parse(editedAnalysis);
  }

  await editHumanApproval(approvalId, {
    human_feedback: getFeedback(formData),
    edited_analysis_json: editedAnalysisJson,
  });
  redirect(`/human-approvals/${approvalId}`);
}
