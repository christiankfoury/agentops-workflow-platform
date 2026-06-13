export type WorkflowType = "sales_report" | "customer_feedback" | "incident_log";
export type RunMode = "baseline" | "multi_agent";
export type DemoSeedTarget =
  | "sales-report"
  | "customer-feedback"
  | "incident-log"
  | "full-evaluation";
export type AgentType =
  | "analyst"
  | "reviewer"
  | "writer"
  | "router"
  | "timeline"
  | "root_cause"
  | "classifier"
  | "insight";
export type WorkflowStatus =
  | "created"
  | "running"
  | "routing"
  | "analyst_running"
  | "reviewer_running"
  | "retrying"
  | "waiting_for_human"
  | "writer_running"
  | "completed"
  | "failed"
  | "cancelled";

export type AgentStepStatus = "pending" | "running" | "completed" | "failed";
export type ApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "retry_requested";
export type WorkflowEventType =
  | "workflow_started"
  | "workflow_completed"
  | "workflow_failed"
  | "workflow_cancelled"
  | "agent_started"
  | "agent_completed"
  | "agent_failed"
  | "reviewer_rejected_output"
  | "retry_triggered"
  | "human_approval_required"
  | "human_edited_analysis"
  | "human_approved"
  | "human_rejected"
  | "human_requested_retry";

