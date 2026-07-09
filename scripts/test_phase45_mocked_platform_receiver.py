from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.models.agent_step import AgentStep, AgentStepStatus  # noqa: E402
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType  # noqa: E402
from src.observability.platform_telemetry import (  # noqa: E402
    build_agent_step_event,
    build_workflow_summary_event,
    submit_platform_telemetry,
)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        agentops_telemetry_enabled=True,
        agentops_telemetry_endpoint="http://platform.test/v1/usage/llm-events",
        agentops_telemetry_api_key_value="agentops-local-placeholder-key-not-a-secret",
        agentops_telemetry_timeout_seconds=2.0,
        agentops_telemetry_max_metadata_bytes=2048,
        agentops_telemetry_redact_content=True,
    )


class MockedPlatformReceiverTests(unittest.TestCase):
    def test_agent_step_event_posts_to_mocked_receiver(self) -> None:
        run = WorkflowRun(
            id=uuid4(),
            workflow_type=WorkflowType.sales_report,
            run_mode=RunMode.multi_agent,
            status=WorkflowStatus.reviewer_running,
        )
        step = AgentStep(
            id=uuid4(),
            workflow_run_id=run.id,
            agent_name="Sales Analyst Agent",
            agent_type="analyst",
            step_order=1,
            status=AgentStepStatus.completed,
            output_json={"key_findings": ["safe structured output is not sent"]},
            model="gpt-4.1-mini",
            tokens_input=100,
            tokens_output=50,
            total_tokens=150,
            latency_ms=250,
            cost=0.00012,
            retry_count=0,
        )
        captured: dict[str, object] = {}

        def sender(endpoint, payload, api_key, timeout):
            captured.update(
                endpoint=endpoint,
                payload=payload,
                api_key=api_key,
                timeout=timeout,
            )
            return 202

        event = build_agent_step_event(step, run=run)

        self.assertTrue(
            submit_platform_telemetry(event, active_settings=_settings(), sender=sender)
        )
        self.assertEqual(
            captured["endpoint"], "http://platform.test/v1/usage/llm-events"
        )
        self.assertEqual(
            captured["api_key"], "agentops-local-placeholder-key-not-a-secret"
        )
        self.assertEqual(captured["payload"]["source_app"], "agentops")
        self.assertEqual(captured["payload"]["operation_type"], "agent_step")
        self.assertNotIn("output_json", captured["payload"])
        self.assertNotIn("tool_payload", captured["payload"])

    def test_workflow_summary_event_is_nonbillable_with_mocked_receiver(self) -> None:
        run = WorkflowRun(
            id=uuid4(),
            workflow_type=WorkflowType.sales_report,
            run_mode=RunMode.multi_agent,
            status=WorkflowStatus.completed,
            total_cost=0.5,
            total_tokens=2000,
            latency_ms=9000,
            retry_count=1,
        )
        captured: dict[str, object] = {}

        def sender(_endpoint, payload, _api_key, _timeout):
            captured["payload"] = payload
            return 202

        event = build_workflow_summary_event(run)

        self.assertTrue(
            submit_platform_telemetry(event, active_settings=_settings(), sender=sender)
        )
        payload = captured["payload"]
        self.assertEqual(payload["operation_type"], "workflow_summary")
        self.assertNotIn("estimated_cost_usd", payload)
        self.assertNotIn("input_tokens", payload)
        self.assertNotIn("output_tokens", payload)
        self.assertNotIn("total_tokens", payload)

    def test_mocked_receiver_failure_is_isolated(self) -> None:
        def sender(*_args):
            raise TimeoutError("platform timeout")

        event = {
            "event_id": "evt_agentops_mock_failure",
            "external_request_id": "workflow_mock_failure",
            "source_app": "agentops",
            "operation_type": "agent_step",
            "environment": "local",
            "occurred_at": "2026-07-09T00:00:00Z",
            "status": "failed",
            "provider": "unknown",
            "model": "unknown",
            "error_category": "provider_timeout",
            "metadata": {"workflow_external_id": "workflow_mock_failure"},
        }

        self.assertFalse(
            submit_platform_telemetry(event, active_settings=_settings(), sender=sender)
        )


if __name__ == "__main__":
    unittest.main()
