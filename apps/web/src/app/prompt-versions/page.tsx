import Link from "next/link";
import { CheckCircle2, GitBranch, ShieldCheck, Sparkles } from "lucide-react";
import { LocalDateTime } from "@/components/local-date-time";
import { agentDisplayConfigs, getAgentDisplay } from "@/lib/agent-display";
import { listPromptVersions } from "@/lib/api";
import type { AgentType, PromptVersion } from "@/lib/types";
import { CreatePromptVersionModal } from "./create-prompt-version-modal";

const workflowAccentClasses: Record<string, string> = {
  Sales:
    "border-blue-200 bg-blue-50/70 text-blue-950 dark:border-blue-900/60 dark:bg-blue-950/35 dark:text-blue-200",
  "Customer Feedback":
    "border-blue-200 bg-blue-50/70 text-blue-950 dark:border-blue-900/60 dark:bg-blue-950/35 dark:text-blue-200",
  Incident:
    "border-blue-200 bg-blue-50/70 text-blue-950 dark:border-blue-900/60 dark:bg-blue-950/35 dark:text-blue-200",
  Intake:
    "border-blue-200 bg-blue-50/70 text-blue-950 dark:border-blue-900/60 dark:bg-blue-950/35 dark:text-blue-200",
  "Shared Governance":
    "border-blue-200 bg-blue-50/70 text-blue-950 dark:border-blue-900/60 dark:bg-blue-950/35 dark:text-blue-200",
  Shared: "border-border bg-muted text-foreground",
};

const bluePanelClass =
  "border-blue-200 bg-blue-50/70 dark:border-blue-900/60 dark:bg-blue-950/25";
const blueKickerClass = "text-blue-700 dark:text-blue-300";
const blueTitleClass = "text-blue-950 dark:text-blue-50";
const blueBodyClass = "text-blue-950/75 dark:text-blue-100/75";
const blueNestedPanelClass =
  "border-blue-200 bg-background/80 dark:border-blue-900/60 dark:bg-card/80";

function getWorkflowAccent(workflowLabel: string): string {
  return workflowAccentClasses[workflowLabel] ?? workflowAccentClasses.Shared;
}

function getAgentAccentBar(workflowLabel: string): string {
  return workflowLabel === "Shared" ? "bg-muted-foreground" : "bg-blue-600";
}

function getLatestPrompt(prompts: PromptVersion[]): PromptVersion | null {
  if (prompts.length === 0) return null;
  return [...prompts].sort((a, b) => {
    if (b.version !== a.version) return b.version - a.version;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  })[0];
}

function getPromptPreview(prompt: PromptVersion | null): string {
  if (!prompt) return "No prompt is active for this agent yet.";
  return prompt.template.replace(/\s+/g, " ").trim();
}

function getHistoryScopeLabel(agent: ReturnType<typeof getAgentDisplay>): string {
  return agent.group === "shared" ? "Shared" : agent.workflowLabel;
}

function promptNameLooksMismatched(prompt: PromptVersion | null, agentType: AgentType): boolean {
  if (!prompt) return false;
  const name = prompt.name.toLowerCase();
  const agentNameHints: Partial<Record<AgentType, string[]>> = {
    analyst: ["analyst", "sales"],
    classifier: ["classifier", "feedback"],
    insight: ["insight", "feedback"],
    timeline: ["timeline", "incident"],
    root_cause: ["root cause", "root_cause", "incident"],
    router: ["router"],
    reviewer: ["reviewer", "review"],
    writer: ["writer", "report"],
  };
  const matchedAgentType = Object.entries(agentNameHints).find(([, hints]) =>
    hints.some((hint) => name.includes(hint)),
  )?.[0];
  return matchedAgentType !== undefined && matchedAgentType !== agentType;
}

function getPromptRows(prompts: PromptVersion[]) {
  return agentDisplayConfigs.map((config) => {
    const promptsForAgent = prompts.filter((prompt) => prompt.agent_type === config.agentType);
    const activePrompt = getLatestPrompt(promptsForAgent.filter((prompt) => prompt.is_active));
    return {
      config,
      activePrompt,
      promptCount: promptsForAgent.length,
    };
  });
}

