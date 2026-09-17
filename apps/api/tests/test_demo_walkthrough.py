"""Safety boundaries and approved-input behavior of the optional demo helper."""

import json
from types import SimpleNamespace

import pytest

from examples import demo_fixture as demo


@pytest.mark.parametrize(
    "environment,identity,host,database",
    [
        ("production", False, "127.0.0.1", "phase104_demo_test"),
        ("development", True, "127.0.0.1", "phase104_demo_test"),
        ("development", False, "db.example.com", "phase104_demo_test"),
        ("development", False, "127.0.0.1", "agentops"),
    ],
)
def test_fixture_refuses_non_demo_targets_before_database_access(
    monkeypatch, environment, identity, host, database,
):
    monkeypatch.setattr(demo.settings, "environment", environment)
    monkeypatch.setattr(demo.settings, "identity_enabled", identity)
    # No connection method exists: rejection must happen before any DB access.
    monkeypatch.setattr(demo, "engine", SimpleNamespace(
        url=SimpleNamespace(host=host, database=database),
    ))
    with pytest.raises(ValueError, match="Requires development"):
        demo.guard()


def test_fixture_writer_uses_approved_edit_and_rejects_other_schemas():
    provider = demo.SyntheticProvider()
    response = provider.generate_structured(
        schema={"properties": {"final_output": {"type": "string"}}},
        model="synthetic-fixture",
        messages=[{"content": json.dumps({"input": {
            "approved_analysis": {"recommendations": ["Human-edited action"]},
        }})}],
    )
    assert "Human-edited action" in response.data["final_output"]
    assert "Review renewal coverage." not in response.data["final_output"]
    assert response.usage.input_tokens == response.usage.output_tokens == 0
    with pytest.raises(ValueError, match="no provider fallback"):
        provider.generate_structured(schema={"properties": {"unknown": {}}})
