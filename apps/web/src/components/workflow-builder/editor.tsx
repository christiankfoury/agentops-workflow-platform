"use client";

import { startTransition, useEffect, useRef, useState } from "react";
import { draftIssues, editableGraph, isObject, newNode, nodeTypes, starterGraph,
  type CatalogItem, type DraftBody, type DraftDefinition, type DraftResult, type NodeType, type ObjectValue } from "@/lib/workflow-builder";
import { changed, control, Field, JsonField, NodeConfig } from "./fields";

export function WorkflowBuilder({ initial, scope, canEdit, save, tools = [], prompts = [], catalogError = false }: {
  initial?: DraftDefinition; scope: string | null; canEdit: boolean; tools?: CatalogItem[]; prompts?: CatalogItem[]; catalogError?: boolean;
  save: (id: string | null, scope: string | null, body: DraftBody) => Promise<DraftResult>;
}) {
  const [definition, setDefinition] = useState(initial);
  const [name, setName] = useState(initial?.name ?? "Untitled workflow");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [graph, setGraph] = useState<ObjectValue>(initial?.draft_graph ?? starterGraph());
  const [rawMode, setRawMode] = useState(() => !editableGraph(initial?.draft_graph ?? starterGraph()));
  const [selected, setSelected] = useState("");
  const [type, setType] = useState<NodeType>("transform");
  const [buffers, setBuffers] = useState<Record<string, { raw: string; error: string | null }>>({});
  const [busy, setBusy] = useState(false), [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState(""), [errors, setErrors] = useState<string[]>([]);
  const [source, setSource] = useState(""), [target, setTarget] = useState(""), [label, setLabel] = useState("");
  const counter = useRef(0);
  const saving = useRef(false);
  const supported = editableGraph(graph);
  const nodes = supported ? graph.nodes : [], edges = supported ? graph.edges : [];
  const node = nodes.find(n => n.id === selected);
  const disabled = !canEdit || !!definition?.archived || busy;
  const jsonErrors = Object.entries(buffers).filter(([, v]) => v.error).map(([k, v]) => `${k}: ${v.error}`);
  const issues = draftIssues(graph);
  useEffect(() => {
    function warn(event: BeforeUnloadEvent) { if (dirty) { event.preventDefault(); event.returnValue = ""; } }
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function update(next: ObjectValue) { setGraph(next); setDirty(true); setNotice(""); }
  function graphValue(key: string, value: unknown) { update(changed(graph, key, value)); }
  function nodeValue(key: string, value: unknown) { if (node) graphValue("nodes", nodes.map(n => n.id === node.id ? changed(n, key, value) : n)); }
  function json(key: string, title: string, value: unknown, apply: (v: unknown) => void, optional = false) {
    return <JsonField key={key} label={title} value={value} raw={buffers[key]?.raw} optional={optional}
      onChange={(raw, parsed, error) => {
        setBuffers(old => ({ ...old, [key]: { raw, error } })); setDirty(true);
        if (!error) apply(parsed);
      }} />;
  }
  async function submit() {
    try {
      const result = await save(definition?.id ?? null, scope, { name, description, graph,
        ...(definition ? { expected_revision: definition.draft_revision } : {}) });
      if (result.definition) {
        setDefinition(result.definition); setGraph(result.definition.draft_graph);
        setName(result.definition.name); setDescription(result.definition.description); setBuffers({});
        setDirty(false); setNotice(`Saved draft revision ${result.definition.draft_revision}.`);
      }
      else { setNotice(result.error ?? "Save failed. Your edits are retained."); setErrors(result.fields ?? []); }
    } catch { setNotice("The connection failed. Your edits are retained; retry saving."); }
    finally { saving.current = false; setBusy(false); }
  }
  return <form onSubmit={event => {
    event.preventDefault(); if (disabled || jsonErrors.length || saving.current) return;
    saving.current = true; setBusy(true); setNotice(""); setErrors([]); startTransition(submit);
  }} className="space-y-6 break-words">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><h1 className="text-2xl font-bold">Workflow builder</h1><p className="text-sm text-muted-foreground">Draft {definition ? `revision ${definition.draft_revision}` : "· new workflow"} · {dirty ? "Unsaved edits" : definition ? "Saved state" : "Not saved yet"}</p></div>
      <button className="rounded-md bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50" disabled={disabled || jsonErrors.length > 0}>{busy ? "Saving…" : "Save draft"}</button>
    </header>
    {!canEdit && <p role="status">Read-only access. An operator or administrator can edit drafts.</p>}
    {definition?.archived && <p role="status">This workflow is archived and cannot be edited.</p>}
    {notice && <p role="status" className="rounded-md border p-3">{notice}</p>}
    {definition && <a className="text-sm underline" href={`/workflow-definitions/${encodeURIComponent(definition.id)}`} target="_blank" rel="noreferrer">Open saved draft in a new tab</a>}
    {!!errors.length && <ul role="alert" className="text-red-600">{errors.map(e => <li key={e}>{e}</li>)}</ul>}
    {catalogError && <p role="status">Some tool or prompt choices are unavailable. Existing selections are retained. Reload to retry loading the catalog.</p>}
    <button type="button" className="rounded border px-3 py-2 text-sm" disabled={busy || jsonErrors.length > 0 || (rawMode && !supported)} onClick={() => {
      setRawMode(!rawMode); setBuffers({}); setSelected(""); setSource(""); setTarget(""); setLabel("");
    }}>{rawMode ? "Use visual editor" : "Edit graph JSON"}</button>
    {supported && !rawMode && <Field label="Inspect node" value={selected} options={nodes.map(n => ({ id: n.id, name: `${n.id} · ${n.type}` }))} onChange={v => setSelected(String(v))} />}
    <fieldset disabled={disabled} className="min-w-0 space-y-6">
      <legend className="sr-only">Draft editing</legend>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium">Workflow name<input className={control} value={name} required maxLength={200} onChange={e => { setName(e.target.value); setDirty(true); }} /></label>
        <label className="text-sm font-medium">Description<input className={control} value={description} maxLength={4000} onChange={e => { setDescription(e.target.value); setDirty(true); }} /></label>
      </div>
      {supported && !rawMode && <>
        <section className="rounded-lg border border-border bg-card p-4" aria-label="Graph canvas">
          <h2 className="font-semibold">Graph</h2><p className="mb-3 text-sm text-muted-foreground">Select a node below to edit. Arrows follow the connection list. Every operation is available by keyboard.</p>
          <div className="overflow-x-auto">
            <svg role="img" aria-label="Workflow connection diagram" width={Math.max(420, nodes.length * 180)} height={140} className="text-muted-foreground">
              <defs><marker id="builder-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" /></marker></defs>
              {edges.map((e, i) => { const a = nodes.findIndex(n => n.id === e.source), b = nodes.findIndex(n => n.id === e.target); return a < 0 || b < 0 ? null : <path key={i} d={`M ${a * 180 + 90} 78 Q ${(a + b) * 90 + 90} ${15 + i % 3 * 12} ${b * 180 + 90} 78`} stroke="currentColor" fill="none" markerEnd="url(#builder-arrow)" />; })}
              {nodes.map((n, i) => <g key={n.id}><rect x={i * 180 + 10} y={80} width={160} height={45} rx={8} fill="var(--card)" stroke="currentColor" /><text x={i * 180 + 90} y={108} textAnchor="middle" fill="currentColor" fontSize={12}>{n.id.length > 20 ? `${n.id.slice(0, 18)}…` : n.id}</text></g>)}
            </svg>
          </div>
          <div className="my-3 flex flex-wrap gap-2">{nodes.map(n => <button type="button" key={n.id} aria-pressed={selected === n.id} className={`rounded border px-3 py-2 text-sm ${selected === n.id ? "bg-accent font-bold" : ""}`} onClick={() => setSelected(n.id)}>{n.id} · {n.type}</button>)}</div>
          {!nodes.length && <p>No nodes yet. Add a step to begin.</p>}
          <div className="flex flex-wrap items-end gap-3"><Field label="New step type" value={type} options={nodeTypes.map(id => ({ id, name: id }))} onChange={v => { if (nodeTypes.includes(v as NodeType)) setType(v as NodeType); }} />
            <button type="button" className="rounded border px-3 py-2" onClick={() => {
              let id: string; do { id = `${type}_${++counter.current}`; } while (JSON.stringify(graph).includes(`"${id}"`));
              graphValue("nodes", [...nodes, newNode(type, id)]); setSelected(id);
            }}>Add node</button></div>
        </section>
        <div className="grid min-w-0 gap-6 xl:grid-cols-2">
          <section className="min-w-0 space-y-4 rounded-lg border p-4"><h2 className="font-semibold">{node ? `Node: ${node.id}` : "Node settings"}</h2>
            {!node ? <p className="text-sm text-muted-foreground">Select a node to configure it.</p> : <>
              <p className="text-sm">Type: {node.type}. Node IDs stay stable so bindings keep their meaning.</p>
              <NodeConfig node={node} tools={tools} prompts={prompts} set={(k, v) => nodeValue("config", changed(node.config, k, v))}
                json={(k, title, v, optional) => json(`${node.id}.config.${k}`, title, v, value => nodeValue("config", changed(node.config, k, value)), optional)} />
              <Field label="Node timeout (seconds)" value={node.timeout_seconds ?? 60} type="number" min={0.001} max={3600} onChange={v => nodeValue("timeout_seconds", v)} />
              <Field label="Merge policy" value={node.merge} optional options={[{ id: "exclusive", name: "Exclusive" }]} onChange={v => nodeValue("merge", v)} />
              {json(`${node.id}.inputs`, "Input bindings JSON", node.inputs ?? {}, v => nodeValue("inputs", v))}
              {json(`${node.id}.input_schema`, "Node input schema JSON", node.input_schema, v => nodeValue("input_schema", v))}
              {json(`${node.id}.output_schema`, "Node output schema JSON", node.output_schema, v => nodeValue("output_schema", v))}
              {json(`${node.id}.retry`, "Retry policy JSON", node.retry ?? { max_attempts: 1, retryable_errors: [], initial_delay_seconds: 1, max_delay_seconds: 60, backoff_factor: 2, jitter_fraction: 0.2 }, v => nodeValue("retry", v))}
              <button type="button" className="rounded border border-red-500 px-3 py-2" onClick={() => {
                update({ ...graph, nodes: nodes.filter(n => n.id !== node.id), edges: edges.filter(e => e.source !== node.id && e.target !== node.id) });
                setBuffers(old => Object.fromEntries(Object.entries(old).filter(([k]) => !k.startsWith(`${node.id}.`)))); setSelected("");
              }}>Remove node {node.id}</button>
            </>}
          </section>
          <section className="min-w-0 space-y-4 rounded-lg border p-4"><h2 className="font-semibold">Connections and workflow settings</h2>
            <Field label="Entry node" value={graph.entry_node} options={nodes.map(n => ({ id: n.id, name: n.id }))} onChange={v => graphValue("entry_node", v)} />
            <div className="grid gap-3 sm:grid-cols-2"><Field label="From node" value={source} options={nodes.map(n => ({ id: n.id, name: n.id }))} onChange={v => setSource(String(v))} />
              <Field label="To node" value={target} options={nodes.map(n => ({ id: n.id, name: n.id }))} onChange={v => setTarget(String(v))} /></div>
            <Field label="Outcome label (optional)" value={label} onChange={v => setLabel(String(v))} />
            <button type="button" className="rounded border px-3 py-2" disabled={!source || !target} onClick={() => graphValue("edges", [...edges, { source, target, ...(label ? { label } : {}) }])}>Add connection</button>
            <ul className="space-y-2">{edges.map((e, i) => <li key={i} className="flex flex-wrap justify-between gap-2 text-sm"><span>{e.source} → {e.target}{e.label ? ` (${e.label})` : ""}</span><button type="button" className="underline" aria-label={`Remove connection ${i + 1}`} onClick={() => graphValue("edges", edges.filter((_, j) => j !== i))}>Remove</button></li>)}</ul>
            <Field label="Workflow timeout (seconds)" value={graph.overall_timeout_seconds ?? 86400} type="number" min={0.001} max={2592000} onChange={v => graphValue("overall_timeout_seconds", v)} />
            {json("graph.input_schema", "Workflow input schema JSON", graph.input_schema, v => graphValue("input_schema", v))}
            {json("graph.output_schema", "Workflow output schema JSON", graph.output_schema, v => graphValue("output_schema", v))}
            {json("graph.outputs", "Output bindings JSON", graph.outputs ?? {}, v => graphValue("outputs", v))}
            {json("graph.quality_revision", "Bounded quality revision JSON (optional)", graph.quality_revision, v => graphValue("quality_revision", v), true)}
            <p className="text-sm text-muted-foreground">Revision settings: entry_node, review_node, nodes, max_revisions (1–5), optional approval_node, retry_on_low_score and retry_on_high_severity. Bindings use literal, ref or operator expressions.</p>
          </section>
        </div>
      </>}
      {(rawMode || !supported) && <section className="space-y-3 rounded border p-4"><h2 className="font-semibold">Graph JSON editor</h2><p>Edit the complete graph, including fields outside the visual forms. Structural repairs are required before returning to the visual editor. Original values are preserved until you edit them.</p>
        {json("rawGraph", "Graph JSON", graph, v => { if (isObject(v)) update(v); else setBuffers(old => ({ ...old, rawGraph: { raw: JSON.stringify(v), error: "Graph must be an object" } })); })}
      </section>}
    </fieldset>
    {(issues.length > 0 || jsonErrors.length > 0) && <section className="rounded-lg border border-amber-500 p-4" aria-label="Draft diagnostics"><h2 className="font-semibold">Draft needs attention</h2><p className="text-sm">Incomplete configurations may be saved. Invalid JSON must be repaired first. These checks do not establish that a workflow can run.</p><ul className="mt-2 list-inside list-disc text-sm">{[...jsonErrors, ...issues].map((e, i) => <li key={i}>{e}</li>)}</ul></section>}
  </form>;
}
