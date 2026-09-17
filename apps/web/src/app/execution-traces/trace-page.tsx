import Link from "next/link";
import { LiveRefresh } from "@/components/live-refresh";
import { builderRequest } from "@/lib/api";
import type { TraceHead, TracePage } from "@/lib/execution-traces";
import { TraceDebugger } from "@/components/execution-traces/debugger";
import { ExecutionControls } from "@/components/execution-traces/controls";
import { controlExecution } from "./control-actions";
import { readTrace } from "./actions";

export async function TracePageView({ id, legacy = false }: { id: string; legacy?: boolean }) {
  const path = `/execution-traces/${legacy ? "legacy/" : ""}${encodeURIComponent(id)}`;
  let head: TraceHead, access: { organization_id: string | null };
  let initial: TracePage = { items: [], offset: 0, next_offset: null }, initialError = false;
  try { [head, access] = await Promise.all([builderRequest<TraceHead>(path), builderRequest<{ organization_id: string | null }>("/access/permissions")]); }
  catch { return <p role="alert">This run trace is unavailable. It may be missing or outside your current organization.</p>; }
  if (legacy && head.execution_id) return <div className="space-y-4"><h1 className="text-2xl font-bold">This run uses the generic engine</h1><p>Its historical agent records are compatibility projections. Open the canonical trace to avoid counting usage twice.</p><Link className="underline" href={`/execution-traces/${head.execution_id}`}>Open canonical run debugger</Link></div>;
  try { initial = await builderRequest<TracePage>(`${path}/${legacy ? "steps" : "records/steps"}?limit=25`); } catch { initialError = true; }
  return <div className="space-y-5"><Link href="/execution-traces" className="underline">All graph runs</Link>
    <LiveRefresh scope={access.organization_id} kind={legacy ? "run" : "execution"} id={id} terminal={["completed", "failed", "cancelled", "skipped"].includes(String(head.run.status))} />
    {!legacy && <ExecutionControls key={`controls:${access.organization_id}:${id}`} id={id} scope={access.organization_id} action={controlExecution} refreshToken={head.run.state_revision} />}
    <TraceDebugger key={`${access.organization_id}:${id}`} head={head} initial={initial} initialError={initialError} scope={access.organization_id} read={readTrace} /></div>;
}
