from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from src.config import settings
from src.models.agent_setting import AgentSetting
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.services.llm_client import DEFAULT_MAX_TOKENS

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 2
ROUTER_MAX_TOKENS = 600


class AgentSettingsError(Exception):
    pass


@dataclass(frozen=True)
class AgentRuntimeConfig:
    prompt: PromptVersion
    model: str
    temperature: float | None
    max_tokens: int
    timeout_seconds: float | None
    max_retries: int
    uses_persisted_settings: bool

    def generation_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
        }
        if self.uses_persisted_settings and self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.uses_persisted_settings and self.timeout_seconds is not None:
            kwargs["timeout"] = self.timeout_seconds
        if self.uses_persisted_settings:
            kwargs["max_retries"] = self.max_retries
        return kwargs


def get_agent_runtime_config(
    db: Session,
    agent_type: AgentType,
    *,
    default_max_tokens: int = DEFAULT_MAX_TOKENS,
) -> AgentRuntimeConfig:
    setting = (
        db.query(AgentSetting).filter(AgentSetting.agent_type == agent_type).first()
    )
    prompt = _resolve_prompt(db, agent_type, setting)
    return AgentRuntimeConfig(
        prompt=prompt,
        model=setting.model if setting is not None else settings.openai_model,
        temperature=setting.temperature if setting is not None else None,
        max_tokens=setting.max_tokens if setting is not None else default_max_tokens,
        timeout_seconds=setting.timeout_seconds if setting is not None else None,
        max_retries=setting.max_retries if setting is not None else DEFAULT_MAX_RETRIES,
        uses_persisted_settings=setting is not None,
    )


def _resolve_prompt(
    db: Session,
    agent_type: AgentType,
    setting: AgentSetting | None,
) -> PromptVersion:
    if setting is not None and setting.active_prompt_version_id is not None:
        prompt = (
            db.query(PromptVersion)
            .filter(PromptVersion.id == setting.active_prompt_version_id)
            .first()
        )
        if prompt is None:
            raise AgentSettingsError("Configured active prompt version not found")
        if prompt.agent_type != agent_type:
            raise AgentSettingsError("Configured active prompt version has wrong agent type")
        return prompt

    prompt = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == agent_type,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .order_by(PromptVersion.version.desc(), PromptVersion.created_at.desc())
        .first()
    )
    if prompt is None:
        raise AgentSettingsError(f"Active {agent_type.value} prompt not found")
    return prompt
