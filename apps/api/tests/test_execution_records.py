import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from src.models.workflow_execution import ExecutionEvent, StepAttempt, StepRun, WorkflowExecution
from src.schemas.workflow_definition import DefinitionCreate
from src.services import workflow_definitions
from src.services.execution_records import add_attempt, add_step
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_graph import code
from tests.test_workflow_transactions_postgres import database as database


def fixture_execution(db):
    definition = workflow_definitions.create_definition(
        db,
        DefinitionCreate(
            name="Records",
            graph={
                "entry_node": "start",
                "nodes": [
                    code("start", retry={"max_attempts": 2}),
                ],
            },
        ),
    )
    version = workflow_definitions.publish(db, definition.id, 1)
    # Explicit persistence fixture: Phase 73 owns accepted starts, not this helper.
    run = WorkflowExecution(version_id=version.id, input_json={})
    db.add(run)
    db.commit()
    return run


def test_non_llm_attempt_history_and_atomic_terminal_transitions(database):
    with Session(database) as db:
        run = fixture_execution(db)
        transition(db, run, run, "running")
        step = add_step(db, run, "start")
        first = add_attempt(db, run, step)
        transition(db, run, step, "running")
        transition(db, run, first, "running")
        with pytest.raises(ValueError, match="active steps"):
            transition(db, run, run, "completed")
        transition(db, run, first, "failed")
        transition(db, run, step, "retrying")
        second = add_attempt(db, run, step)
        assert [first.number, second.number] == [1, 2]
        assert first.idempotency_key == second.idempotency_key == step.idempotency_key
        assert second.llm_metadata is None and not hasattr(step, "agent_name")
        with workflow_transaction(db, run):
            transition(db, run, step, "running")
            transition(db, run, second, "running")
            second.output_json = step.output_json = run.output_json = {"result": "fixture"}
            transition(db, run, second, "completed")
            transition(db, run, step, "completed")
            transition(db, run, run, "completed")
        assert all(item.completed_at is not None for item in [first, second, step, run])
        with pytest.raises(ValueError, match="Cannot transition"):
            transition(db, run, run, "running")
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 2


def test_logical_identity_uniqueness_branch_iteration_and_version_pin(database):
    with Session(database) as db:
        run = fixture_execution(db)
        first = add_step(db, run, "start")
        branch = add_step(db, run, "start", branch="other")
        revision = add_step(db, run, "start", iteration=1)
        assert len({item.idempotency_key for item in [first, branch, revision]}) == 3
        with pytest.raises(IntegrityError):
            add_step(db, run, "start")
        assert db.scalar(select(func.count()).select_from(StepRun)) == 3
        with pytest.raises(ValueError, match="absent"):
            add_step(db, run, "missing")
        run.version_id = uuid.uuid4()
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
        run.status = "running"
        with pytest.raises(ValueError, match="authority"):
            db.commit()
        db.rollback()
        run.output_json = {"bypass": True}
        with pytest.raises(ValueError, match="authority"):
            db.commit()
        db.rollback()
        other = fixture_execution(db)
        with pytest.raises(ValueError, match="authority"):
            with workflow_transaction(db, other):
                first.output_json = {"wrong_run": True}
                db.flush()


def test_transition_failure_rolls_back_state_output_events_and_revision(database):
    with Session(database) as db:
        run = fixture_execution(db)
        before = run.state_revision
        with pytest.raises(RuntimeError, match="injected"):
            with workflow_transaction(db, run):
                transition(db, run, run, "running")
                run.output_json = {"discard": True}
                raise RuntimeError("injected")
        assert run.status == "pending" and run.state_revision == before
        assert run.output_json is None
        assert db.scalar(select(func.count()).select_from(ExecutionEvent)) == 0


def test_children_cannot_start_before_parents_and_terminal_output_stays_frozen(database):
    with Session(database) as db:
        run = fixture_execution(db)
        step = add_step(db, run, "start")
        with pytest.raises(ValueError, match="parent execution"):
            transition(db, run, step, "running")
        transition(db, run, run, "running")
        attempt = add_attempt(db, run, step)
        with pytest.raises(ValueError, match="logical step"):
            transition(db, run, attempt, "running")
        transition(db, run, step, "running")
        transition(db, run, attempt, "running")
        transition(db, run, attempt, "completed")
        transition(db, run, step, "completed")
        transition(db, run, run, "completed")
        with pytest.raises(ValueError, match="Terminal"):
            with workflow_transaction(db, run):
                run.output_json = {"late_result": True}
        assert run.output_json is None


