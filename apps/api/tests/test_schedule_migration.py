import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from src.services import schedules
from tests.test_schedules import setup


def test_schedule_migration_roundtrip_and_retention():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration92_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f091_webhook_triggers")
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            with Session(scoped) as db:
                item = setup(db)
                due = item.next_fire_at
            assert schedules.fire_due_schedules(scoped, now=due) == 1
            for statement in [
                "DELETE FROM workflow_schedules",
                "DELETE FROM schedule_fires",
                "UPDATE schedule_fires SET status='rejected'",
                "UPDATE schedule_fires SET revision=revision+1",
                "UPDATE workflow_schedules SET organization_id=gen_random_uuid()",
            ]:
                with pytest.raises(DBAPIError, match="immutable|Retain"):
                    conn.execute(text(statement))
                conn.rollback()
            with pytest.raises(RuntimeError, match="Retain schedule"):
                command.downgrade(config, "f091_webhook_triggers")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
