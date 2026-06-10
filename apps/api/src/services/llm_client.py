from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import anthropic

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 2048


@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class TextResponse:
    content: str
    model: str
    usage: LLMUsage


@dataclass
class StructuredResponse:
    data: Any
    model: str
    usage: LLMUsage


class LLMClient:
    """Thin abstraction over the Anthropic Messages API.

    Supports plain text generation and structured JSON output with token
    usage tracking, configurable timeouts, and automatic SDK-level retries.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self._client = anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.default_model = default_model

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> TextResponse:
        """Send a chat completion request and return the text response."""
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system is not None:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        text = next(b.text for b in response.content if b.type == "text")
        return TextResponse(
            content=text,
            model=response.model,
            usage=LLMUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> StructuredResponse:
        """Send a chat completion request and return a JSON-parsed response.

        The schema must be a valid JSON Schema object. The API guarantees the
        response text is valid JSON conforming to the schema.
        """
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "max_tokens": max_tokens,
            "messages": messages,
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": schema,
                }
            },
        }
        if system is not None:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        text = next(b.text for b in response.content if b.type == "text")
        return StructuredResponse(
            data=json.loads(text),
            model=response.model,
            usage=LLMUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )
