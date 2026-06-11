import { listAgentSettings, listPromptVersions } from "@/lib/api";
import { AgentSettingsForm } from "./settings-form";

export default async function SettingsPage() {
  const [settings, prompts] = await Promise.all([
    listAgentSettings(),
    listPromptVersions(),
  ]);

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Agent Settings</h1>
      <section className="mt-6 overflow-hidden rounded-lg border border-border">
        <div className="grid gap-3 bg-muted px-4 py-3 text-xs font-medium uppercase text-muted-foreground lg:grid-cols-[1fr_1.2fr_repeat(5,minmax(0,0.8fr))_auto]">
          <span>Agent</span>
          <span>Model</span>
          <span>Temp</span>
          <span>Max Tokens</span>
          <span>Timeout</span>
          <span>Retries</span>
          <span>Reviewer</span>
          <span>Human</span>
        </div>
        {settings.map((setting) => (
          <AgentSettingsForm
            key={setting.agent_type}
            setting={setting}
            prompts={prompts}
          />
        ))}
      </section>
    </div>
  );
}
