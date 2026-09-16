import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from tests.generic_migration_fixtures import legacy_business_rows


def test_evaluation_migration_preserves_history_and_freezes_approval_authority():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration85_" + uuid.uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as connection:
            connection.execute(text(f'SET search_path TO "{schema}"'))
            connection.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "f083_sales_templates")
            ids = legacy_business_rows(connection)
            before = connection.scalar(text("SELECT to_jsonb(t) FROM evaluation_results t"))
            connection.commit()
            command.upgrade(config, "head")
            after = connection.scalar(text("SELECT to_jsonb(t) FROM evaluation_results t"))
            assert all(after[key] == value for key, value in before.items())
            assert after["requested_by_user_id"] is None and not after["automatic_approval"]
            connection.commit()
            with pytest.raises(DBAPIError, match="intent is immutable"):
                connection.execute(text("UPDATE evaluation_results SET automatic_approval=true"))
            connection.rollback()
            pending = uuid.uuid4()
            connection.execute(
                text("""
                INSERT INTO evaluation_results
                (id,evaluation_case_id,workflow_run_id,run_mode,status,automatic_approval)
                VALUES (:id,:case,:run,'multi_agent','pending',true)
            """),
                {"id": pending, "case": ids["case"], "run": ids["run"]},
            )
            connection.commit()
            with pytest.raises(DBAPIError, match="binding is immutable"):
                connection.execute(
                    text("UPDATE evaluation_results SET workflow_run_id=NULL WHERE id=:id"),
                    {"id": pending},
                )
            connection.rollback()
            with pytest.raises(RuntimeError, match="Finish or cancel"):
                command.downgrade(config, "f083_sales_templates")
            connection.rollback()
            connection.execute(
                text("UPDATE evaluation_results SET status='failed' WHERE id=:id"), {"id": pending}
            )
            connection.commit()
            command.downgrade(config, "f083_sales_templates")
            command.upgrade(config, "head")
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
