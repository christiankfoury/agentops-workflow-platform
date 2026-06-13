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

function formatWorkflowStatus(status: string): string {
  const labels: Record<string, string> = {
    created: "Created",
    running: "Running",
    routing: "Routing",
    analyst_running: "Analyst running",
    reviewer_running: "Reviewer running",
    retrying: "Retrying",
    waiting_for_human: "Waiting for human approval",
    writer_running: "Writer running",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
  };
  return labels[status] ?? status.replaceAll("_", " ");
}

function formatWorkflowType(type: string): string {
  const labels: Record<string, string> = {
    sales_report: "Sales report",
    customer_feedback: "Customer feedback",
    incident_log: "Incident log",
  };
  return labels[type] ?? type.replaceAll("_", " ");
}

function formatApprovalStatus(status: string): string {
  const labels: Record<string, string> = {
    pending: "Pending human review",
    approved: "Approved",
    rejected: "Rejected",
    retry_requested: "Retry requested",
  };
  return labels[status] ?? status.replaceAll("_", " ");
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

function asObjectArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is Record<string, unknown> =>
          typeof item === "object" && item !== null && !Array.isArray(item),
      )
    : [];
}

function getStringValue(
  record: Record<string, unknown>,
  key: string,
): string | null {
  const value = record[key];
  return typeof value === "string" && value.trim().length > 0
    ? value.trim()
    : null;
}

function getIssueSeverity(issue: Record<string, unknown>): string {
  return getStringValue(issue, "severity") ?? "review";
}

function getIssueLabel(issue: Record<string, unknown>): string {
  return (
    getStringValue(issue, "label") ??
    getStringValue(issue, "issue") ??
    getStringValue(issue, "message") ??
    "Reviewer issue"
  );
}

function getApprovalSummary(
  approval: HumanApproval,
  reviewerStep: AgentStep | undefined,
): string {
  const reviewerOutput = asRecord(reviewerStep?.output_json);
  const approved =
    reviewerOutput.approved === true ||
    (approval.reviewer_score != null && approval.reviewer_score >= 0.85);
  const issueCount = approval.issues_json?.length ?? 0;

  if (approval.status !== "pending") {
    return "This approval gate has already been resolved.";
  }
  if (issueCount > 0) {
    return "The reviewer found issues that need human review before this workflow can continue.";
  }
  if (approved) {
    return "The reviewer found no unsupported or missing-evidence issues. This workflow is ready for human approval.";
  }
  return "The reviewer completed its checks, but a human should inspect the output before approving.";
}

function getWorkflowLineage(workflowType: string): string[] {
  if (workflowType === "customer_feedback") {
    return ["Classifier", "Insight Agent", "Reviewer", "Human Approval"];
  }
  if (workflowType === "incident_log") {
    return ["Timeline", "Root Cause", "Reviewer", "Human Approval"];
  }
  return ["Analyst", "Reviewer", "Human Approval"];
}

function getRecommendationPriority(recommendation: Record<string, unknown>): string {
  const text = JSON.stringify(recommendation).toLowerCase();
  if (
    text.includes("checkout") ||
    text.includes("crash") ||
    text.includes("upload") ||
    text.includes("freeze")
  ) {
    return "Critical bug";
  }
  if (
    text.includes("performance") ||
    text.includes("slow") ||
    text.includes("latency") ||
    text.includes("responsiveness")
  ) {
    return "Performance";
  }
  if (text.includes("pricing") || text.includes("analytics")) {
    return "Pricing clarity";
  }
  if (text.includes("sso") || text.includes("single sign-on")) {
    return "Enterprise blocker";
  }
  if (text.includes("support") || text.includes("billing")) {
    return "Support quality";
  }
  return "Product improvement";
}

function InputHygieneWarning({ rawText }: { rawText: string }) {
  if (!rawText.toLowerCase().includes("expected themes:")) return null;

  return (
    <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
      Demo note: this input includes expected themes, which can make the run look
      pre-answered. For recruiter demos, use only the source feedback.
    </p>
  );
}

