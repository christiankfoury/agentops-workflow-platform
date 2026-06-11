import json
from unittest.mock import MagicMock, patch

import pytest

from src.services.llm_client import (
    DEFAULT_MODEL,
    LLMClient,
    LLMUsage,
    StructuredResponse,
    TextResponse,
)


def _mock_response(
    text: str,
    model: str = DEFAULT_MODEL,
    input_tokens: int = 10,
    output_tokens: int = 20,
) -> MagicMock:
    response = MagicMock()
    response.model = model
    response.usage.prompt_tokens = input_tokens
    response.usage.completion_tokens = output_tokens
    response.choices[0].message.content = text
    return response


@pytest.fixture
def mock_openai():
    with patch("src.services.llm_client.OpenAI") as MockClass:
        instance = MagicMock()
        MockClass.return_value = instance
        yield instance


class TestLLMClientInit:
    def test_default_model(self):
        with patch("src.services.llm_client.OpenAI"):
            c = LLMClient(api_key="k")
        assert c.default_model == DEFAULT_MODEL

    def test_custom_model(self):
        with patch("src.services.llm_client.OpenAI"):
            c = LLMClient(api_key="k", default_model="gpt-4.1")
        assert c.default_model == "gpt-4.1"

    def test_passes_api_key_and_settings(self):
        with patch("src.services.llm_client.OpenAI") as MockClass:
            LLMClient(api_key="sk-test", timeout=30.0, max_retries=5)
        MockClass.assert_called_once_with(api_key="sk-test", timeout=30.0, max_retries=5)


class TestGenerateText:
    def test_returns_text_response(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response("Hello there")

        result = LLMClient(api_key="k").generate_text([{"role": "user", "content": "Hi"}])

        assert isinstance(result, TextResponse)
        assert result.content == "Hello there"
        assert result.model == DEFAULT_MODEL

    def test_usage_tracking(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response(
            "Hi", input_tokens=5, output_tokens=15
        )

        result = LLMClient(api_key="k").generate_text([{"role": "user", "content": "Hi"}])

        assert isinstance(result.usage, LLMUsage)
        assert result.usage.input_tokens == 5
        assert result.usage.output_tokens == 15
        assert result.usage.total_tokens == 20

    def test_includes_system_when_provided(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response("ok")

        LLMClient(api_key="k").generate_text(
            [{"role": "user", "content": "Hi"}], system="Be helpful"
        )

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["messages"][0] == {"role": "system", "content": "Be helpful"}

    def test_omits_system_when_not_provided(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response("ok")

        LLMClient(api_key="k").generate_text([{"role": "user", "content": "Hi"}])

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["messages"] == [{"role": "user", "content": "Hi"}]

    def test_model_override(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response("ok")

        LLMClient(api_key="k").generate_text(
            [{"role": "user", "content": "Hi"}], model="gpt-4.1"
        )

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["model"] == "gpt-4.1"

    def test_uses_default_model_when_no_override(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response("ok")

        LLMClient(api_key="k").generate_text([{"role": "user", "content": "Hi"}])

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["model"] == DEFAULT_MODEL

    def test_max_tokens_passed_through(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response("ok")

        LLMClient(api_key="k").generate_text(
            [{"role": "user", "content": "Hi"}], max_tokens=512
        )

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["max_completion_tokens"] == 512

    def test_temperature_passed_through(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response("ok")

        LLMClient(api_key="k").generate_text(
            [{"role": "user", "content": "Hi"}], temperature=0.2
        )

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["temperature"] == 0.2

    def test_timeout_and_retries_use_request_options(self, mock_openai):
        request_client = MagicMock()
        request_client.chat.completions.create.return_value = _mock_response("ok")
        mock_openai.with_options.return_value = request_client

        LLMClient(api_key="k").generate_text(
            [{"role": "user", "content": "Hi"}], timeout=12.0, max_retries=4
        )

        mock_openai.with_options.assert_called_once_with(timeout=12.0, max_retries=4)
        request_client.chat.completions.create.assert_called_once()


class TestGenerateStructured:
    SCHEMA = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }

    def test_returns_structured_response(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response('{"name": "Alice"}')

        result = LLMClient(api_key="k").generate_structured(
            [{"role": "user", "content": "Extract name: Alice"}], schema=self.SCHEMA
        )

        assert isinstance(result, StructuredResponse)
        assert result.data == {"name": "Alice"}

    def test_parses_json_from_text_block(self, mock_openai):
        payload = {"name": "Bob", "score": 42}
        mock_openai.chat.completions.create.return_value = _mock_response(json.dumps(payload))

        result = LLMClient(api_key="k").generate_structured(
            [{"role": "user", "content": "Extract"}], schema=self.SCHEMA
        )

        assert result.data == payload

    def test_passes_response_format_with_schema(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response('{"name": "Bob"}')

        LLMClient(api_key="k").generate_structured(
            [{"role": "user", "content": "Extract"}], schema=self.SCHEMA
        )

        kwargs = mock_openai.chat.completions.create.call_args[1]
        fmt = kwargs["response_format"]
        assert fmt["type"] == "json_schema"
        assert fmt["json_schema"]["schema"] == self.SCHEMA

    def test_usage_tracking(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response(
            '{"name": "Bob"}', input_tokens=8, output_tokens=12
        )

        result = LLMClient(api_key="k").generate_structured(
            [{"role": "user", "content": "Extract"}], schema=self.SCHEMA
        )

        assert result.usage.input_tokens == 8
        assert result.usage.output_tokens == 12
        assert result.usage.total_tokens == 20

    def test_includes_system_when_provided(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response('{"name": "Bob"}')

        LLMClient(api_key="k").generate_structured(
            [{"role": "user", "content": "Extract"}],
            schema=self.SCHEMA,
            system="Extract JSON only",
        )

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["messages"][0] == {"role": "system", "content": "Extract JSON only"}

    def test_model_override(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response('{"name": "Bob"}')

        LLMClient(api_key="k").generate_structured(
            [{"role": "user", "content": "Extract"}],
            schema=self.SCHEMA,
            model="gpt-4.1",
        )

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["model"] == "gpt-4.1"

    def test_structured_temperature_passed_through(self, mock_openai):
        mock_openai.chat.completions.create.return_value = _mock_response('{"name": "Bob"}')

        LLMClient(api_key="k").generate_structured(
            [{"role": "user", "content": "Extract"}],
            schema=self.SCHEMA,
            temperature=0.1,
        )

        kwargs = mock_openai.chat.completions.create.call_args[1]
        assert kwargs["temperature"] == 0.1


class TestLLMUsage:
    def test_total_tokens(self):
        usage = LLMUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150
