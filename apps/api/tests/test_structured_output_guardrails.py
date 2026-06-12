from typing import Any

import pytest

from src.services.llm_client import LLMUsage, StructuredResponse
from src.services.sales_analyst import SalesAnalysisOutput
from src.services.structured_output_guardrails import (
    StructuredOutputRepairError,
    validate_or_repair_structured_response,
)

VALID_SALES_ANALYSIS = {
    "key_findings": ["Revenue increased 12%."],
    "risks": ["Enterprise churn increased."],
    "opportunities": ["North America growth can be expanded."],
    "recommendations": ["Prioritize enterprise retention."],
    "supporting_evidence": ["Revenue increased 12% from $4.2M to $4.7M."],
}


class FakeRepairClient:
    def __init__(self, repair_data: dict[str, Any]) -> None:
        self.repair_data = repair_data
        self.calls: list[dict[str, Any]] = []

    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
        timeout: float | None = None,
    ) -> StructuredResponse:
        self.calls.append(
            {
                "messages": messages,
                "schema": schema,
                "system": system,
                "model": model,
                "max_tokens": max_tokens,
                "timeout": timeout,
            }
        )
        return StructuredResponse(
            data=self.repair_data,
            model=model or "repair-model",
            usage=LLMUsage(input_tokens=20, output_tokens=10),
        )


def make_response(data: dict[str, Any]) -> StructuredResponse:
    return StructuredResponse(
        data=data,
        model="test-model",
        usage=LLMUsage(input_tokens=12, output_tokens=8),
    )


def test_validate_or_repair_structured_response_accepts_valid_output_without_repair():
    client = FakeRepairClient(repair_data={})

    output, response = validate_or_repair_structured_response(
        response=make_response(VALID_SALES_ANALYSIS),
        output_model=SalesAnalysisOutput,
        llm_client=client,
        messages=[{"role": "user", "content": "Analyze sales report."}],
        schema={"type": "object"},
        system="system",
    )

    assert output.key_findings == ["Revenue increased 12%."]
    assert response.model == "test-model"
    assert client.calls == []


def test_validate_or_repair_structured_response_repairs_invalid_output():
    client = FakeRepairClient(repair_data=VALID_SALES_ANALYSIS)

    output, response = validate_or_repair_structured_response(
        response=make_response({"key_findings": []}),
        output_model=SalesAnalysisOutput,
        llm_client=client,
        messages=[{"role": "user", "content": "Analyze sales report."}],
        schema={"type": "object"},
        system="system",
        max_tokens=300,
        request_kwargs={"model": "gpt-test", "timeout": 5.0},
    )

    assert output.recommendations == ["Prioritize enterprise retention."]
    assert response.model == "gpt-test"
    assert len(client.calls) == 1
    repair_call = client.calls[0]
    assert repair_call["max_tokens"] == 300
    assert repair_call["timeout"] == 5.0
    assert repair_call["messages"][-1]["role"] == "user"
    assert "failed schema validation" in repair_call["messages"][-1]["content"]
    assert "Invalid output" in repair_call["messages"][-1]["content"]


def test_validate_or_repair_structured_response_raises_after_failed_repair():
    client = FakeRepairClient(repair_data={"key_findings": []})

    with pytest.raises(StructuredOutputRepairError) as excinfo:
        validate_or_repair_structured_response(
            response=make_response({"key_findings": []}),
            output_model=SalesAnalysisOutput,
            llm_client=client,
            messages=[{"role": "user", "content": "Analyze sales report."}],
            schema={"type": "object"},
            system=None,
        )

    assert "Structured output failed validation after repair attempt" in str(excinfo.value)
    assert len(client.calls) == 1
