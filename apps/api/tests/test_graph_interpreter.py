import os
import uuid

import pytest
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from alembic import command
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.workflow_definition import DefinitionCreate
from src.schemas.workflow_graph import Expression, WorkflowGraph
from src.services import execution_starts, workflow_definitions
from src.services.execution_registry import ExecutorRegistry
from src.services.graph_expressions import ExecutionError, evaluate
from src.services.graph_interpreter import (
    advance_checkpoint,
    complete_work,
    execute_work,
    prepare_next,
    run_deterministic_execution,
)
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction
from tests.test_workflow_graph import NUMBER, all_primitives, code, edge, literal, obj, ref
from tests.test_workflow_transactions_postgres import database as database


def branching_graph():
    return {
        "entry_node": "start",
        "input_schema": obj(value=NUMBER),
        "output_schema": obj(result=NUMBER),
        "outputs": {"result": ref("result", "finish")},
        "nodes": [
            code(
                "start",
                input_schema=obj(value=NUMBER),
                output_schema=obj(value=NUMBER),
                inputs={"value": ref("value")},
            ),
            {
                "id": "choice",
                "type": "condition",
                "config": {
                    "cases": [
                        {
                            "label": "positive",
                            "when": {
                                "op": "gte",
                                "args": [ref("value", "start"), literal(0)],
                            },
                        }
                    ],
                    "default": "negative",
                },
            },
            {
                "id": "positive",
                "type": "transform",
                "output_schema": obj(result=NUMBER),
                "config": {"assign": {"result": {"op": "add", "args": [ref("value"), literal(1)]}}},
            },
            {
                "id": "negative",
                "type": "transform",
                "output_schema": obj(result=NUMBER),
                "config": {
                    "assign": {"result": {"op": "subtract", "args": [ref("value"), literal(1)]}}
                },
            },
            {
                "id": "finish",
                "type": "transform",
                "merge": "exclusive",
                "output_schema": obj(result=NUMBER),
                "config": {
                    "assign": {
                        "result": {
                            "op": "coalesce",
                            "args": [
                                ref("result", "positive", on_missing="null"),
                                ref("result", "negative", on_missing="default", default=0),
                            ],
                        }
                    }
                },
            },
        ],
        "edges": [
            edge("start", "choice"),
            edge("choice", "positive", "positive"),
            edge("choice", "negative", "negative"),
            edge("positive", "finish"),
            edge("negative", "finish"),
        ],
    }


def start(db, payload=None, inputs=None):
    item = workflow_definitions.create_definition(
        db,
        DefinitionCreate(
            name="Configured graph",
            graph=payload or branching_graph(),
        ),
    )
    workflow_definitions.publish(db, item.id, 1)
    return execution_starts.start_execution(
        db,
        ExecutionStartRequest(
            definition_id=item.id,
            input={"value": 2} if inputs is None else inputs,
            idempotency_key=uuid.uuid4().hex,
        ),
    )


@pytest.mark.parametrize("value,expected,selected", [(2, 3, "positive"), (-2, -3, "negative")])
def test_data_configured_branches_outputs_skips_and_attempts(database, value, expected, selected):
    with Session(database) as db:
        run = start(db, inputs={"value": value})
        result = run_deterministic_execution(db, run.id)
        assert result.status == "completed" and result.output_json == {"result": expected}
        rows = {row.node_id: row for row in db.scalars(select(StepRun)).all()}
        assert len(rows) == 5 and rows[selected].status == "completed"
        skipped = "negative" if selected == "positive" else "positive"
        assert rows[skipped].status == "skipped"
        attempts = db.scalars(select(StepAttempt)).all()
        assert len(attempts) == 4 and all(attempt.status == "completed" for attempt in attempts)
        assert all(attempt.llm_metadata is None for attempt in attempts)
        route_index = "1" if selected == "positive" else "2"
        assert result.checkpoint_json["edges"][route_index] == "selected"


def test_restart_continues_checkpoint_without_repeating_completed_handler(database):
    registry = ExecutorRegistry()
    calls = []

    def identity(value):
        calls.append(value)
        return value

    registry.handlers[("builtin.identity", 1)] = identity
    with Session(database) as db:
        identity = start(db).id
        advance_checkpoint(db, identity, registry)
        assert len(calls) == 1
    with Session(database) as restarted:
        run = run_deterministic_execution(restarted, identity, registry)
        assert run.status == "completed" and len(calls) == 1
        assert len(restarted.scalars(select(StepRun).where(StepRun.node_id == "start")).all()) == 1


def test_execution_releases_lock_and_stale_results_cannot_commit(database):
    with Session(database) as db, Session(database) as other:
        run = start(db)
        work = prepare_next(db, run.id)
        # Independent PostgreSQL session can acquire the row lock while work executes.
        current = other.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == run.id)
            .with_for_update(nowait=True)
        )
        other.commit()
        result = execute_work(work)
        with workflow_transaction(other, current):
            current.error_message = "Control operation fixture"
        with pytest.raises(StaleWorkflowError):
            complete_work(db, work, result=result)
        db.rollback()
        assert db.get(StepAttempt, work.attempt_id).output_json is None
        assert db.get(WorkflowExecution, run.id).status == "running"


