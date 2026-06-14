import Link from "next/link";
import { LocalDateTime } from "@/components/local-date-time";
import { agentDisplayConfigs, getAgentDisplay } from "@/lib/agent-display";
import { listPromptVersions } from "@/lib/api";
import type { AgentType, PromptVersion } from "@/lib/types";
import { CreatePromptVersionModal } from "./create-prompt-version-modal";

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
  return (
    <article className="border-t border-border px-4 py-4 first:border-t-0">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-base font-semibold">{config.displayName}</h4>
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

        <div className="rounded-md bg-muted px-3 py-3">
          <p className="text-xs uppercase text-muted-foreground">Active prompt</p>
          <p className="mt-1 font-medium">
            {activePrompt ? `${activePrompt.name} v${activePrompt.version}` : "Not configured"}
          </p>
          <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">
            {getPromptPreview(activePrompt)}
          </p>
          {hasNamingMismatch ? (
            <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
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
    <div className="overflow-hidden rounded-lg border border-border">
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
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold">Shared Governance Prompts</h2>
        <p className="text-sm text-muted-foreground">
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
  return (
    <section className="mt-5">
      <div className="mb-3">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <PromptRows rows={rows} />
    </section>
  );
}

function WorkflowPromptGroup({ prompts }: { prompts: ReturnType<typeof getPromptRows> }) {
  return (
    <section className="mt-8">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold">Workflow-Specific Prompts</h2>
        <p className="text-sm text-muted-foreground">
          These prompts belong to one workflow path and should match that workflow's business output.
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
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium uppercase text-muted-foreground">Prompt Versions</p>
        <h1 className="text-2xl font-bold tracking-tight">Prompt Control Center</h1>
        <p className="max-w-3xl text-muted-foreground">
          Review the prompts currently used by each workflow agent. Prompt changes affect future
          agent runs only; completed workflow outputs are not mutated.
        </p>
      </div>

      <section className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-border p-4">
          <p className="text-sm text-muted-foreground">Active Prompts</p>
          <p className="mt-2 text-2xl font-semibold">{activePromptCount}</p>
          <p className="mt-1 text-sm text-muted-foreground">of {promptRows.length} agent slots</p>
        </div>
        <div className="rounded-lg border border-border p-4">
          <p className="text-sm text-muted-foreground">Workflow-Specific</p>
          <p className="mt-2 text-2xl font-semibold">{workflowSpecificCount}</p>
          <p className="mt-1 text-sm text-muted-foreground">Sales, Feedback, and Incident agents</p>
        </div>
        <div className="rounded-lg border border-border p-4">
          <p className="text-sm text-muted-foreground">Shared Governance</p>
          <p className="mt-2 text-2xl font-semibold">{sharedPromptCount}</p>
          <p className="mt-1 text-sm text-muted-foreground">Router, Reviewer, and Writer prompts</p>
        </div>
      </section>

      <SharedPromptGroup prompts={promptRows} />
      <WorkflowPromptGroup prompts={promptRows} />

      <section className="mt-8 overflow-hidden rounded-lg border border-border">
        <div className="flex flex-col gap-4 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Prompt History</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Full version history across all workflow-specific and shared agents.
            </p>
          </div>
          <CreatePromptVersionModal />
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Prompt</th>
              <th className="px-4 py-3">Agent</th>
              <th className="px-4 py-3">Used By</th>
              <th className="px-4 py-3">Version</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {prompts.map((prompt) => {
              const agent = getAgentDisplay(prompt.agent_type);
              return (
                <tr key={prompt.id} className="border-t border-border">
                  <td className="px-4 py-3">
                    <Link href={`/prompt-versions/${prompt.id}`} className="font-medium hover:underline">
                      {prompt.name}
                    </Link>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                      {prompt.template}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="font-medium">{agent.displayName}</p>
                    <p className="text-xs text-muted-foreground">{agent.description}</p>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{agent.usedBy}</td>
                  <td className="px-4 py-3">v{prompt.version}</td>
                  <td className="px-4 py-3">{prompt.is_active ? "Active" : "Inactive"}</td>
                  <td className="px-4 py-3">
                    <LocalDateTime value={prompt.created_at} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}
