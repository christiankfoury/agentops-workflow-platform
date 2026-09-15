import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from openai import APITimeoutError, AuthenticationError, RateLimitError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.models.workflow_execution import StepAttempt, WorkflowExecution
from src.schemas.workflow_graph import WorkflowGraph
from src.services import durable_queue as queue
from src.services.execution_registry import ExecutorRegistry
from src.services.graph_expressions import ExecutionError
from src.services.graph_interpreter import WorkItem, execute_work
from src.services.llm_client import LLMUsage, StructuredDecodeError, StructuredResponse
from src.services.tenancy import tenant_id
from src.worker import run_worker
from tests.test_graph_interpreter import start
from tests.test_workflow_graph import NUMBER, literal, obj, ref
from tests.test_workflow_transactions_postgres import database as database


class Provider:
    def __init__(self, outputs):
        self.outputs, self.calls, self.closed = list(outputs), [], 0

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        result = self.outputs.pop(0)
        if isinstance(result, Exception):
            raise result
        return StructuredResponse(result, kwargs["model"], LLMUsage(10, 5))

    def close(self):
        self.closed += 1


def prompt(db, agent_type=AgentType.analyst):
    tenant_id(db)
    item = PromptVersion(
        agent_type=agent_type,
        name=str(uuid4()),
        version=1,
        template="Fixture prompt",
        is_active=False,
    )
    db.add(item)
    db.commit()
    return item.id


def graph(prompt_id=None):
    return {
        "entry_node": "generate",
        "output_schema": obj(value=NUMBER),
        "outputs": {"value": ref("value", "generate")},
        "nodes": [
            {
                "id": "generate",
                "type": "llm",
                "config": {"prompt_version_id": str(prompt_id or uuid4()), "model": "gpt-4.1-mini"},
                "input_schema": obj(value=NUMBER),
                "output_schema": obj(value=NUMBER),
                "inputs": {"value": literal(2)},
            }
        ],
    }


def work():
    node = WorkflowGraph.model_validate(graph()).nodes[0]
    return WorkItem(
        uuid4(),
        uuid4(),
        uuid4(),
        0,
        node,
        {"value": 2},
        ({}, {}),
        datetime.now(UTC) + timedelta(seconds=30),
        runtime_config={
            "prompt_version_id": str(node.config.prompt_version_id),
            "prompt_version": 1,
            "system": "Fixture prompt",
            "model": "gpt-4.1-mini",
            "temperature": 0.1,
            "max_tokens": 50,
            "timeout_seconds": 10,
            "max_schema_repairs": 1,
            "pricing": {"input_per_million": 0.4, "output_per_million": 1.6},
        },
    )


@pytest.mark.parametrize(
    "outputs,failed",
    [([{"value": 3}], False), ([{"value": "bad"}, {"value": 4}], False), ([{}, {}], True)],
)
def test_schema_repair_usage_and_sdk_retry_coordination(outputs, failed):
    provider, registry = Provider(outputs), ExecutorRegistry()
    registry.llm_factory = lambda _: provider
    if failed:
        with pytest.raises(ExecutionError, match="bounded repair") as error:
            execute_work(work(), registry)
        metadata = error.value.llm_metadata
    else:
        result = execute_work(work(), registry)
        metadata = result.llm_metadata
        assert result.output == outputs[-1]
    assert metadata["input_tokens"] == 10 * len(outputs)
    assert metadata["total_tokens"] == 15 * len(outputs)
    assert metadata["schema_repairs"] == len(outputs) - 1
    assert metadata["estimated_cost_usd"] == pytest.approx(0.000012 * len(outputs))
    assert metadata["usage_complete"]
    assert all(call["max_retries"] == 0 and 0 < call["timeout"] <= 10 for call in provider.calls)
    assert provider.closed == 1
    assert provider.calls[0]["schema"] == {
        "type": "object",
        "properties": {"value": {"type": "number"}},
        "required": ["value"],
        "additionalProperties": False,
    }


