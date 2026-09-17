import Link from "next/link";
import { builderRequest } from "@/lib/api";
import { LivePage } from "@/components/live-page";
import type { TracePage } from "@/lib/execution-traces";

type Summary = {
  observed_at: string; jobs: Record<string, number>; runs: Record<string, number>; attempts: Record<string, number>;
  workers: Record<string, number>; claims: number; lease_recoveries: number; abandoned_attempts: number;
  linked_recoveries: number; waiting_steps: number; oldest_ready_seconds: number; completed_in_window: number;
  window_seconds: number; queue_wait: { samples: number; sum_seconds: number; max_seconds: number };
};
const filters = ["all", "queued", "running", "retrying", "failed", "dead_letter", "stale", "completed", "cancelled"];
export default async function Operations({ searchParams }: { searchParams: Promise<{ kind?: string; offset?: string }> }) {
  const query = await searchParams, kind = filters.includes(query.kind ?? "") ? query.kind! : "all";
  const offset = /^\d{1,6}$/.test(query.offset ?? "") ? Number(query.offset) : 0;
  let data: Summary, page: TracePage;
  try { [data, page] = await Promise.all([builderRequest<Summary>("/operations"), builderRequest<TracePage>(`/operations/jobs?kind=${kind}&offset=${offset}&limit=25`)]); }
  catch { return <div><LivePage kind="operations" /><p role="alert">Operations data is unavailable. Check your connection and organization.</p></div>; }
  const metrics = {
    "Queued jobs": data.jobs.queued ?? 0, "Running jobs": data.jobs.running ?? 0, "Retrying jobs": data.jobs.retrying,
    "Failed jobs": data.jobs.failed ?? 0, "Dead-letter jobs": data.jobs.dead_letter, "Stale leases": data.jobs.stale,
    "Waiting steps": data.waiting_steps, "Observed available workers": data.workers.running ?? 0,
    "Claims recorded": data.claims, "Lease recoveries": data.lease_recoveries, "Abandoned attempts": data.abandoned_attempts,
    "Linked recoveries": data.linked_recoveries,
  };
  return <div className="space-y-5"><h1 className="text-2xl font-bold">Worker operations</h1><LivePage kind="operations" />
    <p className="text-sm">Current organization only · observed {data.observed_at}. Retrying, dead-letter and stale counts are subsets of job states.</p>
    <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">{Object.entries(metrics).map(([label, value]) => <div className="rounded border p-3" key={label}><p className="text-sm">{label}</p><strong className="text-2xl">{value}</strong></div>)}</div>
    <section className="space-y-2 rounded border p-4"><h2 className="font-semibold">Queue and throughput</h2>
      <p>Oldest ready job: {data.oldest_ready_seconds.toFixed(1)} seconds. Future backoff and scheduled waits are excluded.</p>
      <p>Measured claim wait: {data.queue_wait.samples ? (data.queue_wait.sum_seconds / data.queue_wait.samples).toFixed(2) : "Unavailable"} seconds average · {data.queue_wait.max_seconds.toFixed(2)} maximum · {data.queue_wait.samples} samples.</p>
      <p>{data.completed_in_window} completed workflows in the last {data.window_seconds / 60} minutes · {(data.completed_in_window / data.window_seconds).toFixed(4)} workflows/second.</p>
      <p className="text-sm">Worker availability covers recent heartbeats from workers associated with your jobs. Zero can mean no observed worker; it does not prove the shared fleet is down. Fleet capacity and identities are restricted to infrastructure operators.</p>
    </section>
    <section className="rounded border p-4"><h2 className="font-semibold">Persisted attempts</h2><p className="text-sm">{Object.entries(data.attempts).map(([state, count]) => `${state}: ${count}`).join(" · ") || "No attempts yet."} Claims and attempts are different: a claim can register a wait without executing a node.</p><Link href="/costs" className="underline">Cost and usage</Link> · <Link href="/execution-traces" className="underline">Run traces and events</Link></section>
    <nav aria-label="Job filters" className="flex flex-wrap gap-2">{filters.map(value => <Link key={value} aria-current={kind === value ? "page" : undefined} className="rounded border px-3 py-2 text-sm aria-[current=page]:bg-muted" href={`/operations?kind=${value}`}>{value.replaceAll("_", " ")}</Link>)}</nav>
    <p className="text-sm">Dead-letter means a failed job exhausted its attempt or recovery budget. Open its run to review eligibility and recovery controls.</p>
    {!page.items.length && <p>No jobs match this view.</p>}
    <ul className="space-y-3">{page.items.map(job => <li className="space-y-2 rounded border p-4 text-sm" key={job.id}><p className="break-all">Job {job.id} · {String(job.status)}</p><Link className="break-all underline" href={`/execution-traces/${job.execution_id}`}>Inspect run {String(job.execution_id)}</Link><p>Node {String(job.node_id ?? "sequential checkpoint")} · iteration {String(job.iteration)} · recoveries {String(job.recovery_count)}</p><p>Due: {String(job.due_at)} · lease expires: {String(job.lease_expires_at ?? "No active lease")}</p></li>)}</ul>
    <nav className="flex gap-4" aria-label="Job pages">{offset > 0 && <Link className="underline" href={`/operations?kind=${kind}&offset=${Math.max(0, offset - 25)}`}>Previous</Link>}{page.next_offset != null && <Link className="underline" href={`/operations?kind=${kind}&offset=${page.next_offset}`}>Next</Link>}</nav>
  </div>;
}
