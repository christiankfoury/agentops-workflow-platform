from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.observability.platform_telemetry import submit_platform_telemetry  # noqa: E402


def _event() -> dict:
    return {
        "event_id": f"evt_agentops_smoke_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "external_request_id": "agentops_workflow_smoke",
        "source_app": "agentops",
        "operation_type": "agent_step",
        "environment": os.getenv("ENVIRONMENT", "local"),
        "occurred_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_name": "agent_step_smoke",
        "prompt_version": "workflow-prompt-v1",
        "input_tokens": 100,
        "output_tokens": 25,
        "total_tokens": 125,
        "estimated_cost_usd": "0.000080",
        "currency": "USD",
        "pricing_status": "estimated",
        "latency_ms": 95,
        "metadata": {
            "workflow_external_id": "workflow_run_smoke",
            "agent_step_external_id": "agent_step_smoke",
            "agent_name": "analyst",
            "agent_type": "analysis",
            "step_order": 1,
            "retry_count": 0,
            "workflow_status": "running",
            "step_status": "completed",
            "response_type": "text",
        },
    }


def _settings() -> SimpleNamespace:
    api_key = os.getenv(
        "AGENTOPS_TELEMETRY_API_KEY",
        "agentops-local-placeholder-key-not-a-secret",
    )
    return SimpleNamespace(
        agentops_telemetry_enabled=True,
        agentops_telemetry_endpoint=os.getenv(
            "AGENTOPS_TELEMETRY_ENDPOINT",
            "http://localhost:8000/v1/usage/llm-events",
        ),
        agentops_telemetry_api_key_value=api_key,
        agentops_telemetry_timeout_seconds=float(
            os.getenv("AGENTOPS_TELEMETRY_TIMEOUT_SECONDS", "2")
        ),
        agentops_telemetry_max_metadata_bytes=int(
            os.getenv("AGENTOPS_TELEMETRY_MAX_METADATA_BYTES", "2048")
        ),
        agentops_telemetry_redact_content=os.getenv(
            "AGENTOPS_TELEMETRY_REDACT_CONTENT", "true"
        ).lower()
        not in {"0", "false", "no"},
    )


def main() -> int:
    accepted = submit_platform_telemetry(_event(), active_settings=_settings())
    if not accepted:
        print("AgentOps telemetry smoke event was not accepted")
        return 1
    print("AgentOps telemetry smoke event accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
