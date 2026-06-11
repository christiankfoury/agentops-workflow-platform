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

function getString(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function getLines(formData: FormData, name: string): string[] {
  return getString(formData, name)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function getJsonArray(formData: FormData, name: string): unknown[] {
  const value = getString(formData, name);
  if (!value) return [];
  const parsed = JSON.parse(value);
  if (!Array.isArray(parsed)) {
    throw new Error(`${name} must be a JSON array.`);
  }
  return parsed;
}

function getEditedAnalysis(formData: FormData): Record<string, unknown> {
  const workflowType = getString(formData, "workflow_type");

  if (workflowType === "sales_report") {
    return {
      key_findings: getLines(formData, "analysis_key_findings"),
      risks: getLines(formData, "analysis_risks"),
      opportunities: getLines(formData, "analysis_opportunities"),
      recommendations: getLines(formData, "analysis_recommendations"),
      supporting_evidence: getLines(formData, "analysis_supporting_evidence"),
    };
  }

  if (workflowType === "customer_feedback") {
    return {
      top_insights: getLines(formData, "analysis_top_insights"),
      customer_pain_points: getLines(formData, "analysis_customer_pain_points"),
      feature_requests: getJsonArray(formData, "analysis_feature_requests_json"),
      risks: getLines(formData, "analysis_risks"),
      recommendations: getJsonArray(formData, "analysis_recommendations_json"),
      supporting_examples: getJsonArray(formData, "analysis_supporting_examples_json"),
    };
  }

  if (workflowType === "incident_log") {
    return {
      impact: getJsonArray(formData, "analysis_impact_json"),
      suspected_root_cause: getString(formData, "analysis_suspected_root_cause"),
      confirmed_facts: getJsonArray(formData, "analysis_confirmed_facts_json"),
      likely_causes: getJsonArray(formData, "analysis_likely_causes_json"),
      inferred_claims: getJsonArray(formData, "analysis_inferred_claims_json"),
      unknowns: getLines(formData, "analysis_unknowns"),
      follow_up_actions: getJsonArray(formData, "analysis_follow_up_actions_json"),
    };
  }

  const legacyJson = getString(formData, "edited_analysis_json");
  if (!legacyJson) return {};
  return JSON.parse(legacyJson) as Record<string, unknown>;
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

  await editHumanApproval(approvalId, {
    human_feedback: getFeedback(formData),
    edited_analysis_json: getEditedAnalysis(formData),
  });
  redirect(`/human-approvals/${approvalId}`);
}