@pytest.mark.parametrize(
    "mode,expected", [("exception", "handler_failed"), ("output", "output_invalid")]
)
def test_handler_and_output_failures_are_typed_and_preserve_attempts(database, mode, expected):
    registry = ExecutorRegistry()

    def handler(value):
        if mode == "exception":
            raise RuntimeError("private provider credential fixture")
        return {"value": "invalid number"}

    registry.handlers[("builtin.identity", 1)] = handler
    with Session(database) as db:
        run = start(db)
        result = advance_checkpoint(db, run.id, registry)
        assert result.status == "failed" and result.error_code == expected
        assert "credential" not in result.error_message
        attempt = db.scalar(select(StepAttempt))
        assert attempt.status == "failed" and attempt.error_code == expected
        assert attempt.input_json == {"value": 2}


def test_missing_binding_failure_and_explicit_null_default_semantics(database):
    payload = branching_graph()
    payload["input_schema"]["required"] = []
    with Session(database) as db:
        run = start(db, payload, {})
        result = advance_checkpoint(db, run.id)
        assert result.status == "failed" and result.error_code == "binding_missing"
        assert db.scalar(select(StepAttempt)).status == "failed"
    expression = Expression.model_validate(ref("value", on_missing="default", default=42))
    assert evaluate(expression, {}, {}) == 42
    assert evaluate(expression, {"value": None}, {}) is None
    exists = Expression.model_validate({"op": "exists", "args": [ref("value")]})
    assert evaluate(exists, {}, {}) is False and evaluate(exists, {"value": None}, {}) is True
    equality = Expression.model_validate({"op": "eq", "args": [literal(True), literal(1)]})
    assert evaluate(equality, {}, {}) is False
    overflow = Expression.model_validate(
        {"op": "multiply", "args": [literal(1e308), literal(1e308)]}
    )
    with pytest.raises(ExecutionError, match="non-finite"):
        evaluate(overflow, {}, {})


def test_registry_rejects_unregistered_handlers_unsupported_types_and_quality_revisions():
    registry = ExecutorRegistry()
    payload = {
        "entry_node": "start",
        "nodes": [code("start", config={"handler": "os.system", "version": 1})],
    }
    with pytest.raises(ValidationError, match="handler/version"):
        registry.validate(WorkflowGraph.model_validate(payload))
    # Every primitive now has a dispatch path. Catalog and policy availability
    # are checked separately at publication/start, and tools require workers.
    registry.validate(WorkflowGraph.model_validate(all_primitives()))
    payload = {
        "entry_node": "start",
        "nodes": [code("start"), code("review")],
        "edges": [edge("start", "review")],
        "quality_revision": {
            "entry_node": "start",
            "review_node": "review",
            "nodes": ["start", "review"],
            "max_revisions": 1,
        },
    }
    with pytest.raises(ValidationError, match="Quality revision"):
        registry.validate(WorkflowGraph.model_validate(payload))


@pytest.mark.parametrize("binding", ["input", "output"])
def test_expression_overflow_persists_a_typed_failure(database, binding):
    payload = {
        "entry_node": "start",
        "input_schema": obj(value=NUMBER),
        "output_schema": obj(value=NUMBER),
        "outputs": {"value": ref("value", "start")},
        "nodes": [
            code(
                "start",
                input_schema=obj(value=NUMBER),
                output_schema=obj(value=NUMBER),
                inputs={"value": ref("value")},
            )
        ],
    }
    expression = {"op": "add", "args": [ref("value"), literal(0.5)]}
    if binding == "input":
        payload["nodes"][0]["inputs"]["value"] = expression
    else:
        payload["outputs"]["value"] = expression
    with Session(database) as db:
        run = start(db, payload, {"value": 10**400})
        run = run_deterministic_execution(db, run.id)
        assert run.status == "failed" and run.error_code == "expression_range"
        db.expire_all()
        assert db.get(WorkflowExecution, run.id).status == "failed"


def test_checkpoint_migration_round_trip_and_nonempty_retention(monkeypatch):
    # Exercise checkpoint retention independently of the later job retention gate.
    monkeypatch.setattr(execution_starts, "enqueue", lambda *_: None)
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration74_" + uuid.uuid4().hex
    with engine.begin() as admin:
        admin.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f073_execution_starts")
            command.upgrade(config, "head")
            with Session(conn) as db:
                run = start(db)
                assert run.checkpoint_json == {}
                run_deterministic_execution(db, run.id)
                db.commit()
            with pytest.raises(RuntimeError, match="Retain execution"):
                command.downgrade(config, "f073_execution_starts")
            conn.rollback()
    finally:
        with engine.begin() as admin:
            admin.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
