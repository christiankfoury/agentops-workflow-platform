import { CheckCircle2, GitBranch, ShieldCheck, SlidersHorizontal, TriangleAlert } from "lucide-react";
import { getAgentDisplay } from "@/lib/agent-display";
import { listAgentSettings, listPromptVersions } from "@/lib/api";
import type { AgentSetting, AgentType } from "@/lib/types";
import { AgentSettingsForm } from "./settings-form";

const settingGroups: Array<{
  title: string;
  description: string;
  agentTypes: AgentType[];
}> = [
  {
    title: "Sales Workflow",
    description: "Settings for turning sales inputs into structured findings and reports.",
    agentTypes: ["analyst"],
  },
  {
    title: "Customer Feedback Workflow",
    description: "Settings for classifying feedback and generating product insights.",
    agentTypes: ["classifier", "insight"],
  },
  {
    title: "Incident Workflow",
    description: "Settings for timeline extraction and root-cause analysis.",
    agentTypes: ["timeline", "root_cause"],
  },
  {
    title: "Shared Governance",
    description: "Shared routing, review, and writing settings used across workflows.",
    agentTypes: ["router", "reviewer", "writer"],
  },
];

function getSettingsForGroup(settings: AgentSetting[], agentTypes: AgentType[]) {
  const settingsByType = new Map(settings.map((setting) => [setting.agent_type, setting]));
  return agentTypes
    .map((agentType) => settingsByType.get(agentType))
    .filter((setting): setting is AgentSetting => setting !== undefined);
}

function modelConsistencyLabel(settings: AgentSetting[]): string {
  const uniqueModels = new Set(settings.map((setting) => setting.model));
  return uniqueModels.size === 1 ? "Consistent model" : `${uniqueModels.size} models in use`;
}

function riskyRuntimeCount(settings: AgentSetting[]): number {
  return settings.filter((setting) => {
    const timeout = setting.timeout_seconds ?? 0;
    return setting.max_retries > 3 || timeout > 180;
  }).length;
}

export default async function SettingsPage() {
  const [settings, prompts] = await Promise.all([
    listAgentSettings(),
    listPromptVersions(),
  ]);
  const activePromptCount = settings.filter((setting) => setting.active_prompt_name !== null).length;
  const sharedGovernanceConfigured = settings.filter(
    (setting) =>
      (["reviewer", "writer"] as AgentType[]).includes(setting.agent_type) &&
      setting.active_prompt_name !== null,
  ).length;
  const riskyCount = riskyRuntimeCount(settings);

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-5 dark:border-blue-900/60 dark:bg-blue-950/25">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase text-blue-700 dark:text-blue-300">Agent Configuration</p>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-blue-950 dark:text-blue-50">
              Agent Settings
            </h1>
            <p className="mt-2 text-sm leading-6 text-blue-950/75 dark:text-blue-100/75">
              Configure model runtime, prompt selection, retries, and approval policy for future
              agent executions only. Saved changes do not mutate completed workflow outputs.
            </p>
          </div>
          <div className="grid gap-2 text-sm sm:grid-cols-3 lg:min-w-[440px]">
            <div className="rounded-lg border border-blue-200 bg-background/80 p-3 dark:border-blue-900/60 dark:bg-card/80">
              <p className="font-medium text-blue-950 dark:text-blue-100">{settings.length} agents configured</p>
              <p className="mt-1 text-blue-950/70 dark:text-blue-100/65">Across workflow and shared roles</p>
            </div>
            <div className="rounded-lg border border-blue-200 bg-background/80 p-3 dark:border-blue-900/60 dark:bg-card/80">
              <p className="font-medium text-blue-950 dark:text-blue-100">{activePromptCount} active prompts</p>
              <p className="mt-1 text-blue-950/70 dark:text-blue-100/65">Selected or inherited per agent</p>
            </div>
            <div className="rounded-lg border border-blue-200 bg-background/80 p-3 dark:border-blue-900/60 dark:bg-card/80">
              <p className="font-medium text-blue-950 dark:text-blue-100">Shared reviewer/writer</p>
              <p className="mt-1 text-blue-950/70 dark:text-blue-100/65">
                {sharedGovernanceConfigured}/2 configured across 3 workflows
              </p>
            </div>
          </div>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-blue-700">
            <CheckCircle2 className="h-4 w-4" />
            <p className="text-sm font-medium">Prompt coverage</p>
          </div>
          <p className="mt-2 text-2xl font-semibold">{activePromptCount}/{settings.length}</p>
          <p className="mt-1 text-sm text-muted-foreground">Agents with an active prompt</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-blue-700">
            <ShieldCheck className="h-4 w-4" />
            <p className="text-sm font-medium">Governance</p>
          </div>
          <p className="mt-2 text-2xl font-semibold">{sharedGovernanceConfigured}/2</p>
          <p className="mt-1 text-sm text-muted-foreground">Reviewer and writer prompts</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-blue-700">
            <GitBranch className="h-4 w-4" />
            <p className="text-sm font-medium">Model consistency</p>
          </div>
          <p className="mt-2 text-xl font-semibold">{modelConsistencyLabel(settings)}</p>
          <p className="mt-1 text-sm text-muted-foreground">Runtime model spread</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-blue-700">
            {riskyCount > 0 ? (
              <TriangleAlert className="h-4 w-4 text-amber-600" />
            ) : (
              <SlidersHorizontal className="h-4 w-4" />
            )}
            <p className="text-sm font-medium">Runtime risk</p>
          </div>
          <p className="mt-2 text-2xl font-semibold">{riskyCount}</p>
          <p className="mt-1 text-sm text-muted-foreground">High retry or timeout settings</p>
        </div>
      </section>

      <div className="space-y-6">
        {settingGroups.map((group) => {
          const groupSettings = getSettingsForGroup(settings, group.agentTypes);
          return (
            <section key={group.title} className="space-y-3">
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">{group.title}</h2>
                    <p className="mt-1 text-sm text-muted-foreground">{group.description}</p>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {groupSettings.length} agent{groupSettings.length === 1 ? "" : "s"}
                  </p>
                </div>
              </div>
              <div className="grid gap-4">
                {groupSettings.map((setting) => {
                  const agent = getAgentDisplay(setting.agent_type);
                  return (
                    <AgentSettingsForm
                      key={agent.agentType}
                      setting={setting}
                      prompts={prompts}
                    />
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
