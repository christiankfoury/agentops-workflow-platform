from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from src.services.llm_client import StructuredResponse


class StructuredOutputRepairError(Exception):
    pass


class StructuredLLMClientLike(Protocol):
    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        pass


def validate_or_repair_structured_response[ModelT: BaseModel](
    *,
    response: StructuredResponse,
    output_model: type[ModelT],
    llm_client: StructuredLLMClientLike,
    messages: list[dict[str, Any]],
    schema: dict[str, Any],
    system: str | None,
    max_tokens: int = 2048,
    request_kwargs: dict[str, Any] | None = None,
) -> tuple[ModelT, StructuredResponse]:
    try:
        return output_model.model_validate(response.data), response
    except ValidationError as first_error:
        repair_kwargs = dict(request_kwargs or {})
        repair_kwargs.setdefault("max_tokens", max_tokens)
        repair_response = llm_client.generate_structured(
            messages=[
                *messages,
                {
                    "role": "user",
                    "content": (
                        "The previous structured output failed schema validation. "
                        "Return a corrected JSON object that strictly matches the schema. "
                        "Do not add keys outside the schema.\n\n"
                        f"Validation error:\n{first_error}\n\n"
                        f"Invalid output:\n{response.data}"
                    ),
                },
            ],
            system=system,
            schema=schema,
            **repair_kwargs,
        )
        try:
            return output_model.model_validate(repair_response.data), repair_response
        except ValidationError as second_error:
            raise StructuredOutputRepairError(
                "Structured output failed validation after repair attempt: "
                f"{second_error}"
            ) from second_error
