import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from src.models.tenant import DEFAULT_ORGANIZATION_ID


def test_legacy_backfill_counts_reversal_and_safe_rollback_gate():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration68_" + uuid.uuid4().hex
    with engine.begin() as admin:
        admin.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f067_identity")
            input_id, run_id, original_org = [uuid.uuid4() for _ in range(3)]
            conn.execute(
                text(
                    "INSERT INTO uploaded_inputs "
                    "(id, organization_id, title, input_type, raw_text) "
                    "VALUES (:id, :org, 'Preserved title', 'sales_report', "
                    "'Preserved private source')"
                ),
                {"id": input_id, "org": original_org},
            )
            conn.execute(
                text(
                    "INSERT INTO workflow_runs "
                    "(id, input_id, workflow_type, run_mode, status, final_output) "
                    "VALUES (:id, :input, 'sales_report', 'baseline', 'completed', "
                    "'Preserved output')"
                ),
                {"id": run_id, "input": input_id},
            )
            conn.commit()
            command.upgrade(config, "f068_tenant_ownership")
            source = conn.execute(text("SELECT * FROM uploaded_inputs")).mappings().one()
            run = conn.execute(text("SELECT * FROM workflow_runs")).mappings().one()
            assert source["id"] == input_id and source["organization_id"] == DEFAULT_ORGANIZATION_ID
            assert source["raw_text"] == "Preserved private source"
            assert run["id"] == run_id and run["final_output"] == "Preserved output"
            counts = dict(
                conn.execute(
                    text("SELECT table_name, record_count FROM tenant_backfill_counts")
                ).all()
            )
            assert counts["workflow_runs"] == counts["uploaded_inputs"] == 1
            assert conn.execute(text("SELECT count(*) FROM legacy_tenant_owners")).scalar_one() == 2
            conn.commit()
            command.downgrade(config, "f067_identity")
            assert (
                conn.execute(text("SELECT organization_id FROM uploaded_inputs")).scalar_one()
                == original_org
            )
            assert (
                conn.execute(text("SELECT organization_id FROM workflow_runs")).scalar_one() is None
            )
            conn.commit()
            command.upgrade(config, "f068_tenant_ownership")
            another_org = uuid.uuid4()
            conn.execute(
                text("INSERT INTO organizations (id, name) VALUES (:id, 'New tenant')"),
                {"id": another_org},
            )
            conn.execute(
                text(
                    "INSERT INTO uploaded_inputs (organization_id, title, input_type, raw_text) "
                    "VALUES (:org, 'New tenant input', 'sales_report', 'Do not discard ownership')"
                ),
                {"org": another_org},
            )
            conn.commit()
            with pytest.raises(RuntimeError, match="non-default data"):
                command.downgrade(config, "f067_identity")
            conn.rollback()
            assert (
                conn.execute(
                    text("SELECT count(*) FROM uploaded_inputs WHERE organization_id = :org"),
                    {"org": another_org},
                ).scalar_one()
                == 1
            )
    finally:
        with engine.begin() as admin:
            admin.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
