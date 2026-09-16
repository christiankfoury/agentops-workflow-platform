import Link from "next/link";
import { builderRequest } from "@/lib/api";
import type { DraftDefinition } from "@/lib/workflow-builder";

export default async function DefinitionsPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const params = await searchParams;
  const page = /^\d{1,6}$/.test(params.page ?? "") ? Math.max(0, Number(params.page)) : 0;
  let definitions: DraftDefinition[], actions: string[];
  try {
    const result = await Promise.all([
      builderRequest<DraftDefinition[]>(`/workflow-definitions?offset=${page * 50}&limit=50`),
      builderRequest<{ actions: string[] }>("/access/permissions"),
    ]);
    definitions = result[0]; actions = result[1].actions;
  } catch { return <section role="alert"><h1 className="text-2xl font-bold">Workflow builder</h1><p>Workflow definitions are unavailable. Check your organization access and retry.</p><Link href="/workflow-definitions" className="underline">Retry</Link></section>; }
  return <section className="space-y-6">
    <header className="flex flex-wrap justify-between gap-4"><div><h1 className="text-2xl font-bold">Workflow definitions</h1><p className="text-muted-foreground">Build reusable workflows from typed steps. Draft edits do not change published versions.</p></div>
      {actions.includes("workflow.draft") && <Link href="/workflow-definitions/new" className="h-fit rounded bg-primary px-4 py-2 text-primary-foreground">New definition</Link>}</header>
    {!definitions.length && <p className="rounded border p-6">No workflow definitions on this page. Create a draft to begin with a deterministic example.</p>}
    <ul className="grid gap-4 md:grid-cols-2">{definitions.map(d => <li key={d.id} className="min-w-0 rounded-lg border bg-card p-5"><Link href={`/workflow-definitions/${encodeURIComponent(d.id)}`} className="break-words text-lg font-semibold underline">{d.name}</Link><p className="mt-2 break-words text-sm text-muted-foreground">{d.description || "No description"}</p><p className="mt-3 text-xs">Draft {d.draft_revision} · {d.archived ? "Archived" : d.published_version_id ? "Has published version" : "Unpublished"}</p></li>)}</ul>
    <nav aria-label="Definition pages" className="flex gap-4">{page > 0 && <Link className="underline" href={`/workflow-definitions?page=${page - 1}`}>Previous</Link>}{definitions.length === 50 && <Link className="underline" href={`/workflow-definitions?page=${page + 1}`}>Next</Link>}</nav>
  </section>;
}
