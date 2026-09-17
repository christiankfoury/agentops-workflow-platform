# Optional Production AI Platform telemetry

AgentOps can optionally send safe, best-effort LLM usage telemetry to the
Production AI Platform. Telemetry is disabled by default, and AgentOps workflows
continue normally if the platform is unavailable.

Local placeholder configuration:

```env
AGENTOPS_TELEMETRY_ENABLED=false
AGENTOPS_TELEMETRY_ENDPOINT=http://localhost:8000/v1/usage/llm-events
AGENTOPS_TELEMETRY_API_KEY=agentops-local-placeholder-key-not-a-secret
AGENTOPS_TELEMETRY_TIMEOUT_SECONDS=2
AGENTOPS_TELEMETRY_MAX_METADATA_BYTES=2048
AGENTOPS_TELEMETRY_REDACT_CONTENT=true
```

When AgentOps runs in Docker and Production AI Platform runs on the host, use:

```env
AGENTOPS_TELEMETRY_ENDPOINT=http://host.docker.internal:8000/v1/usage/llm-events
```

The telemetry client only sends operational metadata such as workflow IDs, agent
step IDs, agent name/type, token counts, latency, cost estimate, status, retry
count, and safe error categories. It does not send prompts, generated outputs,
workflow input/output JSON, tool arguments, tool results, provider payloads, API
keys, or OpenAI credentials.

Structured JSON model calls are represented as `agent_step` events with
`response_type=structured_json`; writer and baseline text calls use
`response_type=text`. Workflow summary events are aggregate-only terminal status
events. They intentionally omit token and cost fields so Production AI Platform
does not double-count spend already reported by per-step events.

Send one local smoke event after the Production AI Platform API is running and
seeded with the AgentOps placeholder key:

```powershell
cd apps/api
uv run python ../../scripts/send_platform_telemetry_smoke.py
```

For a browser proof in Production AI Platform, keep the platform dashboard on
`http://localhost:3000` and run AgentOps on non-conflicting ports such as
`API_PORT=8001` and `WEB_PORT=3001`. The safest repeatable demo path is the
platform-owned synthetic sender:

```powershell
cd /path/to/production-ai-platform
uv run python scripts/send_agentops_browser_demo_event.py
```

Then open `http://localhost:3000`, filter **Source App** to `agentops`, and
inspect the resulting `Agent Step` telemetry row. Use a real local AgentOps
workflow only when provider credentials and any OpenAI quota usage are
intentional.
