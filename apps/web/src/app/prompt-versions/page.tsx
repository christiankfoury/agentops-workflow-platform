import Link from "next/link";
import { listPromptVersions } from "@/lib/api";
import { PromptVersionForm } from "./form";

export default async function PromptVersionsPage() {
  const prompts = await listPromptVersions();

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Prompt Versions</h1>
      <PromptVersionForm />
      <section className="mt-8 overflow-hidden rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Prompt</th>
              <th className="px-4 py-3">Agent</th>
              <th className="px-4 py-3">Version</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {prompts.map((prompt) => (
              <tr key={prompt.id} className="border-t border-border">
                <td className="px-4 py-3">
                  <Link href={`/prompt-versions/${prompt.id}`} className="font-medium hover:underline">
                    {prompt.name}
                  </Link>
                  <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                    {prompt.template}
                  </p>
                </td>
                <td className="px-4 py-3">{prompt.agent_type}</td>
                <td className="px-4 py-3">v{prompt.version}</td>
                <td className="px-4 py-3">{prompt.is_active ? "Active" : "Inactive"}</td>
                <td className="px-4 py-3">{new Date(prompt.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
