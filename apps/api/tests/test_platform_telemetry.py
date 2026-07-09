import io
import logging
from types import SimpleNamespace
from uuid import uuid4

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.observability.platform_telemetry import (
    build_agent_step_event,
    sanitize_telemetry_event,
    submit_platform_telemetry,
)


def _settings(**overrides):
    defaults = {
        "agentops_telemetry_enabled": True,
        "agentops_telemetry_endpoint": "http://localhost:8000/v1/usage/llm-events",
        "agentops_telemetry_api_key_value": "agentops-local-placeholder-key-not-a-secret",
        "agentops_telemetry_timeout_seconds": 2.0,
        "agentops_telemetry_max_metadata_bytes": 2048,
        "agentops_telemetry_redact_content": True,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _event() -> dict:
    return {
        "event_id": "evt_agentops_test",
        "external_request_id": "agentops_workflow_test",
        "source_app": "agentops",
        "operation_type": "agent_step",
        "environment": "local",
        "occurred_at": "2026-07-09T00:00:00Z",
        "status": "succeeded",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_name": "agent_step",
        "prompt_version": "workflow-prompt-v1",
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": "0.000010",
        "currency": "USD",
        "latency_ms": 100,
        "metadata": {
            "workflow_external_id": "workflow_test",
            "agent_step_external_id": "step_test",
            "agent_name": "analyst",
            "agent_type": "analysis",
            "step_order": 1,
            "retry_count": 0,
            "workflow_status": "running",
            "step_status": "completed",
            "response_type": "text",
        },
    }


def test_disabled_mode_does_not_call_sender() -> None:
    def sender(*_args):
        raise AssertionError("sender should not be called")

    assert not submit_platform_telemetry(
        _event(),
        active_settings=_settings(agentops_telemetry_enabled=False),
        sender=sender,
    )


def test_success_posts_sanitized_payload() -> None:
    captured = {}

    def sender(endpoint, payload, api_key, timeout):
        captured.update(
            {
                "endpoint": endpoint,
                "payload": payload,
                "api_key": api_key,
                "timeout": timeout,
            }
        )
        return 202

    assert submit_platform_telemetry(_event(), active_settings=_settings(), sender=sender)
    assert captured["endpoint"] == "http://localhost:8000/v1/usage/llm-events"
    assert captured["api_key"] == "agentops-local-placeholder-key-not-a-secret"
    assert captured["timeout"] == 2.0
    assert captured["payload"]["source_app"] == "agentops"
    assert captured["payload"]["operation_type"] == "agent_step"
    assert captured["payload"]["prompt_name"] == "agent_step"
    assert captured["payload"]["prompt_version"] == "workflow-prompt-v1"
    assert captured["payload"]["output_tokens"] == 5
    assert captured["payload"]["metadata"]["agent_name"] == "analyst"


def test_failure_is_logged_without_secret() -> None:
    secret_key = "agentops-local-placeholder-key-not-a-secret"

    def sender(*_args):
        raise TimeoutError("platform did not respond")

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("agentops.platform_telemetry")
    previous_level = logger.level
    logger.setLevel(logging.WARNING)
    logger.addHandler(handler)
    try:
        assert not submit_platform_telemetry(
            _event(),
            active_settings=_settings(agentops_telemetry_api_key_value=secret_key),
            sender=sender,
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    logs = log_stream.getvalue()
    assert "platform_telemetry_submission_failed" in logs
    assert "timeout" in logs
    assert secret_key not in logs


def test_sanitization_redacts_sensitive_workflow_and_tool_fields() -> None:
    event = {
        **_event(),
        "prompt": "system prompt",
        "generated_output": "raw generated text",
        "workflow_json": {"customer": "raw input"},
        "tool_payload": {"secret": "raw tool result"},
        "provider_payload": {"raw": "provider body"},
        "api_key": "fake-platform-key-not-real",
        "metadata": {
            "workflow_external_id": "workflow_test",
            "agent_step_external_id": "step_test",
            "prompt": "raw prompt",
            "output_json": {"result": "raw output"},
            "tool_result": "raw tool output",
        },
    }

    payload = sanitize_telemetry_event(event, redact_content=True, max_metadata_bytes=2048)

    assert "prompt" not in payload
    assert "generated_output" not in payload
    assert "workflow_json" not in payload
    assert "tool_payload" not in payload
    assert "provider_payload" not in payload
    assert "api_key" not in payload
    assert payload["metadata"] == {
        "workflow_external_id": "workflow_test",
        "agent_step_external_id": "step_test",
    }


def test_sanitization_enforces_metadata_size() -> None:
    payload = sanitize_telemetry_event(
        {
            **_event(),
            "metadata": {
                "workflow_external_id": "workflow_test",
                "agent_step_external_id": "x" * 500,
                "agent_name": "analyst",
            },
        },
        redact_content=True,
        max_metadata_bytes=45,
    )

    assert payload["metadata"] == {"workflow_external_id": "workflow_test"}


def test_build_agent_step_event_omits_raw_workflow_content() -> None:
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
        input_json={"raw": "workflow input"},
        output_json={"generated": "agent output"},
        model="gpt-4.1-mini",
        tokens_input=100,
        tokens_output=50,
        total_tokens=150,
        latency_ms=250,
        cost=0.00012,
        retry_count=0,
    )

    event = build_agent_step_event(step, run=run)

    assert event["source_app"] == "agentops"
    assert event["operation_type"] == "agent_step"
    assert event["status"] == "succeeded"
    assert event["model"] == "gpt-4.1-mini"
    assert event["input_tokens"] == 100
    assert event["output_tokens"] == 50
    assert event["estimated_cost_usd"] == "0.000120"
    assert event["metadata"]["workflow_external_id"] == str(run.id)
    assert event["metadata"]["agent_step_external_id"] == str(step.id)
    assert event["metadata"]["workflow_status"] == "reviewer_running"
    assert "input_json" not in event
    assert "output_json" not in event
