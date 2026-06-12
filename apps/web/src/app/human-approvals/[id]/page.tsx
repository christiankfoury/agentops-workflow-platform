import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getHumanApproval,
  getUploadedInput,
  getWorkflowRun,
  listAgentSteps,
} from "@/lib/api";
import type { AgentStep, HumanApproval } from "@/lib/types";
import {
  approveAction,
  editAction,
  rejectAction,
  requestRetryAction,
} from "./actions";

function formatJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function getRecommendedAction(approval: HumanApproval): string {
  if (approval.status !== "pending") return "Resolved";
  const hasHighSeverityIssue = (approval.issues_json ?? []).some(
    (issue) =>
      typeof issue === "object" &&
      issue !== null &&
      "severity" in issue &&
      issue.severity === "high",
  );
  if (hasHighSeverityIssue) return "Request Retry";
  if (approval.reviewer_score != null && approval.reviewer_score >= 0.85) {
    return "Approve";
  }
  return "Review Manually";
}

function getGateStatus(
  approval: HumanApproval,
  workflowStatus: string,
): "resolved" | "actionable" | "blocked" {
  if (approval.status !== "pending") return "resolved";
  return workflowStatus === "waiting_for_human" ? "actionable" : "blocked";
}

function getLatestStep(steps: AgentStep[], agentType: string): AgentStep | undefined {
  return steps.filter((step) => step.agent_type === agentType).at(-1);
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function listText(value: unknown): string {
  return asStringArray(value).join("\n");
}

function jsonArrayText(value: unknown): string {
  return JSON.stringify(Array.isArray(value) ? value : [], null, 2);
}

function getEditableStep(steps: AgentStep[], workflowType: string): AgentStep | undefined {
  if (workflowType === "customer_feedback") return getLatestStep(steps, "insight");
  if (workflowType === "incident_log") return getLatestStep(steps, "root_cause");
  return getLatestStep(steps, "analyst");
}

function getEditableAnalysis(
  approval: HumanApproval,
  editableStep: AgentStep | undefined,
): Record<string, unknown> {
  return asRecord(approval.edited_analysis_json ?? editableStep?.output_json);
}

function TextEditField({
  disabled,
  label,
  name,
  value,
}: {
  disabled: boolean;
  label: string;
  name: string;
  value: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium" htmlFor={name}>
        {label}
      </label>
      <textarea
        id={name}
        name={name}
        defaultValue={value}
        disabled={disabled}
        className="mt-2 min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-60"
      />
    </div>
  );
}

function JsonArrayEditField({
  disabled,
  label,
  name,
  value,
}: {
  disabled: boolean;
  label: string;
  name: string;
  value: unknown;
}) {
  return (
    <div>
      <label className="block text-sm font-medium" htmlFor={name}>
        {label}
      </label>
      <textarea
        id={name}
        name={name}
        defaultValue={jsonArrayText(value)}
        disabled={disabled}
        className="mt-2 min-h-32 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm disabled:opacity-60"
      />
    </div>
  );
}

function StructuredAnalysisEditor({
  analysis,
  disabled,
  workflowType,
}: {
  analysis: Record<string, unknown>;
  disabled: boolean;
  workflowType: string;
}) {
  if (workflowType === "customer_feedback") {
    return (
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TextEditField
          disabled={disabled}
          label="Top Insights"
          name="analysis_top_insights"
          value={listText(analysis.top_insights)}
        />
        <TextEditField
          disabled={disabled}
          label="Customer Pain Points"
          name="analysis_customer_pain_points"
          value={listText(analysis.customer_pain_points)}
        />
        <TextEditField
          disabled={disabled}
          label="Risks"
          name="analysis_risks"
          value={listText(analysis.risks)}
        />
        <JsonArrayEditField
          disabled={disabled}
          label="Feature Requests JSON"
          name="analysis_feature_requests_json"
          value={analysis.feature_requests}
        />
        <JsonArrayEditField
          disabled={disabled}
          label="Recommendations JSON"
          name="analysis_recommendations_json"
          value={analysis.recommendations}
        />
        <JsonArrayEditField
          disabled={disabled}
          label="Supporting Examples JSON"
          name="analysis_supporting_examples_json"
          value={analysis.supporting_examples}
        />
      </div>
    );
  }

  if (workflowType === "incident_log") {
    return (
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TextEditField
          disabled={disabled}
          label="Suspected Root Cause"
          name="analysis_suspected_root_cause"
          value={typeof analysis.suspected_root_cause === "string" ? analysis.suspected_root_cause : ""}
        />
        <TextEditField
          disabled={disabled}
          label="Unknowns"
          name="analysis_unknowns"
          value={listText(analysis.unknowns)}
        />
        <JsonArrayEditField
          disabled={disabled}
          label="Impact JSON"
          name="analysis_impact_json"
          value={analysis.impact}
        />
        <JsonArrayEditField
          disabled={disabled}
          label="Confirmed Facts JSON"
          name="analysis_confirmed_facts_json"
          value={analysis.confirmed_facts}
        />
        <JsonArrayEditField
          disabled={disabled}
          label="Likely Causes JSON"
          name="analysis_likely_causes_json"
          value={analysis.likely_causes}
        />
        <JsonArrayEditField
          disabled={disabled}
          label="Inferred Claims JSON"
          name="analysis_inferred_claims_json"
          value={analysis.inferred_claims}
        />
        <JsonArrayEditField
          disabled={disabled}
          label="Follow-up Actions JSON"
          name="analysis_follow_up_actions_json"
          value={analysis.follow_up_actions}
        />
      </div>
    );
  }

  return (
    <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <TextEditField
        disabled={disabled}
        label="Key Findings"
        name="analysis_key_findings"
        value={listText(analysis.key_findings)}
      />
      <TextEditField
        disabled={disabled}
        label="Risks"
        name="analysis_risks"
        value={listText(analysis.risks)}
      />
      <TextEditField
        disabled={disabled}
        label="Opportunities"
        name="analysis_opportunities"
        value={listText(analysis.opportunities)}
      />
      <TextEditField
        disabled={disabled}
        label="Recommendations"
        name="analysis_recommendations"
        value={listText(analysis.recommendations)}
      />
      <TextEditField
        disabled={disabled}
        label="Supporting Evidence"
        name="analysis_supporting_evidence"
        value={listText(analysis.supporting_evidence)}
      />
    </div>
  );
}

export default async function HumanApprovalDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams?: Promise<{ error?: string }>;
}) {
  const { id } = await params;
  const actionError = (await searchParams)?.error;
  const approval = await getHumanApproval(id);

  if (!approval) notFound();

  const run = await getWorkflowRun(approval.workflow_run_id);
  if (!run) notFound();

  const [uploadedInput, agentSteps] = await Promise.all([
    run.input_id ? getUploadedInput(run.input_id) : Promise.resolve(null),
    listAgentSteps(run.id),
  ]);
  const editableStep = getEditableStep(agentSteps, run.workflow_type);
  const reviewerStep = getLatestStep(agentSteps, "reviewer");
  const gateStatus = getGateStatus(approval, run.status);
  const isActionable = gateStatus === "actionable";
  const editableAnalysis = getEditableAnalysis(approval, editableStep);

  return (
    <div>
      <Link
        href="/human-approvals"
        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        Back to Human Approvals
      </Link>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Human Approval</h1>
          <p className="font-mono text-sm text-muted-foreground">{approval.id}</p>
        </div>
        <span className="w-fit rounded-full bg-muted px-3 py-1 text-sm font-medium">
          {approval.status}
        </span>
      </div>

      {actionError && (
        <section className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {actionError}
        </section>
      )}

      {gateStatus === "blocked" && (
        <section className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          This approval record is still pending, but the workflow is currently
          {` ${run.status}`}. Approval actions are available only while the
          workflow is waiting for human approval.
        </section>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Workflow Type</p>
          <p className="mt-1 font-medium">{run.workflow_type}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Workflow Status</p>
          <p className="mt-1 font-medium">{run.status}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Reviewer Score</p>
          <p className="mt-1 font-medium">{approval.reviewer_score ?? "-"}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Recommended Action</p>
          <p className="mt-1 font-medium">{getRecommendedAction(approval)}</p>
        </div>
      </div>

      {uploadedInput && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold">Original Input</h2>
          <div className="mt-2 rounded-lg border border-border bg-card p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
              <p className="font-medium">{uploadedInput.title}</p>
              {uploadedInput.file_name && (
                <p className="text-xs text-muted-foreground">
                  {uploadedInput.file_name}
                </p>
              )}
            </div>
            <pre className="mt-4 max-h-80 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
              {uploadedInput.raw_text}
            </pre>
          </div>
        </section>
      )}

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Analysis Output</h2>
        <pre className="mt-2 max-h-96 overflow-auto rounded-lg border border-border bg-muted p-4 text-sm whitespace-pre-wrap">
          {formatJson(editableStep?.output_json)}
        </pre>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Reviewer Issues</h2>
        <pre className="mt-2 max-h-80 overflow-auto rounded-lg border border-border bg-muted p-4 text-sm whitespace-pre-wrap">
          {formatJson(approval.issues_json)}
        </pre>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Reviewer Output</h2>
        <pre className="mt-2 max-h-80 overflow-auto rounded-lg border border-border bg-muted p-4 text-sm whitespace-pre-wrap">
          {formatJson(reviewerStep?.output_json)}
        </pre>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Edit Analysis</h2>
        <form action={editAction} className="mt-2 rounded-lg border border-border bg-card p-4">
          <input type="hidden" name="approval_id" value={approval.id} />
          <input type="hidden" name="workflow_type" value={run.workflow_type} />
          <label className="block text-sm font-medium" htmlFor="human_feedback">
            Human Feedback
          </label>
          <textarea
            id="human_feedback"
            name="human_feedback"
            defaultValue={approval.human_feedback ?? ""}
            disabled={!isActionable}
            className="mt-2 min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-60"
          />
          <StructuredAnalysisEditor
            analysis={editableAnalysis}
            disabled={!isActionable}
            workflowType={run.workflow_type}
          />
          <details className="mt-4 rounded-md border border-border bg-muted p-3">
            <summary className="cursor-pointer text-sm font-medium">
              Edited JSON Preview
            </summary>
            <pre className="mt-3 max-h-72 overflow-auto text-sm whitespace-pre-wrap">
              {formatJson(editableAnalysis)}
            </pre>
          </details>
          <button
            type="submit"
            disabled={!isActionable}
            className="mt-4 rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
          >
            Save Edits
          </button>
        </form>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">Actions</h2>
        <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <form action={approveAction} className="rounded-lg border border-border bg-card p-4">
            <input type="hidden" name="approval_id" value={approval.id} />
            <input
              type="hidden"
              name="human_feedback"
              value={approval.human_feedback ?? ""}
            />
            <button
              type="submit"
              disabled={!isActionable}
              className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Approve
            </button>
          </form>
          <form
            action={requestRetryAction}
            className="rounded-lg border border-border bg-card p-4"
          >
            <input type="hidden" name="approval_id" value={approval.id} />
            <input
              type="hidden"
              name="human_feedback"
              value={approval.human_feedback ?? ""}
            />
            <button
              type="submit"
              disabled={!isActionable}
              className="w-full rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
            >
              Request Retry
            </button>
          </form>
          <form action={rejectAction} className="rounded-lg border border-border bg-card p-4">
            <input type="hidden" name="approval_id" value={approval.id} />
            <input
              type="hidden"
              name="human_feedback"
              value={approval.human_feedback ?? ""}
            />
            <button
              type="submit"
              disabled={!isActionable}
              className="w-full rounded-md border border-destructive/40 px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Reject Workflow
            </button>
          </form>
        </div>
      </section>

      <div className="mt-6">
        <Link
          href={`/workflow-runs/${run.id}`}
          className="text-sm text-primary underline hover:opacity-80"
        >
          View Workflow Run
        </Link>
      </div>
    </div>
  );
}