def test_duplicate_attempt_race_is_fenced(database):
    with Session(database) as db:
        run = fixture_execution(db)
        transition(db, run, run, "running")
        step = add_step(db, run, "start")
        run_id, step_id = run.id, step.id
    barrier = Barrier(2)

    def attempt():
        with Session(database) as db:
            run, step = db.get(WorkflowExecution, run_id), db.get(StepRun, step_id)
            barrier.wait(timeout=10)
            try:
                add_attempt(db, run, step)
                return "accepted"
            except StaleWorkflowError:
                return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == ["accepted", "stale"]
    with Session(database) as db:
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 1
        run, step = db.get(WorkflowExecution, run_id), db.get(StepRun, step_id)
        with pytest.raises(ValueError, match="active attempt"):
            add_attempt(db, run, step)


def test_attempt_bounds_active_wait_guard_and_pending_initialization(database):
    with Session(database) as db:
        run = fixture_execution(db)
        transition(db, run, run, "running")
        step = add_step(db, run, "start")
        for number in [1, 2]:
            attempt = add_attempt(db, run, step)
            assert attempt.number == number
            transition(db, run, step, "running")
            transition(db, run, attempt, "running")
            with pytest.raises(ValueError, match="active attempts"):
                transition(db, run, step, "waiting")
            transition(db, run, attempt, "failed")
            transition(db, run, step, "retrying")
        with pytest.raises(ValueError, match="limit reached"):
            add_attempt(db, run, step)
        db.add(WorkflowExecution(version_id=run.version_id, status="completed"))
        with pytest.raises(ValueError, match="begin pending"):
            db.commit()
        db.rollback()


def test_execution_reads_are_scoped_and_historical_traces_keep_original_labels(
    database,
    tenants,
    tenant_client,
):
    identities = []
    for owner in tenants:
        actor = prepare(database, owner)
        with Session(database) as db:
            bind_tenant(db, owner["org"])
            db.info["principal"] = Principal("admin", actor, owner["org"])
            run = fixture_execution(db)
            transition(db, run, run, "running")
            step = add_step(db, run, "start")
            add_attempt(db, run, step)
            identities.append((run.id, step.id))
    own, other = identities
    client = tenant_client
    assert len(client.get("/workflow-executions").json()) == 1
    assert client.get(f"/workflow-executions/{own[0]}/steps").json()[0]["step_type"] == "code"
    attempts = client.get(f"/workflow-executions/{own[0]}/steps/{own[1]}/attempts").json()
    assert attempts[0]["number"] == 1 and attempts[0]["llm_metadata"] is None
    for suffix in ["", "/steps", "/events", f"/steps/{other[1]}/attempts"]:
        assert client.get(f"/workflow-executions/{other[0]}{suffix}").status_code == 404
    assert client.get(f"/workflow-executions/{own[0]}/steps/{other[1]}/attempts").status_code == 404
    legacy = client.get(f"/workflow-executions/legacy/{tenants[0]['run']}").json()
    assert legacy["source"] == "legacy" and legacy["run"]["workflow_type"] == "sales_report"
    assert (
        legacy["run"]["run_mode"] == "baseline" and legacy["agent_steps"][0]["model"] == "fixture"
    )
    assert client.get(f"/workflow-executions/legacy/{tenants[1]['run']}").status_code == 404


def test_execution_migration_preserves_legacy_data_and_fences_identity():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration72_" + uuid.uuid4().hex
    with engine.begin() as admin:
        admin.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "f071_workflow_definitions")
            from src.models.workflow_run import WorkflowType
            from src.services.demo_dataset import seed_demo_dataset

            with Session(conn) as db:
                seed_demo_dataset(db, WorkflowType.sales_report)
            tables = ["workflow_runs", "agent_steps", "cost_events", "evaluation_results"]
            before = {
                table: conn.execute(
                    text(f"SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM {table} t")
                ).scalar()
                for table in tables
            }
            conn.commit()
            command.upgrade(config, "f072_execution_records")
            for table in tables:
                # Compare complete rows, including output/cost/evaluation foreign keys.
                assert (
                    conn.execute(
                        text(f"SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM {table} t")
                    ).scalar()
                    == before[table]
                )
            conn.commit()
            command.downgrade(config, "f071_workflow_definitions")
            command.upgrade(config, "f072_execution_records")
            with Session(conn) as db:
                run = fixture_execution(db)
                run_id = run.id
                db.commit()
            with pytest.raises(DBAPIError, match="immutable"):
                conn.execute(
                    text("UPDATE workflow_executions SET version_id = :version WHERE id = :id"),
                    {"version": uuid.uuid4(), "id": run_id},
                )
            conn.rollback()
            with pytest.raises(RuntimeError, match="Retain execution history"):
                command.downgrade(config, "f071_workflow_definitions")
            conn.rollback()
    finally:
        with engine.begin() as admin:
            admin.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