function ApprovalActionControls({
  approval,
  isActionable,
}: {
  approval: HumanApproval;
  isActionable: boolean;
}) {
  return (
    <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
      <form action={approveAction}>
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
      <form action={requestRetryAction}>
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
      <form action={rejectAction}>
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
  );
}

function WorkflowLineage({
  status,
  workflowType,
}: {
  status: string;
  workflowType: string;
}) {
  const steps = getWorkflowLineage(workflowType);
  const currentStatus = formatWorkflowStatus(status);

  return (
    <section className="mt-4 rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <h2 className="text-sm font-semibold">Workflow Lineage</h2>
        <p className="text-xs text-muted-foreground">
          Waiting for reviewer-approved human decision
        </p>
      </div>
      <ol className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-4">
        {steps.map((step, index) => {
          const isCurrent = index === steps.length - 1;
          return (
            <li
              key={step}
              className={`rounded-md border px-3 py-2 text-sm ${
                isCurrent
                  ? "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-200"
                  : "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{step}</span>
                <span className="text-xs">{isCurrent ? currentStatus : "Complete"}</span>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function EvidenceList({ examples }: { examples: unknown }) {
  const items = asObjectArray(examples)
    .map((example) => getStringValue(example, "text"))
    .filter((text): text is string => text !== null)
    .slice(0, 3);

  if (items.length === 0) return null;

  return (
    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
      {items.map((item) => (
        <li key={item} className="rounded-md bg-muted px-3 py-2">
          {item}
        </li>
      ))}
    </ul>
  );
}

function InsightList({
  emptyText,
  items,
}: {
  emptyText: string;
  items: string[];
}) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyText}</p>;
  }

  return (
    <ul className="space-y-2 text-sm">
      {items.map((item) => (
        <li key={item} className="rounded-md bg-muted px-3 py-2">
          {item}
        </li>
      ))}
    </ul>
  );
}

function CustomerFeedbackBriefing({
  analysis,
}: {
  analysis: Record<string, unknown>;
}) {
  const featureRequests = asObjectArray(analysis.feature_requests);
  const recommendations = asObjectArray(analysis.recommendations);

  return (
    <section className="mt-6">
      <div>
        <h2 className="text-lg font-semibold">Product Insight Summary</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Structured customer feedback findings, grouped for product and support
          decision review.
        </p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="rounded-lg border border-border bg-card p-4">
          <h3 className="font-semibold">Top Insights</h3>
          <div className="mt-3">
            <InsightList
              emptyText="No top insights were extracted."
              items={asStringArray(analysis.top_insights)}
            />
          </div>
        </article>
        <article className="rounded-lg border border-border bg-card p-4">
          <h3 className="font-semibold">Customer Pain Points</h3>
          <div className="mt-3">
            <InsightList
              emptyText="No customer pain points were extracted."
              items={asStringArray(analysis.customer_pain_points)}
            />
          </div>
        </article>
        <article className="rounded-lg border border-border bg-card p-4">
          <h3 className="font-semibold">Risks</h3>
          <div className="mt-3">
            <InsightList
              emptyText="No risks were extracted."
              items={asStringArray(analysis.risks)}
            />
          </div>
        </article>
        <article className="rounded-lg border border-border bg-card p-4">
          <h3 className="font-semibold">Feature Requests</h3>
          {featureRequests.length === 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">
              No feature requests were extracted.
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {featureRequests.map((request, index) => {
                const requestText =
                  getStringValue(request, "request") ?? `Feature request ${index + 1}`;
                const count =
                  typeof request.count === "number" && request.count > 0
                    ? request.count
                    : null;
                return (
                  <div key={`${requestText}-${index}`} className="rounded-md bg-muted p-3">
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
                      <p className="text-sm font-medium">{requestText}</p>
                      <p className="text-xs text-muted-foreground">
                        {count && count > 1
                          ? `Mentioned by ${count} customers`
                          : "Evidence from feedback"}
                      </p>
                    </div>
                    <EvidenceList examples={request.supporting_examples} />
                  </div>
                );
              })}
            </div>
          )}
        </article>
      </div>

      <div className="mt-4">
        <h3 className="font-semibold">Recommended Actions</h3>
        {recommendations.length === 0 ? (
          <p className="mt-3 rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
            No recommendations were extracted.
          </p>
        ) : (
          <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {recommendations.map((recommendation, index) => {
              const title =
                getStringValue(recommendation, "recommendation") ??
                `Recommendation ${index + 1}`;
              const rationale = getStringValue(recommendation, "rationale");
              const priority = getRecommendationPriority(recommendation);
              return (
                <article
                  key={`${title}-${index}`}
                  className="rounded-lg border border-border bg-card p-4"
                >
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    {priority}
                  </p>
                  <p className="mt-2 font-medium">{title}</p>
                  {rationale && (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {rationale}
                    </p>
                  )}
                  <EvidenceList examples={recommendation.supporting_examples} />
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

function GenericAnalysisBriefing({
  analysis,
  workflowType,
}: {
  analysis: Record<string, unknown>;
  workflowType: string;
}) {
  if (workflowType === "customer_feedback") {
    return <CustomerFeedbackBriefing analysis={analysis} />;
  }

  const sections =
    workflowType === "incident_log"
      ? [
          ["Suspected Root Cause", [String(analysis.suspected_root_cause ?? "")]],
          ["Unknowns", asStringArray(analysis.unknowns)],
        ]
      : [
          ["Key Findings", asStringArray(analysis.key_findings)],
          ["Risks", asStringArray(analysis.risks)],
          ["Opportunities", asStringArray(analysis.opportunities)],
          ["Recommendations", asStringArray(analysis.recommendations)],
        ];

  return (
    <section className="mt-6">
      <h2 className="text-lg font-semibold">Analysis Summary</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {sections.map(([title, items]) => (
          <article key={title as string} className="rounded-lg border border-border bg-card p-4">
            <h3 className="font-semibold">{title}</h3>
            <div className="mt-3">
              <InsightList
                emptyText="No items were extracted."
                items={(items as string[]).filter(Boolean)}
              />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ReviewerCheckSummary({
  approval,
  reviewerStep,
  workflowStatus,
}: {
  approval: HumanApproval;
  reviewerStep: AgentStep | undefined;
  workflowStatus: string;
}) {
  const issues = asObjectArray(approval.issues_json);
  const reviewerOutput = asRecord(reviewerStep?.output_json);
  const retryRecommended = reviewerOutput.retry_recommended === true;
  const checks = [
    {
      label: "Evidence support",
      value: issues.length === 0 ? "Passed" : "Needs review",
      passed: issues.length === 0,
    },
    {
      label: "Missing claims",
      value: issues.length === 0 ? "None found" : "Review required",
      passed: issues.length === 0,
    },
    {
      label: "Retry needed",
      value: retryRecommended ? "Yes" : "No",
      passed: !retryRecommended,
    },
    {
      label: "Human approval required",
      value:
        approval.status === "pending" && workflowStatus === "waiting_for_human"
          ? "Yes"
          : "No",
      passed:
        approval.status === "pending" && workflowStatus === "waiting_for_human",
    },
  ];

  return (
    <section className="mt-6 rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Reviewer Check</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Evidence gate for unsupported claims, missing support, and retry
            decisions.
          </p>
        </div>
        <span
          className={`w-fit rounded-full border px-3 py-1 text-sm font-medium ${
            issues.length === 0
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300"
              : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200"
          }`}
        >
          {issues.length === 0 ? "No issues found" : `${issues.length} issue${issues.length === 1 ? "" : "s"}`}
        </span>
      </div>

      {issues.length === 0 ? (
        <p className="mt-4 rounded-md bg-muted px-3 py-2 text-sm">
          The reviewer approved this output because every displayed claim is
          supported by the source feedback. No retry is recommended.
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          {issues.map((issue, index) => (
            <article key={index} className="rounded-md bg-muted p-3">
              <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
                <p className="text-sm font-medium">{getIssueLabel(issue)}</p>
                <p className="text-xs uppercase text-muted-foreground">
                  {getIssueSeverity(issue)}
                </p>
              </div>
              {getStringValue(issue, "explanation") && (
                <p className="mt-2 text-sm text-muted-foreground">
                  {getStringValue(issue, "explanation")}
                </p>
              )}
            </article>
          ))}
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {checks.map((check) => (
          <div key={check.label} className="rounded-md border border-border p-3">
            <dt className="text-xs text-muted-foreground">{check.label}</dt>
            <dd
              className={`mt-1 font-medium ${
                check.passed ? "text-emerald-700 dark:text-emerald-300" : ""
              }`}
            >
              {check.value}
            </dd>
          </div>
        ))}
      </div>

      <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-muted-foreground">Reviewer Score</dt>
          <dd className="mt-1 font-medium">{approval.reviewer_score ?? "-"}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Recommended Action</dt>
          <dd className="mt-1 font-medium">{getRecommendedAction(approval)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Retry Recommended</dt>
          <dd className="mt-1 font-medium">{retryRecommended ? "Yes" : "No"}</dd>
        </div>
      </dl>
    </section>
  );
}

function DeveloperDetails({
  analysis,
  issues,
  reviewerOutput,
}: {
  analysis: unknown;
  issues: unknown;
  reviewerOutput: unknown;
}) {
  return (
    <section className="mt-6">
      <details className="rounded-lg border border-border bg-muted p-4">
        <summary className="cursor-pointer text-sm font-medium">
          Developer details: raw agent JSON
        </summary>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Analysis Output
            </p>
            <pre className="mt-2 max-h-80 overflow-auto rounded-md bg-background p-3 text-xs whitespace-pre-wrap">
              {formatJson(analysis)}
            </pre>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Reviewer Issues
            </p>
            <pre className="mt-2 max-h-80 overflow-auto rounded-md bg-background p-3 text-xs whitespace-pre-wrap">
              {formatJson(issues)}
            </pre>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Reviewer Output
            </p>
            <pre className="mt-2 max-h-80 overflow-auto rounded-md bg-background p-3 text-xs whitespace-pre-wrap">
              {formatJson(reviewerOutput)}
            </pre>
          </div>
        </div>
      </details>
    </section>
  );
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
  const reviewerIssues = approval.issues_json ?? [];
  const shouldOpenEditAnalysis =
    reviewerIssues.length > 0 || getRecommendedAction(approval) !== "Approve";

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
          {formatApprovalStatus(approval.status)}
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
          {` ${formatWorkflowStatus(run.status).toLowerCase()}`}. Approval
          actions are available only while the workflow is waiting for human
          approval.
        </section>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Workflow Type</p>
          <p className="mt-1 font-medium">{formatWorkflowType(run.workflow_type)}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Workflow Status</p>
          <p className="mt-1 font-medium">{formatWorkflowStatus(run.status)}</p>
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

      <section className="mt-6 rounded-lg border border-border bg-card p-4">
        <p className="text-xs font-medium uppercase text-muted-foreground">
          Approval review
        </p>
        <h2 className="mt-2 text-xl font-semibold">Ready for Human Approval</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          {getApprovalSummary(approval, reviewerStep)}
        </p>
        <ApprovalActionControls approval={approval} isActionable={isActionable} />
      </section>

      <WorkflowLineage status={run.status} workflowType={run.workflow_type} />

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
            <InputHygieneWarning rawText={uploadedInput.raw_text} />
            <pre className="mt-4 max-h-80 overflow-auto rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">
              {uploadedInput.raw_text}
            </pre>
          </div>
        </section>
      )}

      <GenericAnalysisBriefing
        analysis={editableAnalysis}
        workflowType={run.workflow_type}
      />

      <ReviewerCheckSummary
        approval={approval}
        reviewerStep={reviewerStep}
        workflowStatus={run.status}
      />

      <DeveloperDetails
        analysis={editableStep?.output_json}
        issues={approval.issues_json}
        reviewerOutput={reviewerStep?.output_json}
      />

      <section className="mt-6">
        <details
          className="rounded-lg border border-border bg-card p-4"
          open={shouldOpenEditAnalysis}
        >
          <summary className="cursor-pointer text-lg font-semibold">
            Edit approved analysis
          </summary>
          <form action={editAction} className="mt-4">
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
        </details>
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
