import Link from "next/link";
import { builderRequest } from "@/lib/api";
import { triggerPath, type Trigger, type TriggerKind } from "@/lib/workflow-release";

export default async function TriggersPage({ searchParams }: { searchParams: Promise<{ kind?: string; page?: string }> }) {
  const query = await searchParams;
  const kind: TriggerKind = query.kind === "schedule" ? "schedule" : "webhook";
  const page = /^\d{1,6}$/.test(query.page ?? "") ? Number(query.page) : 0;
  let items: Trigger[], access: { actions: string[] };
  try {
    [items, access] = await Promise.all([builderRequest<Trigger[]>(`${triggerPath(kind)}?offset=${page * 50}&limit=50`), builderRequest<{ actions: string[] }>("/access/permissions")]);
  } catch { return <section role="alert"><h1 className="text-2xl font-bold">Triggers unavailable</h1><p>Check your current organization and reload to retry.</p></section>; }
  return <div className="space-y-5"><h1 className="text-2xl font-bold">Workflow triggers</h1>
      <nav className="flex flex-wrap gap-4" aria-label="Trigger types"><Link href="/workflow-triggers?kind=webhook" className="underline" aria-current={kind === "webhook" ? "page" : undefined}>Webhooks</Link><Link href="/workflow-triggers?kind=schedule" className="underline" aria-current={kind === "schedule" ? "page" : undefined}>Schedules</Link></nav>
      {access.actions.includes("trigger.manage") && <Link className="inline-block rounded bg-primary px-3 py-2 text-primary-foreground" href={`/workflow-triggers/${kind}/new`}>New {kind === "webhook" ? "webhook" : "schedule"}</Link>}
      {!items.length && <p>No {kind === "webhook" ? "webhooks" : "schedules"} on this page.</p>}
      <ul className="grid gap-4 md:grid-cols-2">{items.map(item => <li key={item.id} className="min-w-0 rounded-lg border p-4"><Link className="break-words font-semibold underline" href={`/workflow-triggers/${kind}/${encodeURIComponent(item.id)}`}>{item.name}</Link><p className="text-sm">{item.enabled ? "Enabled" : "Paused"} · revision {item.revision} · {item.version_policy}</p><p className="break-all text-xs">Definition {item.definition_id}</p></li>)}</ul>
      <nav className="flex gap-4" aria-label="Trigger pages">{page > 0 && <Link className="underline" href={`/workflow-triggers?kind=${kind}&page=${page - 1}`}>Previous</Link>}{items.length === 50 && <Link className="underline" href={`/workflow-triggers?kind=${kind}&page=${page + 1}`}>Next</Link>}</nav>
    </div>;
}
