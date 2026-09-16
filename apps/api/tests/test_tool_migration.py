import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from tests.generic_migration_fixtures import legacy_business_rows
from tests.test_tool_effects import effects, invoke, setup


def test_tool_migration_preserves_history_and_enforces_contract_retention(monkeypatch):
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration86_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f085_durable_evaluations")
            legacy_business_rows(conn)
            conn.commit()
            before = conn.execute(text("SELECT to_jsonb(r) FROM workflow_runs r")).all()
            conn.commit()
            command.upgrade(config, "head")
            assert conn.execute(text("SELECT to_jsonb(r) FROM workflow_runs r")).all() == before
            conn.commit()
            command.downgrade(config, "f085_durable_evaluations")
            command.upgrade(config, "head")
            identity, version = uuid.uuid4(), uuid.uuid4()
            conn.execute(
                text("INSERT INTO tool_definitions(id,name,description) VALUES (:id,'Tool','')"),
                {"id": identity},
            )
            conn.execute(
                text(
                    "INSERT INTO tool_versions(id,definition_id,number,contract) "
                    "VALUES (:id,:definition,1,'{}')"
                ),
                {"id": version, "definition": identity},
            )
            conn.commit()
            for statement in [
                "UPDATE tool_versions SET contract='[]'",
                "DELETE FROM tool_versions",
                "UPDATE tool_definitions SET id=gen_random_uuid()",
            ]:
                with pytest.raises(DBAPIError, match="immutable|Retain"):
                    conn.execute(text(statement))
                conn.rollback()
            # Exercise a real worker claim against migrated tables/triggers, not
            # only the metadata-created schemas used by focused domain tests.
            scoped = engine.execution_options(schema_translate_map={None: schema})
            fixture = setup(scoped, monkeypatch, credential=True)
            assert invoke(scoped, fixture, effects.ToolAdapter(lambda **kw: kw["arguments"])) == {
                "value": "one"
            }
            for statement in [
                "UPDATE tool_executions SET result_json='{}'",
                "UPDATE tool_executions SET credential_digest='changed'",
                "DELETE FROM tool_executions",
            ]:
                with pytest.raises(DBAPIError, match="immutable|Retain"):
                    conn.execute(text(statement))
                conn.rollback()
            with pytest.raises(RuntimeError, match="Retain tool"):
                command.downgrade(config, "f085_durable_evaluations")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
