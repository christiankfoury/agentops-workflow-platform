"use client";

import Link from "next/link";
import { startTransition, useEffect, useRef, useState } from "react";
import type { ControlAction, ControlRequest, ControlState } from "@/lib/execution-controls";

const button = "rounded border px-3 py-2 text-sm disabled:opacity-50";
export function ExecutionControls({ id, scope, action, refreshToken }: { id: string; scope: string | null; action: ControlAction; refreshToken?: unknown }) {
  const [state, setState] = useState<ControlState>(), [error, setError] = useState("");
  const [busy, setBusy] = useState(false), [reason, setReason] = useState("");
  const [recovery, setRecovery] = useState<string>(), [notice, setNotice] = useState("");
  const pending = useRef(false);
  const generation = useRef(0), lastRefresh = useRef(refreshToken);
  useEffect(() => {
    if (!state || busy || lastRefresh.current === refreshToken) return;
    lastRefresh.current = refreshToken;
    const current = ++generation.current;
    let active = true;
    void action(scope, id, { action: "read" }).then(result => {
      if (!active || current !== generation.current) return;
      if (result.state) setState(result.state);
      if (result.error) setError(result.error);
    }).catch(() => { if (active && current === generation.current) setError("Eligibility refresh failed. Reload before acting."); });
    return () => { active = false; };
  }, [refreshToken, state, busy, action, scope, id]);
  function submit(request: ControlRequest) {
    if (pending.current) return;
    const current = ++generation.current;
    pending.current = true; setBusy(true); setError(""); setNotice("");
    startTransition(async () => {
      try {
        const result = await action(scope, id, request);
        if (current !== generation.current) return;
        if (result.error) setError(result.error);
        else { if (result.state) setState(result.state); if (result.recovery_id) setRecovery(result.recovery_id);
          if (request.action !== "read") { setNotice("Action recorded. Refreshing the trace."); window.dispatchEvent(new window.Event("workflow:mutated")); } }
      } catch { setError("Connection failed. Reload eligibility before retrying this action."); }
      finally { pending.current = false; setBusy(false); }
    });
  }
  return <section className="space-y-4 rounded-lg border p-4" aria-label="Execution controls">
    <h2 className="font-semibold">Recovery and cancellation</h2>
    <p className="text-sm">Recovery pins the original version, input and settings. It reuses safe completed work and logical effect identities, and requests fresh approvals. Changed input requires a new start.</p>
    <button className={button} disabled={busy} onClick={() => submit({ action: "read" })}>{state ? "Reload eligibility" : "Load control eligibility"}</button>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {state && <>
      <p>Current state: {state.status} · revision {state.state_revision}</p>
      {state.source_id && <Link className="underline" href={`/execution-traces/${state.source_id}`}>Original recovery source</Link>}
      {(recovery || state.recovery_id) && <p><Link className="underline" href={`/execution-traces/${recovery || state.recovery_id}`}>Open linked recovery run</Link></p>}
      {!!state.reasons.length && <ul className="list-disc space-y-1 pl-5 text-sm">{state.reasons.map(message => <li key={message} className="break-all">{message}</li>)}</ul>}
      {(state.can_cancel || state.can_recover) && <label className="block text-sm">Reason for action<textarea className="mt-1 block w-full rounded border bg-background p-2" maxLength={1000} value={reason} onChange={event => setReason(event.target.value)} /></label>}
      <div className="flex flex-wrap gap-2">
        <button className={button} disabled={busy || !state.can_cancel || !reason.trim()} onClick={() => submit({ action: "cancel", reason })}>Cancel execution</button>
        <button className={button} disabled={busy || !state.can_recover || !reason.trim()} onClick={() => submit({ action: "recover", reason })}>{state.recovery_id ? "Retrieve existing recovery" : "Create linked recovery"}</button>
      </div>
      <h3 className="font-semibold">Active job recovery</h3>
      {!state.jobs.length && <p className="text-sm">No queued or running jobs. Failed terminal runs use linked recovery.</p>}
      {state.jobs.map(job => <div key={job.id} className="space-y-2 rounded border p-3 text-sm"><p className="break-all">Job {job.id} · {job.status}</p>
        <p>Recovery attempts: {job.recovery_count}/{job.max_recoveries} · due {job.due_at}</p><p>{job.note}</p>
        <button className={button} disabled={busy || !job.can_retry} onClick={() => submit({ action: "retry", job: job.id })}>Recover expired job {job.id}</button></div>)}
      <h3 className="font-semibold">Effects requiring attention</h3>
      {!state.effects.length && <p className="text-sm">No unresolved effects in this recovery lineage.</p>}
      {state.effects.map(effect => <div key={effect.id} className="space-y-2 rounded border p-3"><p className="break-all text-sm">{effect.id} · {effect.status} · {effect.error_code ?? "No recorded error"}</p>
        {effect.needs_resolution && state.can_resolve ? <Resolution effect={effect.id} busy={busy} submit={submit} /> : <p className="text-sm">{effect.needs_resolution ? "An administrator must verify the remote outcome and record reconciliation." : "The retained tool retry policy applies. A recovery cannot reset it."}</p>}
      </div>)}
    </>}
  </section>;
}
function Resolution({ effect, busy, submit }: { effect: string; busy: boolean; submit: (request: ControlRequest) => void }) {
  const [evidence, setEvidence] = useState(""), [result, setResult] = useState("{}"), [error, setError] = useState("");
  function resolve(succeeded: boolean) {
    try { const parsed = succeeded ? JSON.parse(result) : null; setError(""); submit({ action: "resolve", effect, succeeded, result: parsed, evidence }); }
    catch { setError("Enter a valid JSON result matching the tool output contract."); }
  }
  return <div className="space-y-3"><p className="text-sm">Record the verified remote outcome. This preserves the original effect; it does not send the action again.</p>
    <label className="block text-sm">Reconciliation evidence<textarea className="block w-full rounded border bg-background p-2" maxLength={1000} value={evidence} onChange={event => setEvidence(event.target.value)} /></label>
    <label className="block text-sm">Successful result JSON<textarea className="block w-full rounded border bg-background p-2 font-mono" maxLength={64000} value={result} onChange={event => setResult(event.target.value)} /></label>
    {error && <p role="alert">{error}</p>}
    <div className="flex flex-wrap gap-2"><button className={button} disabled={busy || !evidence.trim()} onClick={() => resolve(true)}>Record confirmed success</button>
      <button className={button} disabled={busy || !evidence.trim()} onClick={() => resolve(false)}>Record confirmed failure</button></div>
  </div>;
}
