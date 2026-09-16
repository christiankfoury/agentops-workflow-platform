"use client";

import { startTransition, useRef, useState } from "react";
import { isObject, type ObjectValue } from "@/lib/workflow-builder";
import { triggerConfig, type ActionResult, type PlatformAction, type PlatformActionHandler, type Trigger, type TriggerKind } from "@/lib/workflow-release";
import { changed, Field, JsonField } from "./fields";

export function TriggerEditor({ kind, initial, definition = "", scope, canManage, action, initialHistory = [], historyError = false }: {
  kind: TriggerKind; initial?: Trigger; definition?: string; scope: string | null; canManage: boolean;
  action: PlatformActionHandler; initialHistory?: ObjectValue[]; historyError?: boolean;
}) {
  const [record, setRecord] = useState(initial), [config, setConfig] = useState(() => triggerConfig(kind, initial, definition));
  const [alias, setAlias] = useState(""), [rotationAlias, setRotationAlias] = useState(""), [grace, setGrace] = useState(300);
  const [raw, setRaw] = useState<string>(), [jsonError, setJsonError] = useState<string | null>(null);
  const [history, setHistory] = useState(initialHistory), [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false), [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState(historyError ? "History is unavailable. Reload history to retry." : ""), [errors, setErrors] = useState<string[]>([]);
  const pending = useRef(false);
  const payloadField = kind === "webhook" ? "input_mapping" : "input";
  function edit(key: string, value: unknown) { setConfig(old => changed(old, key, value)); setDirty(true); }
  function adopt(data: unknown) {
    const current = data as Trigger; setRecord(current); setConfig(triggerConfig(kind, current));
    setRaw(undefined); setJsonError(null); setAlias(""); setRotationAlias(""); setDirty(false);
  }
  function perform(command: PlatformAction, success: (data: unknown) => void) {
    if (pending.current) return;
    pending.current = true; setBusy(true); setNotice(""); setErrors([]);
    startTransition(async () => {
      try {
        const result: ActionResult = await action(scope, command);
        if (result.error) { setNotice(result.error); setErrors(result.fields ?? []); } else success(result.data);
      } catch { setNotice("The request failed. Your configuration is retained; retry when connected."); }
      finally { pending.current = false; setBusy(false); }
    });
  }
  const button = "rounded border px-3 py-2 text-sm disabled:opacity-50";
  function loadHistory(next: number) {
    if (record) perform({ op: "history", kind, id: record.id, offset: next }, data => { setHistory(data as ObjectValue[]); setOffset(next); });
  }
  return <div className="space-y-6 break-words">
    <header><h1 className="text-2xl font-bold">{kind === "webhook" ? "Webhook trigger" : "Cron schedule"}</h1><p className="text-sm text-muted-foreground">{record ? `Revision ${record.revision}` : "New configuration"} · {dirty ? "Unsaved edits" : record ? "Saved state" : "Not saved yet"}</p></header>
    {!canManage && <p role="status">Read-only access. Trigger management requires an administrator.</p>}
    {notice && <p role="status" className="rounded border p-3">{notice}</p>}
    {!!errors.length && <ul role="alert">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>}
    {record && <p className="text-sm">{kind === "webhook" ? `Delivery path: /webhooks/${record.id} · signing reference: ••••••••` : `Next fire: ${String(record.next_fire_at ?? "Unavailable")} · last decision: ${String(record.last_status ?? "None")}`}</p>}
    {record && <a className="text-sm underline" href={`/workflow-triggers/${kind}/${encodeURIComponent(record.id)}`} target="_blank" rel="noreferrer">Open saved trigger in a new tab</a>}
    <form onSubmit={event => {
      event.preventDefault(); if (!canManage || busy || jsonError) return;
      const body = { ...config, version_id: config.version_policy === "pinned" ? config.version_id : null,
        ...(record ? { expected_revision: record.revision } : kind === "webhook" ? { secret_alias: alias } : {}) };
      perform({ op: "save-trigger", kind, id: record?.id ?? null, body }, data => { adopt(data); setNotice("Configuration saved."); });
    }} className="space-y-4 rounded-lg border bg-card p-4">
      <fieldset disabled={!canManage || busy} className="space-y-4">
        <legend className="sr-only">Trigger configuration</legend>
        <Field label="Trigger name" value={config.name} onChange={v => edit("name", v)} />
        <Field label="Definition ID" value={config.definition_id} onChange={v => edit("definition_id", v)} />
        <Field label="Service principal ID" value={config.service_principal_id} onChange={v => edit("service_principal_id", v)} />
        <p className="text-sm text-muted-foreground">Use a provisioned service principal in this organization with workflow.start permission. Enablement checks its current authority.</p>
        <Field label="Version policy" value={config.version_policy} options={[{ id: "published", name: "Current published version" }, { id: "pinned", name: "Pin an immutable version" }]} onChange={v => edit("version_policy", v)} />
        {config.version_policy === "pinned" && <Field label="Pinned version ID" value={config.version_id} onChange={v => edit("version_id", v)} />}
        <Field label="Enabled" type="checkbox" value={config.enabled} onChange={v => edit("enabled", v)} />
        {kind === "webhook" ? <>
          {!record && <Field label="Configured signing alias" type="password" value={alias} onChange={v => { setAlias(String(v)); setDirty(true); }} />}
          <p className="text-sm text-muted-foreground">Reference a signing alias already configured by operations. Do not enter the signing key. Existing aliases and keys are never returned by this screen.</p>
          <Field label="Payload limit (bytes)" type="number" value={config.max_payload_bytes} min={1024} max={262144} onChange={v => edit("max_payload_bytes", v)} />
          <Field label="Signature freshness (seconds)" type="number" value={config.freshness_seconds} min={30} max={600} onChange={v => edit("freshness_seconds", v)} />
        </> : <>
          <Field label="Cron expression" value={config.cron} onChange={v => edit("cron", v)} />
          <Field label="Time zone" value={config.timezone} onChange={v => edit("timezone", v)} />
          <p className="text-sm text-muted-foreground">Five fields: minute, hour, day, month, weekday. One active run at a time; missed ticks coalesce into one catch-up decision. Invalid local times are skipped and repeated local times use their first occurrence. Schedule edits reset the next tick; pause/resume preserves it.</p>
        </>}
        <JsonField label={kind === "webhook" ? "Payload mapping JSON (optional)" : "Schedule input JSON"} value={config[payloadField]} raw={raw} optional={kind === "webhook"}
          onChange={(text, value, error) => {
            setRaw(text); setDirty(true);
            const invalid = error ?? (value == null && kind === "webhook" || isObject(value) ? null : "Enter a JSON object.");
            setJsonError(invalid); if (!invalid) edit(payloadField, value ?? null);
          }} />
        {jsonError && <p role="alert">{jsonError}</p>}
        {kind === "webhook" && <p className="text-sm text-muted-foreground">Blank forwards the complete signed payload. An object maps workflow input fields to references, for example {`{"name":{"source":"input","path":["customer"]}}`}.</p>}
      </fieldset>
      <button className={button} disabled={!canManage || busy || !!jsonError || (!record && kind === "webhook" && !alias)}>Save trigger</button>
    </form>
    {kind === "webhook" && record && <section className="space-y-4 rounded-lg border p-4"><h2 className="font-semibold">Rotate signing reference</h2>
      <p className="text-sm">Save configuration edits before rotating. The previous reference can remain valid for a bounded grace period.</p>
      <fieldset disabled={!canManage || busy || dirty} className="space-y-3"><Field label="New configured signing alias" type="password" value={rotationAlias} onChange={v => setRotationAlias(String(v))} />
        <Field label="Previous key grace (seconds)" type="number" min={0} max={3600} value={grace} onChange={v => setGrace(Number(v))} /></fieldset>
      <button className={button} disabled={!canManage || busy || dirty || !rotationAlias} onClick={() => perform({ op: "rotate", id: record.id, revision: record.revision, alias: rotationAlias, grace }, data => { adopt(data); setNotice("Signing reference rotated."); })}>Rotate signing reference</button>
      {record.previous_secret_until != null && <p className="text-sm">Previous reference expires: {String(record.previous_secret_until)}</p>}
    </section>}
    {record && <section className="space-y-3 rounded-lg border p-4"><h2 className="font-semibold">{kind === "webhook" ? "Delivery history" : "Fire history"}</h2>
      <button className={button} disabled={busy} onClick={() => loadHistory(offset)}>Reload history</button>
      {!history.length && <p>No recorded decisions on this page.</p>}
      <ul className="space-y-3">{history.map((row, i) => <li key={String(row.id ?? i)} className="rounded border p-3 text-sm">
        <p>{String(row.status)} · {String(row.scheduled_at ?? row.created_at ?? "")}</p>
        <p className="break-all">Run: {String(row.execution_id ?? "None")} · version: {String(row.version_id ?? "None")}</p>
        <p>Reason: {String(row.error_code ?? "None")}{kind === "webhook" ? ` · attempts: ${String(row.attempts)}` : ` · coalesced: ${row.coalesced ? "yes" : "no"}`}</p>
      </li>)}</ul>
      <nav aria-label="Trigger history pages" className="flex gap-3"><button className={button} disabled={busy || offset === 0} onClick={() => loadHistory(Math.max(0, offset - 50))}>Newer history</button><button className={button} disabled={busy || history.length < 50} onClick={() => loadHistory(offset + 50)}>Older history</button></nav>
    </section>}
  </div>;
}
