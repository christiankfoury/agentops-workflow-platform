import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from tests.test_execution_starts import available_code as available_code
from tests.test_webhooks import send, setup
from tests.test_webhooks import signing_config as signing_config


def test_webhook_migration_roundtrip_and_retention(available_code, signing_config):
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration91_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f090_llm_conversations")
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            with Session(scoped) as db:
                identity = setup(db).id
                send(db, identity)
            for statement in [
                "DELETE FROM webhook_triggers",
                "DELETE FROM webhook_deliveries",
                "UPDATE webhook_deliveries SET event_id='changed'",
                "UPDATE webhook_deliveries SET status='rejected'",
                "UPDATE webhook_deliveries SET version_id=gen_random_uuid()",
                "UPDATE webhook_triggers SET organization_id=gen_random_uuid()",
            ]:
                with pytest.raises(DBAPIError, match="immutable|Retain"):
                    conn.execute(text(statement))
                conn.rollback()
            conn.execute(text("UPDATE webhook_deliveries SET attempts=attempts+1"))
            conn.commit()
            with pytest.raises(RuntimeError, match="Retain webhook"):
                command.downgrade(config, "f090_llm_conversations")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
