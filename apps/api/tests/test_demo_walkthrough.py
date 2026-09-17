"""Safety boundaries and approved-input behavior of the optional demo helper."""

import json
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from examples import demo_fixture as demo
from src.models.identity import Organization
from tests.test_workflow_transactions_postgres import database as database


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
        url=SimpleNamespace(host=host, database=database, query={}),
    ))
    with pytest.raises(ValueError, match="Requires development"):
        demo.guard()


@pytest.mark.parametrize("query", ["host=remote.invalid", "dbname=agentops"])
def test_fixture_refuses_query_overrides_of_approved_target(monkeypatch, query):
    monkeypatch.setattr(demo.settings, "environment", "development")
    monkeypatch.setattr(demo.settings, "identity_enabled", False)
    target = make_url("postgresql://fixture@127.0.0.1/phase104_demo_safe?" + query)
    assert target.host == "127.0.0.1" and target.database == "phase104_demo_safe"
    monkeypatch.setattr(demo, "engine", SimpleNamespace(url=target))
    with pytest.raises(ValueError, match="URL query parameters"):
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


def test_fixture_refuses_other_organizations_before_seed_or_worker(
    database, monkeypatch, tmp_path,
):
    # The shared fixture owns a fresh isolated PostgreSQL schema. URL guard cases
    # are covered above; bypass only that guard to inspect real tenant behavior.
    monkeypatch.setattr(demo, "engine", database)
    monkeypatch.setattr(demo, "guard", lambda: None)
    monkeypatch.setattr(demo, "run_worker", lambda *a, **k: pytest.fail("Worker must not start"))
    with Session(database) as db:
        db.add(Organization(id=uuid.uuid4(), name="Unrelated fixture tenant"))
        db.commit()
    manifest = tmp_path / "manifest.json"
    with pytest.raises(ValueError, match="single local organization"):
        demo.seed(manifest)
    with pytest.raises(ValueError, match="single local organization"):
        demo.drain({"database": database.url.database})
    assert not manifest.exists()
