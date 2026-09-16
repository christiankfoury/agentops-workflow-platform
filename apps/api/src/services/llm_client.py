from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

DEFAULT_MODEL = "gpt-4.1-mini"
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
    refusal: str | None = None
    finish_reason: str | None = None


@dataclass
class ToolResponse:
    content: str | None
    calls: list[dict]
    model: str
    usage: LLMUsage
    refusal: str | None = None
    finish_reason: str | None = None


class StructuredDecodeError(json.JSONDecodeError):
    """Retain returned usage even when the provider's JSON cannot be decoded."""

    def __init__(self, error, response):
        super().__init__(error.msg, error.doc, error.pos)
        self.response = response


class LLMClient:
    """Thin abstraction over OpenAI chat completions.

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
        self._client = OpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.default_model = default_model

    def close(self):
        self._client.close()

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> TextResponse:
        """Send a chat completion request and return the text response."""
        request_messages = list(messages)
        if system is not None:
            request_messages.insert(0, {"role": "system", "content": system})
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "max_completion_tokens": max_tokens,
            "messages": request_messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        client = self._client
        if timeout is not None or max_retries is not None:
            client = self._client.with_options(timeout=timeout, max_retries=max_retries)
        response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        return TextResponse(
            content=text,
            model=response.model,
            usage=LLMUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            ),
        )

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> StructuredResponse:
        """Send a chat completion request and return a JSON-parsed response.

        Callers validate the returned object against their schema and handle refusals,
        truncated or malformed output explicitly.
        """
        request_messages = list(messages)
        if system is not None:
            request_messages.insert(0, {"role": "system", "content": system})
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "max_completion_tokens": max_tokens,
            "messages": request_messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "schema": schema,
                },
            },
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        client = self._client
        if timeout is not None or max_retries is not None:
            client = self._client.with_options(timeout=timeout, max_retries=max_retries)
        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        text = choice.message.content or "{}"
        result = StructuredResponse(
            data=None,
            model=response.model,
            usage=LLMUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            ),
            refusal=choice.message.refusal if isinstance(choice.message.refusal, str) else None,
            finish_reason=choice.finish_reason if isinstance(choice.finish_reason, str) else None,
        )
        try:
            result.data = json.loads(text)
        except json.JSONDecodeError as error:
            raise StructuredDecodeError(error, result) from error
        return result

    def generate_tools(
        self,
        *,
        messages,
        tools,
        schema,
        system,
        model,
        max_tokens,
        temperature=None,
        timeout=None,
        max_retries=0,
    ):
        kwargs = {
            "model": model,
            "messages": [{"role": "system", "content": system}, *messages],
            "tools": tools,
            "max_completion_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "schema": schema,
                },
            },
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        response = self._client.with_options(
            timeout=timeout, max_retries=max_retries
        ).chat.completions.create(**kwargs)
        choice = response.choices[0]
        return ToolResponse(
            choice.message.content,
            [
                {
                    "id": call.id,
                    "type": call.type,
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in (choice.message.tool_calls or [])
            ],
            response.model,
            LLMUsage(response.usage.prompt_tokens, response.usage.completion_tokens),
            choice.message.refusal,
            choice.finish_reason,
        )
