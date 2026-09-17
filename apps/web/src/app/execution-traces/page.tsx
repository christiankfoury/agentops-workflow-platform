import Link from "next/link";
import { LivePage } from "@/components/live-page";
import { builderRequest } from "@/lib/api";
import type { TracePage } from "@/lib/execution-traces";

export default async function TraceList({ searchParams }: { searchParams: Promise<{ offset?: string }> }) {
  const query = await searchParams;
  const offset = /^\d{1,6}$/.test(query.offset ?? "") ? Number(query.offset) : 0;
  let page: TracePage;
  try { page = await builderRequest<TracePage>(`/execution-traces?offset=${offset}&limit=25`); }
  catch { return <p role="alert">Graph runs are unavailable. Check your organization and reload.</p>; }
  return <div className="space-y-5"><h1 className="text-2xl font-bold">Graph runs</h1><p>Inspect the immutable graph, logical steps, attempts and durable trace for each run.</p><Link className="underline" href="/workflow-runs">Business and historical runs</Link>
    <LivePage kind="executions" />{!page.items.length && <p>No graph runs on this page.</p>}
    <ul className="space-y-3">{page.items.map(row => <li className="rounded border p-4" key={row.id}><Link className="break-all underline" href={`/execution-traces/${row.id}`}>{row.id}</Link><p>{String(row.status)} · {String(row.created_at)}</p></li>)}</ul>
    <nav className="flex gap-4" aria-label="Run pages">{offset > 0 && <Link className="underline" href={`/execution-traces?offset=${Math.max(0, offset - 25)}`}>Previous</Link>}{page.next_offset != null && <Link className="underline" href={`/execution-traces?offset=${page.next_offset}`}>Next</Link>}</nav></div>;
}
