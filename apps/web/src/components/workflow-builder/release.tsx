"use client";

import { startTransition, useRef, useState } from "react";
import type { DraftDefinition } from "@/lib/workflow-builder";
import { isObject } from "@/lib/workflow-builder";
import type { ActionResult, PlatformAction, PlatformActionHandler, StartRequest, Validation, Version } from "@/lib/workflow-release";
import { Field, JsonField } from "./fields";

function ValidationDetails({ value }: { value: Validation }) {
  return <section className="space-y-2 rounded border p-3" aria-label="Validation result">
    <p>{value.valid ? "Graph structure is valid." : "Graph needs repairs."} {value.executable ? "Runtime capabilities are available." : "This configuration cannot currently run."}</p>
    {value.draft_revision != null && <p>Checked draft revision {value.draft_revision}.</p>}
    <ul className="list-inside list-disc text-sm">{[...value.errors, ...value.runtime_errors].map((e, i) => <li key={i}>{e.loc?.join(" · ") || "Graph"}: {e.msg || "Invalid configuration"}</li>)}</ul>
  </section>;
}

export function WorkflowRelease({ initial, initialVersions, scope, permissions, action }: {
  initial: DraftDefinition; initialVersions: Version[]; scope: string | null; permissions: string[]; action: PlatformActionHandler;
}) {
  const [definition, setDefinition] = useState(initial), [versions, setVersions] = useState(initialVersions);
  const [validation, setValidation] = useState<Validation>(), [capabilities, setCapabilities] = useState<Validation>();
  const [selected, setSelected] = useState(initialVersions.find(v => v.id === initial.published_version_id)?.id ?? initialVersions[0]?.id ?? "");
  const [before, setBefore] = useState(initialVersions[1]?.id ?? ""), [diff, setDiff] = useState("");
  const [input, setInput] = useState("{}"), [inputError, setInputError] = useState<string | null>(null);
  const [request, setRequest] = useState<StartRequest | null>(null);
  const [accepted, setAccepted] = useState<{ id: string; version_id: string; status: string }>();
  const [busy, setBusy] = useState(false), [notice, setNotice] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const pending = useRef(false);
  const choices = versions.map(v => ({ id: v.id, name: `v${v.number} · ${v.name}${v.archived_at ? " (archived)" : ""}` }));
  const selectedVersion = versions.find(v => v.id === selected);
  function perform(command: PlatformAction, success: (data: unknown) => void) {
    if (pending.current) return;
    pending.current = true; setBusy(true); setNotice(""); setErrors([]);
    startTransition(async () => {
      try {
        const result: ActionResult = await action(scope, command);
        if (result.error) { setNotice(result.error); setErrors(result.fields ?? []); }
        else success(result.data);
      } catch { setNotice("Connection failed. Retry the same request when available."); }
      finally { pending.current = false; setBusy(false); }
    });
  }
  const button = "rounded border px-3 py-2 text-sm disabled:opacity-50";
  return <div className="space-y-6 break-words">
    <header><h1 className="text-2xl font-bold">Validate and publish · {definition.name}</h1>
      <p className="text-sm text-muted-foreground">Saved draft revision {definition.draft_revision}. Published versions are immutable; existing runs keep their pinned version.</p></header>
    {notice && <p role="status" className="rounded border p-3">{notice}</p>}
    {!!errors.length && <ul role="alert">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>}
    <section className="space-y-4 rounded-lg border bg-card p-4"><h2 className="font-semibold">Saved draft validation</h2>
      <p className="text-sm">Save edits in the builder before checking or publishing. Publication rechecks the current draft and its runtime capabilities.</p>
      <div className="flex flex-wrap gap-3"><button className={button} disabled={busy} onClick={() => perform({ op: "validate", definition: definition.id }, data => setValidation(data as Validation))}>Validate saved draft</button>
        {permissions.includes("workflow.publish") && <button className={button} disabled={busy || definition.archived || !validation?.valid || !validation.executable || validation.draft_revision !== definition.draft_revision}
          onClick={() => perform({ op: "publish", definition: definition.id, revision: definition.draft_revision }, data => {
            const result = data as { definition: DraftDefinition; version: Version };
            setDefinition(result.definition); setVersions(old => [result.version, ...old.filter(v => v.id !== result.version.id)]);
            setValidation(undefined); setCapabilities(undefined); setDiff(""); if (!request) setSelected(result.version.id);
            setNotice(`Published version ${result.version.number}. Running workflows retain their earlier versions.`);
          })}>Publish saved draft</button>}</div>
      {!permissions.includes("workflow.publish") && <p className="text-sm">Publication requires an administrator.</p>}
      {validation && <ValidationDetails value={validation} />}
      {validation && validation.draft_revision !== definition.draft_revision && <p role="alert">The draft changed since this page loaded. Reload to review the current saved draft before publishing.</p>}
    </section>
    <section className="space-y-4 rounded-lg border p-4"><h2 className="font-semibold">Published versions</h2>
      {!versions.length ? <p>No published versions yet.</p> : <>
        <fieldset disabled={busy || !!request}><Field label="Published version" value={selected} options={choices} onChange={v => { setSelected(String(v)); setCapabilities(undefined); setDiff(""); }} /></fieldset>
        {selectedVersion && <p className="text-sm">v{selectedVersion.number} · source draft {selectedVersion.source_revision} · {selectedVersion.created_at} · {selectedVersion.id === definition.published_version_id ? "Current published version" : "Historical version"}</p>}
        <button className={button} disabled={busy || !selected} onClick={() => perform({ op: "capabilities", definition: definition.id, version: selected }, data => setCapabilities(data as Validation))}>Check version capabilities</button>
        {capabilities && <ValidationDetails value={capabilities} />}
        <fieldset disabled={busy}><Field label="Compare with version" value={before} options={choices} onChange={v => { setBefore(String(v)); setDiff(""); }} /></fieldset>
        <button className={button} disabled={busy || !selected || !before || before === selected} onClick={() => perform({ op: "diff", definition: definition.id, version: selected, before }, data => setDiff((data as { diff: string }).diff || "No content differences."))}>Show version diff</button>
        {diff && <pre aria-label="Version diff" className="max-h-96 overflow-auto whitespace-pre-wrap rounded bg-muted p-3 text-xs">{diff.slice(0, 120000)}{diff.length > 120000 ? "\nPreview limited to 120,000 characters." : ""}</pre>}
      </>}
    </section>
    <section className="space-y-4 rounded-lg border p-4"><h2 className="font-semibold">Manual start</h2>
      <p className="text-sm">The selected version and input are frozen on the first attempt. Retry keeps the same request key, including after a connection failure. Keep this page open while resolving an uncertain start.</p>
      <fieldset disabled={busy || !!request || !permissions.includes("workflow.start")}><JsonField label="Run input JSON" value={{}} raw={input} onChange={(raw, value, error) => {
        setInput(raw); setInputError(error ?? (isObject(value) ? null : "Run input must be a JSON object."));
      }} /></fieldset>
      {inputError && <p role="alert">{inputError}</p>}
      {permissions.includes("workflow.start") ? <div className="flex flex-wrap gap-3">
        <button className={button} disabled={busy || (!request && (!selected || !!selectedVersion?.archived_at || definition.archived || !!inputError))} onClick={() => {
          if (pending.current) return;
          const current = request ?? { definition_id: definition.id, version_id: selected, input: JSON.parse(input), idempotency_key: crypto.randomUUID() };
          setRequest(current); perform({ op: "start", request: current }, data => { setAccepted(data as typeof accepted); setNotice("Run accepted. Retrying this request returns the same run."); });
        }}>{request ? "Retry same start" : "Start selected version"}</button>
        {request && <button className={button} disabled={busy} onClick={() => { setRequest(null); setAccepted(undefined); setNotice("Ready to prepare a separate run with a new request key."); }}>Prepare a separate run</button>}
      </div> : <p>Starting a run requires operator permission.</p>}
      {request && <p className="break-all text-xs">Request key: {request.idempotency_key} · version: {request.version_id}</p>}
      {accepted && <p role="status" className="text-sm">Run {accepted.id} · version {accepted.version_id} · {accepted.status}</p>}
    </section>
  </div>;
}
