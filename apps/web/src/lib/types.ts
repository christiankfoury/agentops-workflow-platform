export type WorkflowType = "sales_report" | "customer_feedback" | "incident_log";
export type RunMode = "baseline" | "multi_agent";
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

export interface CreateWorkflowRunRequest {
  workflow_type: WorkflowType;
  run_mode?: RunMode;
  input_id?: string | null;
}
