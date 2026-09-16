import Link from "next/link";
import { builderRequest } from "@/lib/api";
import type { DraftDefinition } from "@/lib/workflow-builder";
import type { Version } from "@/lib/workflow-release";
import { WorkflowRelease } from "@/components/workflow-builder/release";
import { runPlatformAction } from "../../platform-actions";

export default async function ReleasePage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ page?: string }> }) {
  const { id } = await params, query = await searchParams;
  const page = /^\d{1,6}$/.test(query.page ?? "") ? Number(query.page) : 0;
  const path = `/workflow-definitions/${encodeURIComponent(id)}`;
  let definition: DraftDefinition, versions: Version[], access: { organization_id: string | null; actions: string[] };
  try {
    [definition, versions, access] = await Promise.all([
      builderRequest<DraftDefinition>(path), builderRequest<Version[]>(`${path}/versions?offset=${page * 50}&limit=50`),
      builderRequest<{ organization_id: string | null; actions: string[] }>("/access/permissions"),
    ]);
  } catch { return <section role="alert"><h1 className="text-2xl font-bold">Versions unavailable</h1><p>Check your organization access and retry loading this page.</p><Link className="underline" href="/workflow-definitions">All definitions</Link></section>; }
  return <div className="space-y-5"><Link className="underline" href={path}>Edit draft</Link>
      <WorkflowRelease key={`${access.organization_id}:${id}:${page}`} initial={definition} initialVersions={versions} scope={access.organization_id} permissions={access.actions} action={runPlatformAction} />
      <nav className="flex gap-4" aria-label="Version pages">{page > 0 && <Link href={`${path}/release?page=${page - 1}`} className="underline">Previous versions</Link>}{versions.length === 50 && <Link href={`${path}/release?page=${page + 1}`} className="underline">Older versions</Link>}</nav>
    </div>;
}
