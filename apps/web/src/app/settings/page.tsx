import { listAgentSettings, listPromptVersions } from "@/lib/api";
import { AgentSettingsForm } from "./settings-form";

export default async function SettingsPage() {
  const [settings, prompts] = await Promise.all([
    listAgentSettings(),
    listPromptVersions(),
  ]);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-card p-5">
        <p className="text-xs font-medium uppercase text-muted-foreground">
          Runtime controls
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight">Agent Settings</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          Tune model, retry, timeout, threshold, and active prompt settings for
          future workflow runs. Saved changes do not mutate completed outputs.
        </p>
      </div>

      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="hidden gap-3 border-b border-border bg-muted/70 px-4 py-3 text-xs font-semibold uppercase text-muted-foreground lg:grid lg:grid-cols-[1fr_1.2fr_repeat(5,minmax(0,0.8fr))_auto]">
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
