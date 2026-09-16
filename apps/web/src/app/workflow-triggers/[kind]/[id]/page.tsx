import Link from "next/link";
import { builderRequest } from "@/lib/api";
import type { ObjectValue } from "@/lib/workflow-builder";
import { triggerPath, type Trigger } from "@/lib/workflow-release";
import { TriggerEditor } from "@/components/workflow-builder/trigger";
import { runPlatformAction } from "@/app/workflow-definitions/platform-actions";

export default async function TriggerPage({ params, searchParams }: { params: Promise<{ kind: string; id: string }>; searchParams: Promise<{ definition?: string }> }) {
  const { kind, id } = await params, query = await searchParams;
  if (kind !== "webhook" && kind !== "schedule") return <p role="alert">Unknown trigger type.</p>;
  let record: Trigger | undefined, access: { organization_id: string | null; actions: string[] };
  let history: ObjectValue[] = [], historyError = false;
  try {
    const path = `${triggerPath(kind)}/${encodeURIComponent(id)}`;
    [record, access] = await Promise.all([id === "new" ? Promise.resolve(undefined) : builderRequest<Trigger>(path), builderRequest<{ organization_id: string | null; actions: string[] }>("/access/permissions")]);
    if (record) try { history = await builderRequest<ObjectValue[]>(`${path}/${kind === "webhook" ? "deliveries" : "fires"}?limit=50`); } catch { historyError = true; }
  } catch { return <section role="alert"><h1 className="text-2xl font-bold">Trigger unavailable</h1><p>It may be missing or outside your current organization.</p><Link className="underline" href="/workflow-triggers">All triggers</Link></section>; }
  return <div className="space-y-5"><Link className="underline" href={`/workflow-triggers?kind=${kind}`}>All {kind === "webhook" ? "webhooks" : "schedules"}</Link>
      <TriggerEditor key={`${access.organization_id}:${kind}:${id}`} kind={kind} initial={record} definition={query.definition} scope={access.organization_id} canManage={access.actions.includes("trigger.manage")} action={runPlatformAction} initialHistory={history} historyError={historyError} />
    </div>;
}
