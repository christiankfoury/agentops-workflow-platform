// Shared types for AgentOps Workflow Platform.
// Workflow state types and API shapes will be added in later phases.

export type WorkflowStatus =
  | "created"
  | "running"
  | "analyst_running"
  | "reviewer_running"
  | "retrying"
  | "waiting_for_human"
  | "writer_running"
  | "completed"
  | "failed"
  | "cancelled";