export interface WorkflowRun {
  id: string;
  organization_id: string | null;
  created_by_user_id: string | null;
  workflow_type: WorkflowType;
  run_mode: RunMode;
  status: WorkflowStatus;
  input_id: string | null;
  final_output: string | null;
  quality_score: number | null;
  total_cost: number | null;
  total_tokens: number | null;
  latency_ms: number | null;
  retry_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface UploadedInput {
  id: string;
  organization_id: string | null;
  created_by_user_id: string | null;
  title: string;
  input_type: WorkflowType;
  raw_text: string;
  notes: string | null;
  file_name: string | null;
  file_type: string | null;
  file_size: number | null;
  created_at: string;
}

export interface AgentStep {
  id: string;
  workflow_run_id: string;
  agent_name: string;
  agent_type: string;
  step_order: number;
  status: AgentStepStatus;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  model: string | null;
  prompt_version_id: string | null;
  tokens_input: number | null;
  tokens_output: number | null;
  total_tokens: number | null;
  cost: number | null;
  latency_ms: number | null;
  retry_count: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface WorkflowEvent {
  id: string;
  workflow_run_id: string;
  agent_step_id: string | null;
  event_type: WorkflowEventType;
  message: string;
  metadata_json: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
}

export interface EvaluationMetricsSummary {
  workflow_type: WorkflowType;
  run_mode: RunMode;
  run_count: number;
  factual_accuracy: number;
  unsupported_claim_rate: number;
  completeness_score: number;
  router_accuracy: number;
  average_router_confidence: number;
  human_approval_rate: number;
  average_cost: number;
  average_latency_ms: number;
  average_retries: number;
}

export interface EvaluationResult {
  id: string;
  evaluation_case_id: string;
  workflow_run_id: string | null;
  run_mode: RunMode;
  status: "pending" | "completed" | "failed";
  prompt_version_summary_json: Record<string, unknown> | null;
  factual_accuracy: number | null;
  unsupported_claim_rate: number | null;
  completeness_score: number | null;
  router_detected_workflow_type: WorkflowType | null;
  router_confidence: number | null;
  router_correct: boolean | null;
  human_approval_required: boolean | null;
  human_approved: boolean | null;
  retry_count: number | null;
  cost: number | null;
  latency_ms: number | null;
  judge_notes: string | null;
  error_message: string | null;
  created_at: string;
}

export interface EvaluationComparisonRun {
  workflow_run_id: string;
  final_output: string | null;
  factual_accuracy: number | null;
  unsupported_claim_rate: number | null;
  completeness_score: number | null;
  judge_notes: string | null;
  cost: number;
  latency_ms: number;
  created_at: string;
}

export interface RemediationImpact {
  previous_multi_agent_run_id: string;
  corrected_multi_agent_run_id: string;
  previous_reviewer_issue_count: number;
  current_reviewer_issue_count: number;
  factual_accuracy_delta: number | null;
  unsupported_claim_rate_delta: number | null;
  completeness_score_delta: number | null;
  cost_delta: number;
  latency_delta_ms: number;
  impact_status: "improved" | "mixed" | "worsened";
}

export interface EvaluationComparison {
  evaluation_case_id: string;
  workflow_type: WorkflowType;
  title: string;
  input_preview: string;
  baseline: EvaluationComparisonRun;
  multi_agent: EvaluationComparisonRun;
  reviewer_issues: Record<string, unknown>[];
  cost_difference: number;
  latency_difference_ms: number;
  remediation_impact: RemediationImpact | null;
}

export interface WorkflowRunEvaluationComparison {
  evaluation_case_id: string;
  baseline_result_id: string;
  multi_agent_result_id: string;
  baseline_run_id: string;
  multi_agent_run_id: string;
  comparison_url: string;
}

export interface CorrectedEvaluationComparison {
  evaluation_case_id: string;
  baseline_result_id: string;
  corrected_result_id: string;
  baseline_run_id: string;
  source_multi_agent_run_id: string;
  corrected_multi_agent_run_id: string;
  comparison_url: string;
}

export interface AgentPerformanceSummary {
  agent_type: string;
  agent_name: string;
  step_count: number;
  completed_count: number;
  failed_count: number;
  retry_count: number;
  schema_validation_failure_count: number;
  average_latency_ms: number;
  average_cost: number;
  failure_rate: number;
  retry_rate: number;
  average_reviewer_score: number | null;
  schema_validation_failure_rate: number;
}

export interface HumanApproval {
  id: string;
  workflow_run_id: string;
  reviewer_score: number | null;
  issues_json: unknown[] | null;
  status: ApprovalStatus;
  human_feedback: string | null;
  edited_analysis_json: Record<string, unknown> | null;
  approved_by_user_id: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface ReviewerIssueSummary {
  label: string;
  severity: string | null;
  count: number;
}

export interface HumanEditSummary {
  field: string;
  count: number;
  examples: string[];
}

export interface HumanApprovalTrendPoint {
  date: string;
  total: number;
  approved: number;
  retry_requested: number;
  rejected: number;
}

export interface HumanFeedbackSummary {
  total_approvals: number;
  resolved_approvals: number;
  approvals_with_feedback: number;
  approvals_with_edits: number;
  approval_rate: number;
  retry_request_rate: number;
  rejection_rate: number;
  common_reviewer_issues: ReviewerIssueSummary[];
  common_human_edits: HumanEditSummary[];
  approval_trend: HumanApprovalTrendPoint[];
}

export interface PromptVersion {
  id: string;
  agent_type: AgentType;
  name: string;
  version: number;
  template: string;
  is_active: boolean;
  notes: string | null;
  created_by_user_id: string | null;
  created_at: string;
}

export interface AgentSetting {
  id: string | null;
  agent_type: AgentType;
  model: string;
  temperature: number | null;
  max_tokens: number;
  timeout_seconds: number | null;
  max_retries: number;
  active_prompt_version_id: string | null;
  active_prompt_name: string | null;
  reviewer_approval_threshold: number | null;
  human_approval_threshold: number | null;
}

export interface UpdateAgentSettingRequest {
  model: string;
  temperature?: number | null;
  max_tokens: number;
  timeout_seconds?: number | null;
  max_retries: number;
  active_prompt_version_id?: string | null;
  reviewer_approval_threshold?: number | null;
  human_approval_threshold?: number | null;
}

export interface CreatePromptVersionRequest {
  agent_type: AgentType;
  name: string;
  version: number;
  template: string;
  is_active?: boolean;
  notes?: string | null;
  created_by_user_id?: string | null;
}

export interface HumanApprovalActionRequest {
  human_feedback?: string | null;
  approved_by_user_id?: string | null;
}

export interface HumanApprovalEditRequest {
  human_feedback?: string | null;
  edited_analysis_json?: Record<string, unknown> | null;
}

export interface CreateUploadedInputRequest {
  title: string;
  input_type: WorkflowType;
  raw_text: string;
  notes?: string | null;
  file_name?: string | null;
  file_type?: string | null;
  file_size?: number | null;
}

export interface UploadInputFileRequest {
  title: string;
  input_type: WorkflowType;
  notes?: string | null;
  file: File;
}

export interface DetectWorkflowRequest {
  title: string;
  raw_text: string;
  notes?: string | null;
}

export interface WorkflowDetection {
  workflow_type: WorkflowType;
  confidence: number;
  reasoning_summary: string;
  recommended_action: "auto_select" | "confirm" | "manual_required";
}

export interface CreateWorkflowRunRequest {
  workflow_type: WorkflowType;
  run_mode?: RunMode;
  input_id?: string | null;
}

export interface DemoDatasetSummary {
  evaluation_cases: number;
  uploaded_inputs: number;
  workflow_runs: number;
  evaluation_results: number;
  agent_steps: number;
}
