import {
  Activity,
  CheckCircle2,
  Database,
  GitCompare,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { LocalDateTime } from "@/components/local-date-time";
import { getAgentDisplay } from "@/lib/agent-display";
import { getPromptVersion, listPromptVersions } from "@/lib/api";
import type { PromptVersion } from "@/lib/types";
import { activatePromptVersionAction } from "../actions";

function DetailItem({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="rounded-md border border-border bg-background/80 px-3 py-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 rounded-md bg-sky-50 p-2 text-sky-700">{icon}</span>
        <div>
          <p className="text-xs uppercase text-muted-foreground">{label}</p>
          <div className="mt-1 text-sm font-medium">{value}</div>
        </div>
      </div>
    </div>
  );
}

function getActivationMessage(prompt: PromptVersion, currentActivePrompt: PromptVersion | null, agentName: string) {
  if (prompt.is_active) return "This prompt is currently active for future runs.";
  if (currentActivePrompt) {
    return `Activating this will replace ${currentActivePrompt.name} v${currentActivePrompt.version} for future ${agentName} runs.`;
  }
  return `Activating this will make it the first active prompt for future ${agentName} runs.`;
}

function statusBadgeClass(isActive: boolean): string {
  return isActive
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : "border-amber-200 bg-amber-50 text-amber-800";
}

function activationPanelClass(isActive: boolean): string {
  return isActive
    ? "border-emerald-200 bg-emerald-50/70"
    : "border-amber-200 bg-amber-50/80";
}

export default async function PromptVersionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [prompt, prompts] = await Promise.all([
    getPromptVersion(id),
    listPromptVersions(),
  ]);
  if (!prompt) notFound();
  const agent = getAgentDisplay(prompt.agent_type);
  const currentActivePrompt =
    prompts.find(
      (candidate) => candidate.agent_type === prompt.agent_type && candidate.is_active,
    ) ?? null;
  const activationMessage = getActivationMessage(prompt, currentActivePrompt, agent.displayName);

  return (
    <div>
      <Link href="/prompt-versions" className="text-sm text-muted-foreground hover:text-foreground">
        Back to Prompt Versions
      </Link>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{prompt.name}</h1>
            <span className={`rounded-full border px-3 py-1 text-xs font-medium ${statusBadgeClass(prompt.is_active)}`}>
              {prompt.is_active ? "Active" : "Inactive"}
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-medium text-sky-800">
              {agent.displayName}
            </span>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
              {agent.usedBy}
            </span>
            <span className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-medium text-violet-800">
              v{prompt.version}
            </span>
          </div>
        </div>
      </div>

      <section className="mt-6 rounded-lg border border-sky-200 bg-sky-50/50 p-4">
        <p className="text-xs font-semibold uppercase text-sky-800">Impact</p>
        <h2 className="mt-1 text-lg font-semibold">Operational Impact</h2>
        <p className="mt-1 text-sm text-sky-950/70">
          This describes where the prompt is used and what changes when it is activated.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          <DetailItem icon={<Activity className="h-4 w-4" />} label="Agent" value={agent.displayName} />
          <DetailItem icon={<GitCompare className="h-4 w-4" />} label="Workflow usage" value={agent.usedBy} />
          <DetailItem icon={<CheckCircle2 className="h-4 w-4" />} label="Applies to" value="Future agent runs only" />
          <DetailItem icon={<Database className="h-4 w-4" />} label="Completed outputs" value="Existing workflow outputs are not changed" />
          <DetailItem icon={<ShieldCheck className="h-4 w-4" />} label="Version" value={`v${prompt.version}`} />
          <DetailItem icon={<Activity className="h-4 w-4" />} label="Created" value={<LocalDateTime value={prompt.created_at} />} />
        </div>
      </section>

      <section className={`mt-6 rounded-lg border p-4 ${activationPanelClass(prompt.is_active)}`}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className={`text-xs font-semibold uppercase ${prompt.is_active ? "text-emerald-800" : "text-amber-800"}`}>
              Change Control
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">Active Prompt Status</h2>
            <p className={`mt-1 text-sm ${prompt.is_active ? "text-emerald-950/75" : "text-amber-950/75"}`}>
              {activationMessage}
            </p>
          </div>
          {!prompt.is_active ? (
            <form action={activatePromptVersionAction}>
              <input type="hidden" name="prompt_id" value={prompt.id} />
              <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
                Activate Prompt
              </button>
            </form>
          ) : null}
        </div>
      </section>

      <section className="mt-6 rounded-lg border border-border p-4">
        <p className="text-xs font-semibold uppercase text-muted-foreground">Template</p>
        <h2 className="mt-1 text-lg font-semibold">Prompt Template</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Template text sent to the agent when this prompt version is used.
        </p>
        <pre className="mt-4 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-muted p-5 text-sm leading-7 text-foreground">
          {prompt.template}
        </pre>
      </section>

      <section className="mt-6 rounded-lg border border-violet-100 bg-violet-50/40 p-4">
        <p className="text-xs font-semibold uppercase text-violet-800">Notes</p>
        <h2 className="mt-1 text-lg font-semibold">Notes</h2>
        <p className="mt-3 rounded-md border border-violet-100 bg-background/80 px-3 py-3 text-sm text-muted-foreground">
          {prompt.notes && prompt.notes.trim().length > 0 ? prompt.notes : "No notes provided."}
        </p>
      </section>
    </div>
  );
}
