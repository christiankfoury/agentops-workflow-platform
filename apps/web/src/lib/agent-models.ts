export const AGENT_MODEL_OPTIONS = [
  "gpt-4.1-mini",
  "gpt-4.1",
  "gpt-4.1-nano",
] as const;

export function isAllowedAgentModel(model: string): boolean {
  return AGENT_MODEL_OPTIONS.includes(model as (typeof AGENT_MODEL_OPTIONS)[number]);
}
