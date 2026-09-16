import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from tests.test_llm_tools import process, response, setup


def test_migration_roundtrip_and_populated_retention(monkeypatch):
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration90_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f086_tool_contracts")
            command.upgrade(config, "head")
            command.downgrade(config, "f086_tool_contracts")
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            _, registry, _, _ = setup(scoped, monkeypatch, [response(content='{"value":2}')])
            process(scoped, registry)
            for statement in [
                "DELETE FROM llm_conversations",
                "UPDATE llm_conversations SET fingerprint='changed'",
                "UPDATE llm_conversations SET step_run_id=gen_random_uuid()",
            ]:
                with pytest.raises(DBAPIError, match="immutable|Retain"):
                    conn.execute(text(statement))
                conn.rollback()
            with pytest.raises(RuntimeError, match="Retain LLM"):
                command.downgrade(config, "f086_tool_contracts")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
