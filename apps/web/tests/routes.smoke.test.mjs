import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

test("workflow dashboard pages stay wired to the API flow", () => {
  assert.match(read("src/app/page.tsx"), /listWorkflowRuns/);
  assert.match(read("src/app/page.tsx"), /getHumanFeedbackSummary/);
  assert.match(read("src/app/page.tsx"), /Human Feedback Loop/);
  assert.match(read("src/app/workflow-runs/page.tsx"), /listWorkflowRuns/);
  assert.match(read("src/app/workflow-runs/page.tsx"), /WorkflowRunsTable/);
  assert.match(read("src/app/workflow-runs/workflow-runs-table.tsx"), /Search workflow runs/);
  assert.match(read("src/app/workflow-runs/workflow-runs-table.tsx"), /input_title/);
  assert.match(read("src/app/workflow-runs/workflow-runs-table.tsx"), /role="link"/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /getWorkflowRun/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /getUploadedInput/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /listAgentSteps/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /listWorkflowEvents/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /listHumanApprovals/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Observability Timeline/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /RecoverySummary/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Workflow completed\. Final report is ready\./);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /CompactMetricStrip/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Workflow Lineage/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /ArrowRight/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Pending/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Current/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Outcome Summary/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /timestamped incident event/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /confirmed fact/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /reviewer-approved incident analysis/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Final Output Preview/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Writer output generated after human approval/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /seeded or imported run/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /final-output/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /CreateEvaluationComparisonForm/);
  assert.match(read("src/app/workflow-runs/[id]/final-output/page.tsx"), /Final Executive Summary/);
  assert.match(read("src/app/workflow-runs/[id]/final-output/page.tsx"), /Workflow Trace/);
  assert.match(read("src/app/workflow-runs/[id]/final-output/page.tsx"), /Writer output generated from the human-approved analysis/);
  assert.match(read("src/app/workflow-runs/[id]/final-output/page.tsx"), /Insight Output/);
  assert.match(read("src/app/workflow-runs/[id]/final-output/page.tsx"), /listAgentSteps/);
  assert.match(read("src/app/human-approvals/page.tsx"), /listHumanApprovals/);
  assert.match(read("src/app/human-approvals/page.tsx"), /HumanApprovalsTable/);
  assert.match(read("src/app/human-approvals/human-approvals-table.tsx"), /Approval Queue/);
  assert.match(read("src/app/human-approvals/human-approvals-table.tsx"), /Search human approvals/);
  assert.match(read("src/app/human-approvals/human-approvals-table.tsx"), /role="link"/);
  assert.match(read("src/app/human-approvals/human-approvals-table.tsx"), /Approval for/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /getHumanApproval/);
  assert.match(read("src/app/human-approvals/[id]/actions.ts"), /approveHumanApproval/);
  assert.match(read("src/app/human-approvals/[id]/actions.ts"), /requestHumanApprovalRetry/);
  assert.match(read("src/app/human-approvals/[id]/actions.ts"), /rejectHumanApproval/);
  assert.match(read("src/app/human-approvals/[id]/actions.ts"), /editHumanApproval/);
  assert.match(read("src/app/human-approvals/[id]/actions.ts"), /redirectWithActionError/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /StructuredAnalysisEditor/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Approval review/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Waiting for human approval/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Pending human review/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Customer feedback/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Ready for Human Approval/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Classifier/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Insight Agent/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Product Insight Summary/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Reviewer Check/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Evidence support/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Edit approved analysis/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Evidence from feedback/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /Developer details: raw agent JSON/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /actionError/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /analysis_key_findings/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /analysis_top_insights/);
  assert.match(read("src/app/human-approvals/[id]/page.tsx"), /analysis_suspected_root_cause/);
  assert.match(read("src/app/human-approvals/[id]/actions.ts"), /getEditedAnalysis/);
  assert.match(read("src/app/costs/page.tsx"), /Cost Dashboard/);
  assert.match(read("src/app/costs/page.tsx"), /listWorkflowRuns/);
  assert.match(read("src/app/costs/page.tsx"), /listAgentSteps/);
  assert.match(read("src/app/costs/page.tsx"), /Cost Insights/);
  assert.match(read("src/app/costs/page.tsx"), /Recent Cost Over Time/);
  assert.match(read("src/app/costs/page.tsx"), /Avg Cost \/ Retried Step/);
  assert.match(read("src/app/costs/page.tsx"), /Seeded demo/);
  assert.match(read("src/app/costs/page.tsx"), /Workflow input/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/costs"/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/evaluation"/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/demo"/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/agent-performance"/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/workflow-comparison"/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/failures"/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/improvements"/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/prompt-versions"/);
  assert.match(read("src/components/nav.tsx"), /href:\s*"\/settings"/);
  assert.match(read("src/app/evaluation/page.tsx"), /Evaluation Dashboard/);
  assert.match(read("src/app/evaluation/page.tsx"), /getEvaluationSummary/);
  assert.match(read("src/app/evaluation/page.tsx"), /Router Accuracy/);
  assert.match(read("src/app/evaluation/page.tsx"), /Export CSV/);
  assert.match(read("src/app/evaluation/page.tsx"), /Export JSON/);
  assert.match(read("src/app/evaluation/page.tsx"), /Export Markdown/);
  assert.match(read("src/app/demo/page.tsx"), /Demo Mode/);
  assert.match(read("src/app/demo/page.tsx"), /Sales Workflow Demo/);
  assert.match(read("src/app/demo/page.tsx"), /Feedback Workflow Demo/);
  assert.match(read("src/app/demo/page.tsx"), /Incident Workflow Demo/);
  assert.match(read("src/app/demo/page.tsx"), /Full Portfolio Demo/);
  assert.match(read("src/app/demo/page.tsx"), /Load Feedback Demo/);
  assert.match(read("src/app/demo/page.tsx"), /Open existing output/);
  assert.match(read("src/app/demo/page.tsx"), /Accuracy is factual accuracy/);
  assert.match(read("src/app/demo/page.tsx"), /evaluation summary API/);
  assert.match(read("src/app/demo/page.tsx"), /deterministic demo data/);
  assert.match(read("src/app/demo/page.tsx"), /\/workflow-comparison\?search=Feedback/);
  assert.match(read("src/app/demo/actions.ts"), /demoDestinations/);
  assert.match(read("src/app/demo/actions.ts"), /\/workflow-comparison\?search=Incident/);
  assert.match(read("src/app/demo/page.tsx"), /What these demo actions do/);
  assert.match(read("src/app/demo/page.tsx"), /Demo data loaders/);
  assert.match(read("src/app/demo/page.tsx"), /Evaluation Results/);
  assert.match(read("src/app/demo/page.tsx"), /Multi-agent Accuracy/);
  assert.match(read("src/app/demo/page.tsx"), /1\. Seed/);
  assert.match(read("src/app/demo/page.tsx"), /Guided stories/);
  assert.match(read("src/app/demo/actions.ts"), /seedDemoDataset/);
  assert.match(read("src/app/agent-performance/page.tsx"), /Agent Performance Dashboard/);
  assert.match(read("src/app/agent-performance/page.tsx"), /getAgentPerformanceSummary/);
  assert.match(read("src/app/agent-performance/page.tsx"), /Schema Validation Failures/);
  assert.match(read("src/app/workflow-comparison/page.tsx"), /Workflow Comparison/);
  assert.match(read("src/app/workflow-comparison/page.tsx"), /getEvaluationComparisons/);
  assert.match(read("src/app/workflow-comparison/page.tsx"), /WorkflowComparisonExplorer/);
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Reviewer Issues/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /How to read this comparison/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Unsupported claim rate is better when lower/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Demo story shortcuts/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Reviewer Clean/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Mixed Outcome/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Evaluation rationale/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Baseline stays fixed/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Reviewed claim/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Keeps the baseline and original multi-agent run unchanged/,
  );
  assert.match(
    read("src/app/workflow-comparison/workflow-comparison-explorer.tsx"),
    /Show .* more/,
  );
  assert.match(read("src/app/failures/page.tsx"), /Failure Case Explorer/);
  assert.match(read("src/app/failures/page.tsx"), /listWorkflowRuns/);
  assert.match(read("src/app/failures/page.tsx"), /Schema Validation Failures/);
  assert.match(read("src/app/improvements/page.tsx"), /Improvement Tracking/);
  assert.match(read("src/app/improvements/page.tsx"), /listEvaluationResults/);
  assert.match(read("src/app/improvements/page.tsx"), /Evaluation Trends/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /Prompt Control Center/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /listPromptVersions/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /Workflow-Specific Prompts/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /Shared Governance Prompts/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /title="Sales"/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /title="Customer Feedback"/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /title="Incident"/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /Prompt changes affect future/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /Review naming/);
  assert.match(read("src/app/prompt-versions/page.tsx"), /CreatePromptVersionModal/);
  assert.match(read("src/app/prompt-versions/form.tsx"), /useActionState/);
  assert.match(read("src/app/prompt-versions/create-prompt-version-modal.tsx"), /role="dialog"/);
  assert.match(read("src/app/prompt-versions/create-prompt-version-modal.tsx"), /Create Prompt Version/);
  assert.match(read("src/lib/agent-display.ts"), /Sales Analyst/);
  assert.match(read("src/lib/agent-display.ts"), /Root Cause Agent/);
  assert.match(read("src/lib/agent-display.ts"), /Used before workflow creation/);
  assert.match(read("src/lib/agent-display.ts"), /Shared by Sales, Customer Feedback, and Incident/);
  assert.match(read("src/app/prompt-versions/[id]/page.tsx"), /Activate Prompt/);
  assert.match(read("src/app/settings/page.tsx"), /Agent Settings/);
  assert.match(read("src/app/settings/page.tsx"), /listAgentSettings/);
  assert.match(read("src/app/settings/settings-form.tsx"), /useActionState/);
  assert.match(read("src/app/settings/actions.ts"), /updateAgentSetting/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /runSalesAnalyst/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /runSalesBaseline/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /runCustomerFeedbackClassifier/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /runCustomerFeedbackInsight/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /runIncidentTimeline/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /runIncidentRootCause/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /runSalesReviewer/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /runSalesWriter/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /cancelWorkflowRun/);
  assert.match(read("src/app/workflow-runs/[id]/actions.ts"), /createEvaluationComparisonFromRun/);
  assert.match(read("src/app/workflow-runs/[id]/run-analyst-form.tsx"), /useActionState/);
  assert.match(read("src/app/workflow-runs/[id]/run-baseline-form.tsx"), /useActionState/);
  assert.match(read("src/app/workflow-runs/[id]/run-classifier-form.tsx"), /useActionState/);
  assert.match(read("src/app/workflow-runs/[id]/run-insight-form.tsx"), /useActionState/);
  assert.match(read("src/app/workflow-runs/[id]/run-timeline-form.tsx"), /Run Timeline Agent/);
  assert.match(read("src/app/workflow-runs/[id]/run-root-cause-form.tsx"), /Run Root Cause Agent/);
  assert.match(read("src/app/workflow-runs/[id]/run-reviewer-form.tsx"), /useActionState/);
  assert.match(read("src/app/workflow-runs/[id]/run-writer-form.tsx"), /useActionState/);
  assert.match(read("src/app/workflow-runs/[id]/create-evaluation-comparison-form.tsx"), /Compare This Run/);
  assert.match(
    read("src/app/workflow-runs/[id]/create-evaluation-comparison-form.tsx"),
    /only\s+the\s+missing\s+baseline\s+or\s+multi-agent\s+side\s+is\s+created/s,
  );
  assert.match(read("src/app/workflow-runs/[id]/cancel-workflow-form.tsx"), /Cancel Workflow/);
  assert.match(read("src/app/workflow-runs/new/actions.ts"), /createWorkflowRun/);
  assert.match(read("src/app/workflow-runs/new/actions.ts"), /createUploadedInput/);
  assert.match(read("src/app/workflow-runs/new/actions.ts"), /uploadInputFile/);
  assert.match(read("src/app/workflow-runs/new/actions.ts"), /detectWorkflowType/);
  assert.match(read("src/app/workflow-runs/new/page.tsx"), /Workflow intake/);
  assert.match(read("src/app/workflow-runs/new/page.tsx"), /Supported inputs/);
  assert.match(read("src/app/workflow-runs/new/page.tsx"), /Run mode choice/);
  assert.match(read("src/app/workflow-runs/new/form.tsx"), /useActionState/);
  assert.match(read("src/app/workflow-runs/new/form.tsx"), /Workflow details/);
  assert.match(read("src/app/workflow-runs/new/form.tsx"), /Auto-detect workflow type/);
  assert.match(read("src/app/workflow-runs/new/form.tsx"), /\.csv/);
  assert.match(read("src/app/workflow-runs/new/form.tsx"), /CSV Preview/);
  assert.match(read("src/app/workflow-runs/[id]/page.tsx"), /Input Missing/);
});

