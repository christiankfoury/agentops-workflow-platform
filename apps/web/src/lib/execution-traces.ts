export type TraceRecord = { id: string; [key: string]: unknown };
export type Preview = { text: string; truncated: boolean; limit: number };
export type TracePage = { items: TraceRecord[]; offset: number; next_offset: number | null };
export type TraceDetail = { record: TraceRecord; payloads: Record<string, Preview>; usage?: Record<string, unknown> | null };
export type TraceKind = "steps" | "attempts" | "events" | "tools" | "approvals";
export type TraceHead = { source: "generic" | "legacy"; execution_id?: string; run: TraceRecord;
  version?: { id: string; definition_id: string; number: number; name: string; graph_hash: string };
  graph?: { entry_node: string; nodes: { id: string; type: string }[]; edges: { source: string; target: string; label?: string; state: string }[] };
  latest_steps?: TraceRecord[]; checkpoint?: Preview; usage_source: string };
export type TraceRequest = { id: string; legacy?: boolean; kind?: TraceKind; step?: string; record?: string; offset?: number; payloads?: boolean };
export type TraceResult = { data?: TracePage | TraceDetail | Record<string, Preview>; error?: string };
export type TraceReader = (scope: string | null, request: TraceRequest) => Promise<TraceResult>;
export function tracePath(request: TraceRequest) {
  const encoded = encodeURIComponent, base = `/execution-traces/${request.legacy ? "legacy/" : ""}${encoded(request.id)}`;
  if (request.payloads && !request.legacy) return `${base}/payloads`;
  if (!request.kind || !["steps", "attempts", "events", "tools", "approvals"].includes(request.kind) || (request.legacy && request.kind !== "steps")) throw new Error("Unknown trace view");
  const path = `${base}/${request.legacy ? "steps" : `records/${request.kind}`}${request.record ? `/${encoded(request.record)}` : ""}`;
  return `${path}?offset=${request.offset ?? 0}&limit=25${request.step ? `&step_id=${encoded(request.step)}` : ""}`;
}