@pytest.mark.parametrize(
    "kind,code",
    [
        ("timeout", "attempt_timeout"),
        ("auth", "provider_rejected"),
        ("rate", "provider_rate_limit"),
    ],
)
def test_provider_errors_are_typed_and_do_not_leak_details(kind, code):
    request = httpx.Request("POST", "https://example.invalid")
    error = (
        APITimeoutError(request=request)
        if kind == "timeout"
        else (AuthenticationError if kind == "auth" else RateLimitError)(
            "secret provider detail",
            response=httpx.Response(401 if kind == "auth" else 429, request=request),
            body=None,
        )
    )
    registry = ExecutorRegistry()
    provider = Provider([error])
    registry.llm_factory = lambda _: provider
    with pytest.raises(ExecutionError) as failure:
        execute_work(work(), registry)
    assert failure.value.code == code and "secret" not in str(failure.value)
    assert not failure.value.llm_metadata["usage_complete"]
    assert len(provider.calls) == 1


def test_llm_abort_closes_client_and_suppresses_returned_output():
    item, registry = work(), ExecutorRegistry()
    provider = Provider([{"value": 2}])
    original = provider.generate_structured

    def cancelled(**kwargs):
        result = original(**kwargs)
        item.control.abort()
        return result

    provider.generate_structured = cancelled
    registry.llm_factory = lambda _: provider
    with pytest.raises(ExecutionError) as error:
        execute_work(item, registry)
    assert error.value.code == "execution_aborted" and provider.closed >= 1


@pytest.mark.parametrize("outputs,expected", [([{"value": 4}], "completed"), ([{}, {}], "failed")])
def test_durable_llm_attempt_persists_usage_for_success_and_failed_repair(
    database, outputs, expected
):
    with Session(database) as db:
        identity = start(db, graph(prompt(db)), {}).id
    provider, registry = Provider(outputs), ExecutorRegistry()
    registry.llm_factory = lambda _: provider
    assert queue.process_claim(database, queue.claim_jobs(database, "llm")[0], registry)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == expected
        assert run.runtime_config["generate"]["max_retries"] == 0
        attempt = db.scalar(select(StepAttempt))
        assert attempt.llm_metadata["total_tokens"] == len(outputs) * 15
        assert attempt.status == expected


def test_malformed_json_repair_keeps_usage_from_first_response():
    provider = Provider(
        [
            StructuredDecodeError(
                json.JSONDecodeError("bad JSON", "bad", 0),
                StructuredResponse(None, "gpt-4.1-mini", LLMUsage(20, 8)),
            ),
            {"value": 2},
        ]
    )
    registry = ExecutorRegistry()
    registry.llm_factory = lambda _: provider
    result = execute_work(work(), registry)
    assert result.llm_metadata["total_tokens"] == 43
    assert result.llm_metadata["schema_repairs"] == 1


def test_elapsed_timeout_preserves_returned_usage(monkeypatch):
    ticks = iter([0, 0, 11, 11])
    monkeypatch.setattr("src.services.llm_execution.monotonic", lambda: next(ticks))
    registry = ExecutorRegistry()
    registry.llm_factory = lambda _: Provider([{"value": 2}])
    with pytest.raises(ExecutionError) as error:
        execute_work(work(), registry)
    assert error.value.code == "attempt_timeout"
    assert error.value.llm_metadata["total_tokens"] == 15


@pytest.mark.parametrize(
    "reason,code", [("length", "provider_incomplete"), ("content_filter", "provider_refused")]
)
def test_provider_refusal_and_truncation_preserve_usage_without_repair(reason, code):
    registry = ExecutorRegistry()
    provider = Provider([])
    provider.generate_structured = lambda **_: StructuredResponse(
        {}, "gpt-4.1-mini", LLMUsage(10, 5), finish_reason=reason
    )
    registry.llm_factory = lambda _: provider
    with pytest.raises(ExecutionError) as error:
        execute_work(work(), registry)
    assert error.value.code == code
    assert error.value.llm_metadata["provider_requests"] == 1
    assert error.value.llm_metadata["total_tokens"] == 15
