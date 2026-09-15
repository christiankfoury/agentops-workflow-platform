"""Resolve LLM settings once at acceptance; workers read only immutable snapshots."""

from dataclasses import asdict

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from src.models.agent_setting import AgentSetting
from src.models.prompt_version import PromptVersion
from src.schemas.workflow_graph import LLMConfig
from src.services.agent_settings import get_agent_runtime_config
from src.services.cost_tracking import MODEL_PRICING


def snapshot_config(db, version, graph):
    # A single read and shared row locks keep repeated agent settings consistent
    # across all nodes while a concurrent settings publication waits for acceptance.
    locked_settings = (
        db.scalars(
            select(AgentSetting).order_by(AgentSetting.agent_type).with_for_update(read=True)
        ).all()
        if any(node.type == "llm" and node.config.use_agent_settings for node in graph.nodes)
        else []
    )
    snapshots = {}
    settings_snapshot = {item.agent_type: item for item in locked_settings}
    for node in graph.nodes:
        if node.type != "llm":
            continue
        config = node.config
        prompt = version.prompt_snapshots.get(str(config.prompt_version_id))
        if prompt is None:
            raise HTTPException(409, "Pinned prompt snapshot is unavailable")
        model, temperature, max_tokens = config.model, config.temperature, config.max_tokens
        timeout = node.timeout_seconds
        threshold = 0.85
        if config.use_agent_settings:
            pinned = db.scalar(
                select(PromptVersion).where(PromptVersion.id == config.prompt_version_id)
            )
            if pinned is None:
                raise HTTPException(409, "Referenced prompt is unavailable")
            resolved = get_agent_runtime_config(
                db, pinned.agent_type, prompt_override=pinned, settings_snapshot=settings_snapshot
            )
            model, temperature, max_tokens = (
                resolved.model,
                resolved.temperature,
                resolved.max_tokens,
            )
            timeout = min(timeout, resolved.timeout_seconds or timeout)
            threshold = resolved.reviewer_approval_threshold
        pricing = MODEL_PRICING.get(model)
        try:
            LLMConfig.model_validate(
                {
                    **config.model_dump(),
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )
        except ValidationError as error:
            raise HTTPException(
                422, "Resolved LLM settings exceed the graph runtime bounds"
            ) from error
        snapshots[node.id] = {
            "prompt_version_id": str(config.prompt_version_id),
            "prompt_version": prompt["version"],
            "system": prompt["template"],
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout_seconds": timeout,
            "max_retries": 0,
            "max_schema_repairs": config.max_schema_repairs,
            "reviewer_approval_threshold": threshold,
            "pricing": asdict(pricing) if pricing else None,
        }
    del locked_settings
    return snapshots
