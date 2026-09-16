"""Bounded provider execution outside database locks, with complete returned usage."""

import json
from contextlib import suppress
from datetime import UTC, datetime
from time import monotonic

from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import ValidationError

from src.config import settings
from src.schemas.workflow_graph import WorkflowGraph
from src.services.graph_expressions import ExecutionError
from src.services.graph_validation import validate_data
from src.services.llm_client import LLMClient, StructuredDecodeError
from src.services.structured_output_guardrails import repair_messages


def client_factory(config):
    return LLMClient(
        api_key=settings.openai_api_key_value,
        default_model=config["model"],
        timeout=config["timeout_seconds"],
        max_retries=0,
    )


def provider_schema(schema):
    result = {"type": schema.type}
    if "object" in schema.types:
        result.update(
            properties={key: provider_schema(value) for key, value in schema.properties.items()},
            required=schema.required,
            additionalProperties=False,
        )
    if "array" in schema.types:
        result["items"] = provider_schema(schema.items)
    return result


def execute_llm(work, factory, output_validators=None):
    from src.services.execution_registry import NodeResult

    config = work.runtime_config
    if not config:
        raise ExecutionError("configuration_missing", "Pinned LLM configuration is unavailable")
    started = monotonic()
    budget = config["timeout_seconds"]
    if work.deadline_at:
        budget = min(budget, (work.deadline_at - datetime.now(UTC)).total_seconds())
    metadata = {
        "prompt_version_id": config["prompt_version_id"],
        "prompt_version": config["prompt_version"],
        "model": config["model"],
        "sdk_max_retries": 0,
        "requests": [],
        "schema_repairs": 0,
        "provider_requests": 0,
    }
    messages = [
        {
            "role": "user",
            "content": json.dumps(
                {
                    "input": work.inputs,
                    "revision_context": work.revision_context,
                },
                ensure_ascii=False,
            ),
        }
    ]
    client, unregister = None, lambda: None
    try:
        work.control.raise_if_aborted()
        if budget <= 0:
            raise ExecutionError("attempt_timeout", "LLM attempt deadline expired")
        client = factory(config)
        unregister = work.control.on_abort(client.close)
        for repair in range(config["max_schema_repairs"] + 1):
            work.control.raise_if_aborted()
            remaining = budget - (monotonic() - started)
            if remaining <= 0:
                raise ExecutionError("attempt_timeout", "LLM attempt deadline expired")
            decode_error = None
            metadata["provider_requests"] += 1
            metadata["schema_repairs"] = repair
            try:
                response = client.generate_structured(
                    messages=messages,
                    schema=provider_schema(work.node.output_schema),
                    system=config["system"],
                    model=config["model"],
                    max_tokens=config["max_tokens"],
                    temperature=config["temperature"],
                    timeout=remaining,
                    max_retries=0,
                )
            except StructuredDecodeError as error:
                response, decode_error = error.response, error
            if any(
                type(value) is not int or not 0 <= value < 2**63
                for value in (response.usage.input_tokens, response.usage.output_tokens)
            ):
                raise ExecutionError("provider_response_invalid", "Provider returned invalid usage")
            metadata["requests"].append(
                {
                    "model": response.model,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "schema_repair": repair,
                }
            )
            metadata["schema_repairs"] = repair
            if response.refusal or response.finish_reason == "content_filter":
                raise ExecutionError("provider_refused", "Provider refused this request")
            if response.finish_reason == "length":
                raise ExecutionError(
                    "provider_incomplete", "Provider output reached its token limit"
                )
            work.control.raise_if_aborted()
            if monotonic() - started >= budget:
                raise ExecutionError("attempt_timeout", "LLM attempt deadline expired")
            try:
                if decode_error:
                    raise ValueError("Provider returned invalid JSON")
                validate_data(response.data, work.node.output_schema)
                if work.node.config.output_validator:
                    validator = (output_validators or {}).get(work.node.config.output_validator)
                    if validator is None:
                        raise ExecutionError(
                            "configuration_missing", "Output validator is unavailable"
                        )
                    response.data = validator(response.data)
                    validate_data(response.data, work.node.output_schema)
                if work.revision_context.get("quality_reviewer"):
                    from src.schemas.execution_approval import ApprovalReview

                    ApprovalReview.model_validate(response.data)
                WorkflowGraph.payload_bounds({"output": response.data})
            except (ValidationError, ValueError) as error:
                if repair == config["max_schema_repairs"]:
                    raise ExecutionError(
                        "output_invalid", "Structured output failed bounded repair"
                    ) from error
                messages = repair_messages(messages, response.data, error)
                continue
            return NodeResult(
                response.data, llm_metadata=finish_metadata(metadata, config, started)
            )
    except Exception as error:
        if isinstance(error, ExecutionError):
            failure = error
        elif isinstance(error, APITimeoutError):
            failure = ExecutionError("attempt_timeout", "Provider request timed out")
        elif isinstance(error, APIConnectionError):
            failure = ExecutionError("provider_connection", "Provider connection failed")
        elif isinstance(error, APIStatusError):
            code = (
                "provider_rate_limit"
                if error.status_code == 429
                else "provider_unavailable"
                if error.status_code >= 500 or error.status_code in {408, 409}
                else "provider_rejected"
            )
            failure = ExecutionError(code, "Provider rejected the request")
        else:
            failure = ExecutionError("provider_failed", "Provider execution failed")
        failure.llm_metadata = finish_metadata(metadata, config, started)
        raise failure from error
    finally:
        unregister()
        if client:
            with suppress(Exception):
                client.close()


def finish_metadata(metadata, config, started):
    metadata["input_tokens"] = sum(row["input_tokens"] for row in metadata["requests"])
    metadata["output_tokens"] = sum(row["output_tokens"] for row in metadata["requests"])
    metadata["total_tokens"] = metadata["input_tokens"] + metadata["output_tokens"]
    metadata["latency_ms"] = round((monotonic() - started) * 1000)
    metadata["usage_complete"] = len(metadata["requests"]) == metadata["provider_requests"]
    pricing = config["pricing"]
    metadata["estimated_cost_usd"] = (
        (
            metadata["input_tokens"] * pricing["input_per_million"]
            + metadata["output_tokens"] * pricing["output_per_million"]
        )
        / 1_000_000
        if pricing
        else None
    )
    metadata["pricing"] = pricing
    return metadata
