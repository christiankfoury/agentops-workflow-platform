import type { ObjectValue } from "./workflow-builder";

export type Version = { id: string; definition_id: string; number: number; source_revision: number;
  name: string; description: string; graph: ObjectValue; created_at: string; archived_at: string | null; graph_hash: string };
export type Validation = { valid: boolean; executable: boolean; draft_revision: number | null;
  errors: { loc?: (string | number)[]; msg?: string }[]; runtime_errors: { loc?: (string | number)[]; msg?: string }[] };
export type TriggerKind = "webhook" | "schedule";
export type Trigger = ObjectValue & { id: string; name: string; definition_id: string; revision: number; enabled: boolean;
  service_principal_id: string; version_policy: "published" | "pinned"; version_id: string | null };
export type StartRequest = { definition_id: string; version_id: string; input: ObjectValue; idempotency_key: string };
export type PlatformAction =
  | { op: "validate"; definition: string }
  | { op: "publish"; definition: string; revision: number }
  | { op: "capabilities"; definition: string; version: string }
  | { op: "diff"; definition: string; version: string; before: string }
  | { op: "start"; request: StartRequest }
  | { op: "save-trigger"; kind: TriggerKind; id: string | null; body: ObjectValue }
  | { op: "rotate"; id: string; revision: number; alias: string; grace: number }
  | { op: "history"; kind: TriggerKind; id: string; offset: number };
export type ActionResult = { data?: unknown; error?: string; fields?: string[] };
export type PlatformActionHandler = (scope: string | null, action: PlatformAction) => Promise<ActionResult>;
export function triggerPath(kind: TriggerKind) {
  if (kind === "webhook") return "/webhook-triggers";
  if (kind === "schedule") return "/workflow-schedules";
  throw new Error("Unknown trigger type");
}
export function triggerConfig(kind: TriggerKind, record?: Trigger, definition = ""): ObjectValue {
  const common = { name: record?.name ?? "New trigger", definition_id: record?.definition_id ?? definition,
    service_principal_id: record?.service_principal_id ?? "", enabled: record?.enabled ?? false,
    version_policy: record?.version_policy ?? "published", version_id: record?.version_id ?? null };
  return kind === "webhook" ? { ...common, input_mapping: record?.input_mapping ?? null,
    max_payload_bytes: record?.max_payload_bytes ?? 65536, freshness_seconds: record?.freshness_seconds ?? 300 }
    : { ...common, cron: record?.cron ?? "0 9 * * *", timezone: record?.timezone ?? "UTC", input: record?.input ?? {},
      concurrency_policy: "forbid", missed_run_policy: "coalesce" };
}
