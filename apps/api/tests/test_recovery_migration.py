import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from src.services.durable_queue import claim_jobs, process_claim
from src.services.execution_cancellation import cancel_execution
from src.services.execution_recovery import recover
from tests.test_graph_interpreter import start


def test_recovery_migration_roundtrip_and_retention():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration96_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f092_workflow_schedules")
            command.upgrade(config, "head")
            scoped = engine.execution_options(schema_translate_map={None: schema})
            with Session(scoped) as db:
                source_id = start(db).id
            process_claim(scoped, claim_jobs(scoped, "migration-fixture")[0])
            with Session(scoped) as db:
                cancel_execution(db, source_id, "Migration fixture")
                recover(db, source_id, "Migration recovery")
            for statement in [
                "DELETE FROM execution_recoveries",
                "UPDATE execution_recoveries SET reason='rewrite'",
                "UPDATE step_runs SET recovered_from_id=NULL WHERE recovered_from_id IS NOT NULL",
            ]:
                with pytest.raises(DBAPIError, match="immutable"):
                    conn.execute(text(statement))
                conn.rollback()
            with pytest.raises(RuntimeError, match="Retain recovery"):
                command.downgrade(config, "f092_workflow_schedules")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
