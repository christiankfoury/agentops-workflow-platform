"use client";

import { useId } from "react";
import type { CatalogItem, GraphNode, ObjectValue } from "@/lib/workflow-builder";

export const control = "mt-1 block w-full min-w-0 rounded-md border border-border bg-background px-3 py-2 text-sm disabled:opacity-60";
export function Field({ label, value, onChange, type = "text", min, max, options, optional = false }: {
  label: string; value: unknown; onChange: (value: unknown) => void; type?: "text" | "number" | "checkbox" | "password";
  min?: number; max?: number; options?: CatalogItem[]; optional?: boolean;
}) {
  const id = useId();
  const text = typeof value === "string" || typeof value === "number" ? String(value) : "";
  return <label className="block text-sm font-medium" htmlFor={id}>{label}
    {options ? <select id={id} className={control} value={text} onChange={e => onChange(e.target.value || (optional ? undefined : ""))}>
      <option value="">{optional ? "Not set" : "Select…"}</option>
      {text && !options.some(o => o.id === text) && <option value={text}>{text} (current value)</option>}
      {options.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
    </select> : type === "checkbox" ? <input id={id} className="ml-2" type="checkbox" checked={value === true} onChange={e => onChange(e.target.checked)} />
      : <input id={id} className={control} type={type} autoComplete={type === "password" ? "new-password" : undefined} min={min} max={max} step={type === "number" ? "any" : undefined}
        value={text} onChange={e => onChange(e.target.value === "" && optional ? undefined : type === "number" && e.target.value !== "" ? Number(e.target.value) : e.target.value)} />}
  </label>;
}
export function JsonField({ label, value, raw, onChange, optional = false }: {
  label: string; value: unknown; raw?: string; onChange: (raw: string, value: unknown, error: string | null) => void; optional?: boolean;
}) {
  const id = useId();
  const text = raw ?? (value == null && optional ? "" : JSON.stringify(value ?? {}, null, 2));
  let error: string | null = null;
  try { if (text || !optional) JSON.parse(text); } catch { error = "Enter valid JSON; the draft cannot save until this field is repaired."; }
  return <div><label className="block text-sm font-medium" htmlFor={id}>{label}</label>
    <textarea id={id} className={`${control} font-mono`} rows={5} value={text} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined}
      onChange={e => { const next = e.target.value; try { onChange(next, next === "" && optional ? undefined : JSON.parse(next), null); }
        catch { onChange(next, value, "Invalid JSON"); } }} />
    {error && <span id={`${id}-error`} role="alert" className="text-sm text-red-600">{error}</span>}
  </div>;
}

type Spec = { key: string; label: string; type?: "number" | "checkbox"; min?: number; max?: number; options?: string[]; optional?: boolean };
const specs: Record<GraphNode["type"], Spec[]> = {
  code: [{ key: "handler", label: "Handler" }, { key: "version", label: "Handler version", type: "number", min: 1 }],
  llm: [ { key: "model", label: "Model" }, { key: "max_tokens", label: "Maximum tokens", type: "number", min: 1, max: 32768 },
    { key: "temperature", label: "Temperature", type: "number", min: 0, max: 2, optional: true },
    { key: "use_agent_settings", label: "Use agent settings", type: "checkbox" },
    { key: "max_schema_repairs", label: "Schema repair attempts", type: "number", min: 0, max: 2, optional: true },
    { key: "output_validator", label: "Output validator", optional: true },
    { key: "max_tool_calls", label: "Maximum tool calls", type: "number", min: 1, max: 32, optional: true },
    { key: "max_provider_rounds", label: "Maximum provider rounds", type: "number", min: 1, max: 16, optional: true },
    { key: "max_cost_usd", label: "Maximum cost (USD)", type: "number", min: 0.000001, max: 100, optional: true }],
  tool: [{ key: "version", label: "Tool version", type: "number", min: 1 }, { key: "adapter", label: "Adapter", options: ["http", "postgresql", "github"] }, { key: "approval_node", label: "Approval node", optional: true }],
  condition: [{ key: "default", label: "Default outcome" }],
  approval: [{ key: "output_validator", label: "Output validator", optional: true }, { key: "max_review_retries", label: "Review retries", type: "number", min: 0, max: 5 },
    { key: "deadline_seconds", label: "Approval deadline (seconds)", type: "number", min: 0.001, max: 2592000, optional: true }, { key: "timeout_action", label: "Timeout action", options: ["reject", "fail"] }],
  transform: [], parallel: [{ key: "mode", label: "Parallel mode", options: ["fork", "join"] }], delay: [],
};
export function NodeConfig({ node, set, json, tools, prompts }: {
  node: GraphNode; set: (key: string, value: unknown) => void;
  json: (key: string, label: string, value: unknown, optional?: boolean) => React.ReactNode;
  tools: CatalogItem[]; prompts: CatalogItem[];
}) {
  const config = node.config;
  return <div className="space-y-4">
    {node.type === "llm" && <Field label="Prompt version" value={config.prompt_version_id} options={prompts} onChange={v => set("prompt_version_id", v)} />}
    {node.type === "tool" && <Field label="Tool" value={config.tool_id} options={tools} onChange={v => set("tool_id", v)} />}
    {specs[node.type].map(({ key, ...s }) => <Field key={key} {...s} value={config[key]} options={s.options?.map(id => ({ id, name: id }))}
      onChange={v => {
        set(key, v);
      }} />)}
    {node.type === "delay" && <>
      <p className="text-sm text-muted-foreground">Set one timer. Clear the other field. Wake time must include a UTC offset, for example 2026-10-01T09:00:00-04:00.</p>
      <Field label="Delay seconds" value={config.seconds} type="number" min={0} max={604800} optional onChange={v => set("seconds", v)} />
      <Field label="Wake at" value={config.wake_at} optional onChange={v => set("wake_at", v)} />
    </>}
    {node.type === "parallel" && <>
      <Field label="Join node" value={config.join_node} optional onChange={v => set("join_node", v)} />
      <Field label="Fork node" value={config.fork_node} optional onChange={v => set("fork_node", v)} />
      {json("branches", "Branches JSON · [{name, entry_node}]", config.branches ?? [])}
      <p className="text-sm text-muted-foreground">Forks need two or more branches and a join node. Joins use only a fork node. All selected branches must finish.</p>
    </>}
    {node.type === "condition" && json("cases", "Condition cases JSON · [{label, when}]", config.cases)}
    {node.type === "transform" && json("assign", "Assignments JSON", config.assign)}
    {node.type === "approval" && json("reviewer_roles", "Reviewer roles JSON", config.reviewer_roles)}
    {node.type === "llm" && <>{json("tools", "LLM tool aliases JSON", config.tools ?? {})}<p className="text-sm text-muted-foreground">Each alias specifies tool_id, version, adapter, optional approval_node and description. Published tools keep their version.</p></>}
  </div>;
}
export function changed(object: ObjectValue, key: string, value: unknown): ObjectValue {
  const next = { ...object }; if (value === undefined) delete next[key]; else next[key] = value; return next;
}
