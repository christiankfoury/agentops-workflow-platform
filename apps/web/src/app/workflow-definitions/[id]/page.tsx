import Link from "next/link";
import { builderRequest, listPromptVersions } from "@/lib/api";
import { WorkflowBuilder } from "@/components/workflow-builder/editor";
import type { CatalogItem, DraftDefinition } from "@/lib/workflow-builder";
import { saveDraft } from "../actions";

export default async function DefinitionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let definition: DraftDefinition | undefined, access: { organization_id: string | null; actions: string[] };
  try {
    [definition, access] = await Promise.all([
      id === "new" ? Promise.resolve(undefined) : builderRequest<DraftDefinition>(`/workflow-definitions/${encodeURIComponent(id)}`),
      builderRequest<{ organization_id: string | null; actions: string[] }>("/access/permissions"),
    ]);
  } catch { return <section role="alert"><h1 className="text-2xl font-bold">Workflow unavailable</h1><p>The workflow may be missing or outside your current organization. Your access may also have changed.</p><Link href="/workflow-definitions" className="underline">Return to definitions</Link></section>; }
  const [tools, prompts] = await Promise.allSettled([builderRequest<CatalogItem[]>("/tools"), listPromptVersions()]);
  return <div className="space-y-5"><Link className="text-sm underline" href="/workflow-definitions">All definitions</Link>
    <WorkflowBuilder key={`${access.organization_id}:${id}`} initial={definition} scope={access.organization_id} canEdit={access.actions.includes("workflow.draft")} save={saveDraft}
      tools={tools.status === "fulfilled" ? tools.value : []}
      prompts={prompts.status === "fulfilled" ? prompts.value.map(p => ({ id: p.id, name: `${p.name} · v${p.version}` })) : []}
      catalogError={tools.status === "rejected" || prompts.status === "rejected"} />
  </div>;
}