test("workflow API client exposes workflow and uploaded input calls", () => {
  const api = read("src/lib/api.ts");
  const apiUrl = read("src/lib/api-url.ts");

  assert.match(api, /apiUrl/);
  assert.match(apiUrl, /resolveApiBaseUrl/);
  assert.match(apiUrl, /isDockerServiceUrl/);
  assert.match(apiUrl, /hostname === "api"/);
  assert.match(apiUrl, /!isContainer/);

  assert.match(api, /export async function listWorkflowRuns/);
  assert.match(api, /export async function getWorkflowRun/);
  assert.match(api, /export async function createWorkflowRun/);
  assert.match(api, /export async function createUploadedInput/);
  assert.match(api, /export async function uploadInputFile/);
  assert.match(api, /export async function getUploadedInput/);
  assert.match(api, /export async function detectWorkflowType/);
  assert.match(api, /export async function listAgentSteps/);
  assert.match(api, /export async function listWorkflowEvents/);
  assert.match(api, /export async function getEvaluationSummary/);
  assert.match(api, /export async function listEvaluationResults/);
  assert.match(api, /export async function getEvaluationComparisons/);
  assert.match(api, /export async function createEvaluationComparisonFromRun/);
  assert.match(api, /export async function createCorrectedEvaluationComparisonRun/);
  assert.match(api, /export async function seedDemoDataset/);
  assert.match(api, /export async function getAgentPerformanceSummary/);
  assert.match(api, /export async function listPromptVersions/);
  assert.match(api, /export async function getPromptVersion/);
  assert.match(api, /PROMPT_CONFIGURATION_FETCH_TIMEOUT_MS/);
  assert.match(api, /export async function createPromptVersion/);
  assert.match(api, /export async function activatePromptVersion/);
  assert.match(api, /export async function listAgentSettings/);
  assert.match(api, /export async function updateAgentSetting/);
  assert.match(api, /export async function runSalesAnalyst/);
  assert.match(api, /export async function runSalesBaseline/);
  assert.match(api, /export async function runCustomerFeedbackClassifier/);
  assert.match(api, /export async function runCustomerFeedbackInsight/);
  assert.match(api, /export async function runIncidentTimeline/);
  assert.match(api, /export async function runIncidentRootCause/);
  assert.match(api, /export async function runSalesReviewer/);
  assert.match(api, /export async function runSalesWriter/);
  assert.match(api, /export async function cancelWorkflowRun/);
  assert.match(api, /export async function listHumanApprovals/);
  assert.match(api, /export async function getHumanApproval/);
  assert.match(api, /export async function getHumanFeedbackSummary/);
  assert.match(api, /export async function approveHumanApproval/);
  assert.match(api, /export async function requestHumanApprovalRetry/);
  assert.match(api, /export async function rejectHumanApproval/);
  assert.match(api, /export async function editHumanApproval/);
});