function ActivePromptRow({
  activePrompt,
  config,
  promptCount,
}: {
  activePrompt: PromptVersion | null;
  config: ReturnType<typeof getAgentDisplay>;
  promptCount: number;
}) {
  const hasNamingMismatch = promptNameLooksMismatched(activePrompt, config.agentType);
  const accentBar = getAgentAccentBar(config.workflowLabel);
  const accentClass = getWorkflowAccent(config.workflowLabel);
  return (
    <article className="relative border-t border-border px-4 py-4 transition-colors first:border-t-0 hover:bg-muted/30">
      <div className={`absolute bottom-0 left-0 top-0 w-1 ${accentBar}`} />
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-base font-semibold">{config.displayName}</h4>
              <span className={`rounded-full border px-3 py-1 text-xs ${accentClass}`}>
                {config.workflowLabel}
              </span>
              <span className="rounded-full border border-border bg-background px-3 py-1 text-xs text-muted-foreground">
                {promptCount} version{promptCount === 1 ? "" : "s"}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{config.description}</p>
            <p className="mt-2 text-xs text-muted-foreground">{config.usedBy}</p>
          </div>
          {activePrompt ? (
            <Link
              href={`/prompt-versions/${activePrompt.id}`}
              className="shrink-0 text-sm font-medium underline underline-offset-4"
            >
              View/manage
            </Link>
          ) : null}
        </div>

        <div className="rounded-lg border border-border bg-muted/70 px-3 py-3">
          <p className="text-xs font-medium uppercase text-muted-foreground">Active prompt</p>
          <p className="mt-1 font-medium">
            {activePrompt ? `${activePrompt.name} v${activePrompt.version}` : "Not configured"}
          </p>
          <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">
            {getPromptPreview(activePrompt)}
          </p>
          {hasNamingMismatch ? (
            <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              Review naming: this prompt is assigned to {config.displayName}, but its name appears to
              reference another agent role.
            </p>
          ) : null}
          {activePrompt ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Last updated <LocalDateTime value={activePrompt.created_at} />
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function PromptRows({ rows }: { rows: ReturnType<typeof getPromptRows> }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-background shadow-sm">
      {rows.map((row) => (
        <ActivePromptRow
          key={row.config.agentType}
          activePrompt={row.activePrompt}
          config={row.config}
          promptCount={row.promptCount}
        />
      ))}
    </div>
  );
}

function SharedPromptGroup({ prompts }: { prompts: ReturnType<typeof getPromptRows> }) {
  const rows = prompts.filter((row) =>
    (["router", "reviewer", "writer"] as AgentType[]).includes(row.config.agentType),
  );
  return (
    <section className="mt-8">
      <div className={`flex flex-col gap-1 rounded-lg border p-4 ${bluePanelClass}`}>
        <p className={`text-xs font-semibold uppercase ${blueKickerClass}`}>Shared controls</p>
        <h2 className={`text-xl font-semibold ${blueTitleClass}`}>Shared Governance Prompts</h2>
        <p className={`text-sm ${blueBodyClass}`}>
          These prompts are shared across workflows for routing, factual review, and final report generation.
        </p>
      </div>
      <div className="mt-4">
        <PromptRows rows={rows} />
      </div>
    </section>
  );
}

function WorkflowPromptSection({
  agentTypes,
  prompts,
  title,
  description,
}: {
  agentTypes: AgentType[];
  prompts: ReturnType<typeof getPromptRows>;
  title: string;
  description: string;
}) {
  const rows = prompts.filter((row) => agentTypes.includes(row.config.agentType));
  const accentClass = getWorkflowAccent(title);
  return (
    <section className="mt-5">
      <div className={`mb-3 rounded-lg border p-4 ${accentClass}`}>
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-sm opacity-80">{description}</p>
      </div>
      <PromptRows rows={rows} />
    </section>
  );
}

function WorkflowPromptGroup({ prompts }: { prompts: ReturnType<typeof getPromptRows> }) {
  return (
    <section className="mt-8">
      <div className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase text-muted-foreground">Workflow paths</p>
        <h2 className="text-xl font-semibold">Workflow-Specific Prompts</h2>
        <p className="text-sm text-muted-foreground">
          These prompts belong to one workflow path and should match that workflow&apos;s business output.
        </p>
      </div>
      <WorkflowPromptSection
        title="Sales"
        description="Prompt used by the analyst step for sales report workflows."
        agentTypes={["analyst"]}
        prompts={prompts}
      />
      <WorkflowPromptSection
        title="Customer Feedback"
        description="Prompts used to classify feedback and turn it into product insights."
        agentTypes={["classifier", "insight"]}
        prompts={prompts}
      />
      <WorkflowPromptSection
        title="Incident"
        description="Prompts used to extract incident timelines and root-cause analysis."
        agentTypes={["timeline", "root_cause"]}
        prompts={prompts}
      />
    </section>
  );
}

export default async function PromptVersionsPage() {
  const prompts = await listPromptVersions();
  const promptRows = getPromptRows(prompts);
  const activePromptCount = promptRows.filter((row) => row.activePrompt !== null).length;
  const workflowSpecificCount = promptRows.filter(
    (row) => row.config.group === "workflow" && row.activePrompt !== null,
  ).length;
  const sharedPromptCount = promptRows.filter(
    (row) => row.config.group === "shared" && row.activePrompt !== null,
  ).length;

  return (
    <div>
      <div className={`rounded-xl border p-5 ${bluePanelClass}`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <p className={`text-sm font-semibold uppercase ${blueKickerClass}`}>Prompt Versions</p>
            <h1 className={`mt-2 text-2xl font-bold tracking-tight ${blueTitleClass}`}>
              Prompt Control Center
            </h1>
            <p className={`mt-2 ${blueBodyClass}`}>
              Review the active prompt system by workflow path, shared governance role, and version
              history. Prompt changes affect future agent runs only; completed workflow outputs are
              not mutated.
            </p>
          </div>
          <div className="grid gap-2 text-sm sm:grid-cols-3 lg:min-w-[420px]">
            <div className={`rounded-lg border p-3 ${blueNestedPanelClass}`}>
              <p className={`font-medium ${blueTitleClass}`}>Workflow prompts</p>
              <p className={`mt-1 ${blueBodyClass}`}>Sales, feedback, and incident agents</p>
            </div>
            <div className={`rounded-lg border p-3 ${blueNestedPanelClass}`}>
              <p className={`font-medium ${blueTitleClass}`}>Governance</p>
              <p className={`mt-1 ${blueBodyClass}`}>Router, reviewer, and writer</p>
            </div>
            <div className={`rounded-lg border p-3 ${blueNestedPanelClass}`}>
              <p className={`font-medium ${blueTitleClass}`}>Versioning</p>
              <p className={`mt-1 ${blueBodyClass}`}>Audit history and safe activation</p>
            </div>
          </div>
        </div>
      </div>

      <section className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className={`rounded-lg border p-4 ${bluePanelClass}`}>
          <div className={`flex items-center gap-2 ${blueKickerClass}`}>
            <CheckCircle2 className="h-4 w-4" />
            <p className="text-sm font-medium">Active Prompts</p>
          </div>
          <p className={`mt-2 text-2xl font-semibold ${blueTitleClass}`}>{activePromptCount}</p>
          <p className={`mt-1 text-sm ${blueBodyClass}`}>of {promptRows.length} agent slots</p>
        </div>
        <div className={`rounded-lg border p-4 ${bluePanelClass}`}>
          <div className={`flex items-center gap-2 ${blueKickerClass}`}>
            <GitBranch className="h-4 w-4" />
            <p className="text-sm font-medium">Workflow-Specific</p>
          </div>
          <p className={`mt-2 text-2xl font-semibold ${blueTitleClass}`}>{workflowSpecificCount}</p>
          <p className={`mt-1 text-sm ${blueBodyClass}`}>Sales, Feedback, and Incident agents</p>
        </div>
        <div className={`rounded-lg border p-4 ${bluePanelClass}`}>
          <div className={`flex items-center gap-2 ${blueKickerClass}`}>
            <ShieldCheck className="h-4 w-4" />
            <p className="text-sm font-medium">Shared Governance</p>
          </div>
          <p className={`mt-2 text-2xl font-semibold ${blueTitleClass}`}>{sharedPromptCount}</p>
          <p className={`mt-1 text-sm ${blueBodyClass}`}>Router, Reviewer, and Writer prompts</p>
        </div>
      </section>

      <SharedPromptGroup prompts={promptRows} />
      <WorkflowPromptGroup prompts={promptRows} />

      <section className="mt-8 overflow-hidden rounded-lg border border-border bg-background shadow-sm">
        <div className="flex flex-col gap-4 border-b border-border bg-muted/40 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-blue-700" />
              <h2 className="text-lg font-semibold">Prompt History</h2>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Full version history across all workflow-specific and shared agents.
            </p>
          </div>
          <CreatePromptVersionModal />
        </div>
        <div className="overflow-x-auto">
        <table className="min-w-[1120px] w-full text-left text-sm">
          <thead className="bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="w-[44%] px-4 py-3">Prompt</th>
              <th className="w-[20%] px-4 py-3">Agent</th>
              <th className="w-[12%] px-4 py-3">Used By</th>
              <th className="w-[7%] px-4 py-3">Version</th>
              <th className="w-[8%] px-4 py-3">Status</th>
              <th className="w-[14%] px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {prompts.map((prompt) => {
              const agent = getAgentDisplay(prompt.agent_type);
              const agentAccent = getWorkflowAccent(agent.workflowLabel);
              const historyScopeLabel = getHistoryScopeLabel(agent);
              return (
                <tr key={prompt.id} className="border-t border-border hover:bg-muted/30">
                  <td className="px-4 py-4 align-top">
                    <Link href={`/prompt-versions/${prompt.id}`} className="font-medium hover:underline">
                      {prompt.name}
                    </Link>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                      {prompt.template}
                    </p>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <p className="font-medium">{agent.displayName}</p>
                    <p className="text-xs text-muted-foreground">{agent.description}</p>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <span
                      title={agent.usedBy}
                      className={`inline-flex whitespace-nowrap rounded-full border px-3 py-1 text-xs ${agentAccent}`}
                    >
                      {historyScopeLabel}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 align-top">v{prompt.version}</td>
                  <td className="px-4 py-4 align-top">
                    <span
                      className={
                        prompt.is_active
                          ? "inline-flex whitespace-nowrap rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300"
                          : "inline-flex whitespace-nowrap rounded-full border border-border bg-muted px-3 py-1 text-xs text-muted-foreground"
                      }
                    >
                      {prompt.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 align-top text-xs">
                    <LocalDateTime value={prompt.created_at} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </section>
    </div>
  );
}
