import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from src.services.worker_presence import beat


def test_presence_migration_is_additive_and_ephemeral():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration97_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f096_execution_recovery")
            assert "worker_presence" not in inspect(conn).get_table_names(schema=schema)
            command.upgrade(config, "head")
            conn.commit()
            beat(engine.execution_options(schema_translate_map={None: schema}), "fixture", 2)
            assert conn.scalar(text("SELECT count(*) FROM worker_presence")) == 1
            conn.commit()
            command.downgrade(config, "f096_execution_recovery")
            assert "worker_presence" not in inspect(conn).get_table_names(schema=schema)
            assert "execution_events" in inspect(conn).get_table_names(schema=schema)
            command.upgrade(config, "head")
            assert conn.scalar(text("SELECT count(*) FROM worker_presence")) == 0
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
