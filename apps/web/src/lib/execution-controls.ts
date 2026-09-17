export type ControlState = {
  id: string; status: string; state_revision: number; source_id: string | null; recovery_id: string | null;
  can_cancel: boolean; can_recover: boolean; can_resolve: boolean; reasons: string[];
  jobs: { id: string; status: string; due_at: string; recovery_count: number; max_recoveries: number; lease_expires_at: string | null; can_retry: boolean; note: string }[];
  effects: { id: string; status: string; error_code: string | null; needs_resolution: boolean }[];
};
export type ControlRequest = { action: "read" } | { action: "cancel" | "recover"; reason: string }
  | { action: "retry"; job: string } | { action: "resolve"; effect: string; succeeded: boolean; result: unknown; evidence: string };
export type ControlResult = { state?: ControlState; recovery_id?: string; error?: string };
export type ControlAction = (scope: string | null, id: string, request: ControlRequest) => Promise<ControlResult>;
