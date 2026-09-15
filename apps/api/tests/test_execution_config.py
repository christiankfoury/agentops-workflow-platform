import os
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from alembic import command
from src.models.agent_setting import AgentSetting
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.models.workflow_definition import WorkflowDefinition, WorkflowVersion
from src.models.workflow_execution import StepRun, WorkflowExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.workflow_definition import DefinitionUpdate
from src.services import workflow_definitions
from src.services.delay_runtime import wake_due_delays
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.execution_starts import start_execution
from src.services.workflow_transactions import workflow_transaction
from src.worker import run_worker
from tests.test_graph_interpreter import start
from tests.test_llm_execution import Provider, graph, prompt
from tests.test_workflow_graph import edge
from tests.test_workflow_transactions_postgres import database as database


def test_settings_and_prompt_publication_only_affect_later_runs(database, monkeypatch):
    with Session(database) as db:
        first_prompt = prompt(db)
        db.add(
            AgentSetting(
                agent_type=AgentType.analyst,
                model="gpt-4.1-mini",
                temperature=0.2,
                max_tokens=40,
                timeout_seconds=12,
                max_retries=9,
                active_prompt_version_id=first_prompt,
            )
        )
        db.commit()
        payload = graph(first_prompt)
        payload["nodes"][0]["config"]["use_agent_settings"] = True
        payload["entry_node"] = "pause"
        payload["nodes"].insert(0, {"id": "pause", "type": "delay", "config": {"seconds": 3600}})
        payload["edges"] = [edge("pause", "generate")]
        first = start(db, payload, {})
        first_id = first.id
        version = db.get(WorkflowVersion, first.version_id)
        definition_id = version.definition_id
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        second_prompt = prompt(db)
        db.get(PromptVersion, second_prompt).template = "New prompt publication"
        setting = db.scalar(select(AgentSetting))
        setting.model, setting.max_tokens, setting.temperature = "gpt-4.1", 80, 0.7
        setting.active_prompt_version_id = second_prompt
        db.commit()
        payload["nodes"][1]["config"]["prompt_version_id"] = str(second_prompt)
        definition = db.get(WorkflowDefinition, definition_id)
        item = workflow_definitions.update_draft(
            db,
            definition_id,
            DefinitionUpdate(
                name=definition.name, graph=payload, expected_revision=definition.draft_revision
            ),
        )
        workflow_definitions.publish(db, definition_id, item.draft_revision)
        second_id = start_execution(
            db,
            ExecutionStartRequest(
                definition_id=definition_id, input={}, idempotency_key=str(uuid.uuid4())
            ),
        ).id
        with pytest.raises(ValueError, match="immutable"):
            with workflow_transaction(db, db.get(WorkflowExecution, first_id)):
                db.get(WorkflowExecution, first_id).runtime_config = {}
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        due = max(step.wake_at for step in db.scalars(select(StepRun)))
    assert wake_due_delays(database, now=due) == 2
    provider = Provider([{"value": 2}, {"value": 2}])
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    calls = {call["system"]: call for call in provider.calls}
    assert calls["Fixture prompt"]["model"] == "gpt-4.1-mini"
    assert calls["Fixture prompt"]["max_tokens"] == 40
    assert calls["New prompt publication"]["model"] == "gpt-4.1"
    assert calls["New prompt publication"]["max_tokens"] == 80
    assert all(call["max_retries"] == 0 for call in provider.calls)
    with Session(database) as db:
        assert all(
            db.get(WorkflowExecution, key).status == "completed" for key in [first_id, second_id]
        )


def test_configuration_migration_retains_old_rows_and_protects_raw_sql_updates():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration82_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f081_parallel_jobs")
            from tests.generic_migration_fixtures import pre_deadline_execution

            with Session(conn) as db:
                old_id = pre_deadline_execution(db)
            command.upgrade(config, "head")
            assert (
                conn.execute(
                    text("SELECT runtime_config FROM workflow_executions WHERE id=:id"),
                    {"id": old_id},
                ).scalar()
                == {}
            )
            conn.commit()
            scoped = engine.execution_options(schema_translate_map={None: schema})
            with Session(scoped) as db:
                identity = start(db, graph(prompt(db)), {}).id
            with pytest.raises(Exception, match="immutable"):
                conn.execute(
                    text("UPDATE workflow_executions SET runtime_config='{}'::jsonb WHERE id=:id"),
                    {"id": identity},
                )
            conn.rollback()
            with pytest.raises(RuntimeError, match="Retain execution LLM configuration"):
                command.downgrade(config, "f081_parallel_jobs")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_settings_created_during_acceptance_wait_until_the_next_run(database, monkeypatch):
    from copy import deepcopy

    from src.services import execution_config
    from tests.test_workflow_graph import ref

    original, inserted = execution_config.get_agent_runtime_config, False

    def concurrent_publication(db, agent_type, **kwargs):
        nonlocal inserted
        resolved = original(db, agent_type, **kwargs)
        if not inserted:
            inserted = True
            with Session(database) as other:
                other.add(
                    AgentSetting(
                        agent_type=AgentType.analyst,
                        model="fixture-later-model",
                        max_tokens=40,
                        timeout_seconds=12,
                        max_retries=0,
                    )
                )
                other.commit()
        return resolved

    monkeypatch.setattr(execution_config, "get_agent_runtime_config", concurrent_publication)
    with Session(database) as db:
        payload = graph(prompt(db))
        payload["nodes"][0]["config"]["use_agent_settings"] = True
        second = deepcopy(payload["nodes"][0])
        second["id"] = "second"
        second["inputs"] = {"value": ref("value", "generate")}
        payload["nodes"].append(second)
        payload["edges"] = [edge("generate", "second")]
        first = start(db, payload, {}).runtime_config
        later = start(db, payload, {}).runtime_config
    assert first["generate"]["model"] == first["second"]["model"]
    assert first["generate"]["model"] != "fixture-later-model"
    assert later["generate"]["model"] == later["second"]["model"] == "fixture-later-model"
