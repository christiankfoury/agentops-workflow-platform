import Link from "next/link";
import { notFound } from "next/navigation";
import { getPromptVersion } from "@/lib/api";
import { activatePromptVersionAction } from "../actions";

export default async function PromptVersionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const prompt = await getPromptVersion(id);
  if (!prompt) notFound();

  return (
    <div>
      <Link href="/prompt-versions" className="text-sm text-muted-foreground hover:text-foreground">
        Back to Prompt Versions
      </Link>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{prompt.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {prompt.agent_type} - v{prompt.version} - {prompt.is_active ? "Active" : "Inactive"}
          </p>
        </div>
        {!prompt.is_active && (
          <form action={activatePromptVersionAction}>
            <input type="hidden" name="prompt_id" value={prompt.id} />
            <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
              Activate Prompt
            </button>
          </form>
        )}
      </div>
      {prompt.notes && (
        <p className="mt-4 rounded-lg border border-border bg-card p-4 text-sm">{prompt.notes}</p>
      )}
      <pre className="mt-6 whitespace-pre-wrap rounded-lg border border-border bg-muted p-4 text-sm">
        {prompt.template}
      </pre>
    </div>
  );
}
