"use client";

import { startTransition, useEffect, useRef, useState } from "react";
import type { Preview, TraceDetail, TraceHead, TraceKind, TracePage, TraceReader, TraceRecord, TraceRequest } from "@/lib/execution-traces";

const button = "rounded border px-3 py-2 text-sm disabled:opacity-50";
export function Payloads({ values }: { values: Record<string, Preview> }) {
  return <div className="space-y-4">{Object.entries(values).map(([name, value]) => <section key={name}><h3 className="font-semibold">{name.replaceAll("_", " ")}</h3>
    {value.truncated && <p className="text-sm">Preview limited to {value.limit.toLocaleString()} characters or the structure limit.</p>}
    <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-all rounded bg-muted p-3 text-xs" aria-label={name}>{value.text}</pre>
  </section>)}</div>;
}
function Facts({ record }: { record: TraceRecord }) {
  return <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">{Object.entries(record).map(([name, value]) => <div key={name} className="min-w-0"><dt className="text-muted-foreground">{name.replaceAll("_", " ")}</dt><dd className="break-all">{value == null ? "Unavailable" : String(value)}</dd></div>)}</dl>;
}
export function TraceDebugger({ head, initial, initialError, scope, read }: {
  head: TraceHead; initial: TracePage; initialError?: boolean; scope: string | null; read: TraceReader;
}) {
  const [kind, setKind] = useState<TraceKind>("steps"), [page, setPage] = useState(initial);
  const [step, setStep] = useState<string>(), [detail, setDetail] = useState<TraceDetail>();
  const [payloads, setPayloads] = useState<Record<string, Preview>>(), [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError ? "Step history is unavailable. Reload this section to retry." : "");
  const [notice, setNotice] = useState("");
  const pending = useRef(false), legacy = head.source === "legacy";
  const generation = useRef(0), lastHead = useRef(head);
  const selectedSection = useRef<HTMLElement>(null);
  useEffect(() => { if (detail) selectedSection.current?.focus(); }, [detail]);
  useEffect(() => {
    if (lastHead.current === head) return;
    lastHead.current = head;
    const current = ++generation.current;
    let active = true;
    async function refreshVisible() {
      try {
        const result = await read(scope, { id: head.run.id, legacy, kind, offset: page.offset, step });
        if (!active || current !== generation.current) return;
        if (result.error) setError(result.error);
        else { setPage(result.data as TracePage); setDetail(undefined); setPayloads(undefined);
          setNotice("Visible history refreshed; select a record for its latest detail."); }
      } catch { if (active && current === generation.current) setError("Live history refresh failed. Reload this section."); }
    }
    void refreshVisible();
    return () => { active = false; };
  }, [head, legacy, kind, page.offset, step, read, scope]);
  function request(input: Partial<TraceRequest>, accept: (data: unknown) => void) {
    if (pending.current) return;
    const current = ++generation.current;
    pending.current = true; setBusy(true); setError(""); setNotice("");
    startTransition(async () => {
      try { const result = await read(scope, { id: head.run.id, legacy, ...input });
        if (current !== generation.current) return;
        if (result.error) setError(result.error); else accept(result.data);
      } catch { if (current === generation.current) setError("Connection failed. The existing trace remains visible; retry this section."); }
      finally { pending.current = false; setBusy(false); }
    });
  }
  function load(nextKind: TraceKind, offset = 0, nextStep?: string) {
    request({ kind: nextKind, offset, step: nextStep }, data => { setKind(nextKind); setStep(nextStep); setPage(data as TracePage); setDetail(undefined); });
  }
  function inspect(row: TraceRecord, rowKind = kind) {
    request({ kind: rowKind, record: row.id, step: rowKind === "attempts" ? step : undefined }, data => setDetail(data as TraceDetail));
  }
  const graph = head.graph;
  const latest = new Map(head.latest_steps?.map(row => [String(row.node_id), row]));
  return <div className="space-y-6 break-words">
    <header><h1 className="text-2xl font-bold">{legacy ? "Historical run trace" : `Run debugger · ${head.version?.name}`}</h1>
      <p className="break-all text-sm">Run {head.run.id} · {String(head.run.status)}</p>
      {head.version && <p className="break-all text-sm">Pinned version {head.version.number} · {head.version.id}</p>}
      <p className="text-sm text-muted-foreground">{head.usage_source}</p>
      {legacy && <p>No immutable graph was recorded for this historical run. Original agent labels and totals are preserved.</p>}
    </header>
    <section className="rounded-lg border p-4"><h2 className="mb-3 font-semibold">Run state</h2><Facts record={head.run} />
      {!legacy && <button className={`${button} mt-4`} disabled={busy} onClick={() => request({ payloads: true }, data => setPayloads(data as Record<string, Preview>))}>Load run input, output and errors</button>}
      {payloads && <Payloads values={payloads} />}
    </section>
    {graph && <section className="space-y-3 rounded-lg border p-4" aria-label="Pinned run graph"><h2 className="font-semibold">Pinned graph</h2>
      <p className="text-sm">Node badges show the latest logical iteration. Edge decisions describe the current checkpoint. Select a node or use step history for earlier attempts.</p>
      <div className="max-h-[600px] overflow-auto"><svg role="img" aria-label="Immutable graph with current edge decisions" viewBox={`0 0 620 ${Math.max(100, graph.nodes.length * 65)}`} style={{ height: Math.max(100, graph.nodes.length * 65) }} className="min-w-[620px] w-full">
        {graph.edges.map((edge, i) => { const from = graph.nodes.findIndex(n => n.id === edge.source), to = graph.nodes.findIndex(n => n.id === edge.target); return <g key={i}><path d={`M 290 ${from * 65 + 30} C ${340 + i % 8 * 25} ${from * 65 + 30}, ${340 + i % 8 * 25} ${to * 65 + 30}, 290 ${to * 65 + 30}`} fill="none" stroke={edge.state === "selected" ? "#16a34a" : edge.state === "skipped" ? "#d97706" : "#64748b"} strokeDasharray={edge.state === "skipped" ? "5 4" : undefined}><title>{edge.source} → {edge.target}: {edge.state}</title></path></g>; })}
        {graph.nodes.map((node, i) => <g key={node.id}><rect x="10" y={i * 65 + 7} width="280" height="45" rx="6" fill="var(--background)" stroke="#64748b" /><text x="20" y={i * 65 + 34} fill="currentColor" fontSize="13">{node.id} · {String(latest.get(node.id)?.status ?? "not started")}</text></g>)}
      </svg></div>
      <div className="flex flex-wrap gap-2">{graph.nodes.map(node => <button key={node.id} className={button} disabled={busy} onClick={() => { const row = latest.get(node.id); if (row) inspect(row, "steps"); else { setDetail(undefined); setNotice(`No step record exists for ${node.id} yet.`); } }}>{node.id} · {node.type} · {String(latest.get(node.id)?.status ?? "not started")}</button>)}</div>
      <details><summary>Edge decisions and branch state</summary><ul className="text-sm">{graph.edges.map((edge, i) => <li key={i}>{edge.source} → {edge.target}{edge.label ? ` (${edge.label})` : ""}: {edge.state}</li>)}</ul>{head.checkpoint && <Payloads values={{ checkpoint: head.checkpoint }} />}</details>
    </section>}
    {error && <p role="alert" className="rounded border p-3">{error}</p>}{notice && <p role="status">{notice}</p>}
    <section className="space-y-4 rounded-lg border p-4"><h2 className="font-semibold">Trace history · {kind}</h2>
      <nav aria-label="Trace sections" className="flex flex-wrap gap-2">{(legacy ? ["steps"] : ["steps", "events", "tools", "approvals"]).map(value => <button key={value} className={button} disabled={busy} aria-pressed={kind === value} onClick={() => load(value as TraceKind)}>{value[0].toUpperCase() + value.slice(1)}</button>)}<button className={button} disabled={busy} onClick={() => load(kind, page.offset, step)}>Reload section</button></nav>
      {step && <p className="break-all text-sm">Attempts for step {step}</p>}
      {!page.items.length && <p>No records on this page.</p>}
      <ul className="space-y-3">{page.items.map(row => <li key={row.id} className="space-y-3 rounded border p-3"><Facts record={row} /><div className="flex flex-wrap gap-2"><button className={button} disabled={busy} onClick={() => inspect(row)}>Inspect {row.id}</button>{kind === "steps" && !legacy && <button className={button} disabled={busy} onClick={() => load("attempts", 0, row.id)}>Attempts for {row.id}</button>}</div></li>)}</ul>
      <nav aria-label="Trace pages" className="flex gap-3"><button className={button} disabled={busy || page.offset === 0} onClick={() => load(kind, Math.max(0, page.offset - 25), step)}>Previous page</button><button className={button} disabled={busy || page.next_offset == null} onClick={() => load(kind, page.next_offset!, step)}>Next page</button></nav>
    </section>
    {detail && <section ref={selectedSection} tabIndex={-1} className="space-y-4 rounded-lg border p-4" aria-label="Selected trace record"><h2 className="font-semibold">Selected record · {detail.record.id}</h2><Facts record={detail.record} />
      {detail.usage && <section><h3 className="mb-3 font-semibold">Selected attempt usage</h3><Facts record={{ id: detail.record.id, ...detail.usage }} /><p className="text-sm">Unknown cost or usage remains unavailable; these values are not added to historical totals.</p></section>}
      <Payloads values={detail.payloads} /></section>}
  </div>;
}
