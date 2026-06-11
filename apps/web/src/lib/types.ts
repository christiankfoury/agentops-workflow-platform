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
