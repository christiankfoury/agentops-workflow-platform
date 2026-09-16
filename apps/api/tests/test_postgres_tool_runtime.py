import json
from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep

import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models.tool import ToolCredential, ToolExecution
from src.models.workflow_execution import StepAttempt, WorkflowExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.tool import CredentialCreate, ToolContract, ToolCreate
from src.schemas.workflow_definition import DefinitionCreate
from src.services import durable_queue as queue
from src.services import postgres_tool as pg
from src.services import tool_catalog, workflow_definitions
from src.services.execution_cancellation import cancel_execution
from src.services.execution_starts import start_execution
from src.services.tool_effects import ToolFailure
from src.services.workflow_transactions import StaleWorkflowError
from src.worker import run_worker
from tests.test_postgres_tool import ORGANIZATION, PASSWORD, QUERY, active, clean
from tests.test_postgres_tool import data_source as data_source
from tests.test_workflow_graph import STRING, literal, obj
from tests.test_workflow_transactions_postgres import database as database

INPUT = obj(label=STRING)
OUTPUT = obj(rows={"type": "array", "items": INPUT}, row_count={"type": "integer"})
RETRY = {
    "max_attempts": 2,
    "initial_delay_seconds": 0,
    "retryable_errors": ["tool_unavailable", "tool_timeout"],
}


def fixture(database, data_source, monkeypatch, *, query=QUERY, output=OUTPUT):
    raw = data_source.policy.model_dump(mode="json")
    raw["queries"]["find"]["sql"] = query
    monkeypatch.setattr(settings, "postgres_tool_connections", {f"{ORGANIZATION}/fixture": raw})
    monkeypatch.setattr(
        settings, "tool_credential_values", {f"{ORGANIZATION}/fixture": SecretStr(PASSWORD)}
    )
    monkeypatch.setattr(settings, "worker_control_poll_seconds", 0.02)
    with Session(database) as db:
        credential = tool_catalog.create_credential(
            db, CredentialCreate(name="Read data", source_alias="fixture")
        )
        version = tool_catalog.create(
            db,
            ToolCreate(
                name="Registered data query",
                contract=ToolContract(
                    adapter="postgresql",
                    input_schema=INPUT,
                    output_schema=output,
                    credential_ref=credential.id,
                    side_effecting=False,
                    retry=RETRY,
                    options={"connection": "fixture", "query": "find"},
                ),
            ),
        )
        graph = {
            "entry_node": "query",
            "nodes": [
                {
                    "id": "query",
                    "type": "tool",
                    "input_schema": INPUT,
                    "output_schema": output,
                    "inputs": {"label": literal("one")},
                    "retry": RETRY,
                    "config": {
                        "adapter": "postgresql",
                        "tool_id": str(version.definition_id),
                        "version": 1,
                    },
                }
            ],
        }
        definition = workflow_definitions.create_definition(
            db, DefinitionCreate(name="Read graph", graph=graph)
        )
        workflow_definitions.publish(db, definition.id, 1)
        run = start_execution(
            db,
            ExecutionStartRequest(
                definition_id=definition.id, input={}, idempotency_key="postgres-fixture"
            ),
        )
        return run.id, credential.id, definition.id


def test_worker_read_and_redacted_persisted_receipt(database, data_source, monkeypatch):
    run_id, *_ = fixture(database, data_source, monkeypatch)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run, effect = db.get(WorkflowExecution, run_id), db.scalar(select(ToolExecution))
        assert (run.status, effect.status) == ("completed", "succeeded")
        assert effect.result_json == {"rows": [{"label": "one"}], "row_count": 1}
        assert effect.latency_ms > 0 and effect.attempts == 1
        serialized = json.dumps(tool_catalog.public(effect), default=str)
        assert (
            PASSWORD not in serialized
            and "SELECT" not in serialized
            and data_source.policy.database not in serialized
        )
    clean(data_source)


def test_query_output_secret_redaction(database, data_source, monkeypatch):
    fixture(database, data_source, monkeypatch, query=f"SELECT '{PASSWORD}' || %(label)s AS label")
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        assert effect.result_json["rows"] == [{"label": "[REDACTED]one"}]


@pytest.mark.parametrize("change", ["credential", "policy", "alias"])
def test_revocation_and_pinned_policy_prevent_dispatch(database, data_source, monkeypatch, change):
    run_id, credential_id, _ = fixture(database, data_source, monkeypatch)
    if change == "credential":
        with Session(database) as db:
            tool_catalog.set_active(db, ToolCredential, credential_id, False)
    elif change == "policy":
        settings.postgres_tool_connections[f"{ORGANIZATION}/fixture"]["max_rows"] = 5
    else:
        settings.postgres_tool_connections.clear()

    def forbidden(*args, **kwargs):
        pytest.fail("Revoked or changed policy reached the data connection")

    monkeypatch.setattr(pg, "request", forbidden)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, run_id).status == "failed"
        assert db.scalar(select(ToolExecution)) is None


def test_schema_mismatch_is_permanent_and_response_not_retained(database, data_source, monkeypatch):
    run_id, *_ = fixture(
        database,
        data_source,
        monkeypatch,
        output=obj(
            rows={"type": "array", "items": obj(label={"type": "integer"})},
            row_count={"type": "integer"},
        ),
    )
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, run_id).status == "failed"
        effect = db.scalar(select(ToolExecution))
        assert effect.status == "failed" and effect.error_code == "tool_response_invalid"
        assert effect.result_json is None and effect.attempts == 1


def test_retry_after_completed_read_does_not_mutate_data(database, data_source, monkeypatch):
    run_id, *_ = fixture(database, data_source, monkeypatch)
    original, calls = pg.request, []

    def lost_response(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(result)
        if len(calls) == 1:
            raise ToolFailure("tool_unavailable")
        return result

    monkeypatch.setattr(pg, "request", lost_response)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, run_id).status == "completed"
        assert db.scalar(select(ToolExecution)).attempts == 2
        assert len(db.scalars(select(StepAttempt)).all()) == 2
    assert len(calls) == 2 and calls[0] == calls[1]
    with data_source.data.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM public.records")
        assert cursor.fetchone() == (2,)
    clean(data_source)


def test_cancellation_fences_workflow_and_closes_data_connection(
    database, data_source, monkeypatch
):
    run_id, *_ = fixture(
        database, data_source, monkeypatch, query="SELECT %(label)s AS label FROM pg_sleep(10)"
    )
    claim = queue.claim_jobs(database, "cancel-query")[0]
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(queue.process_claim, database, claim)
        end = monotonic() + 5
        while not active(data_source) and monotonic() < end:
            sleep(0.02)
        assert active(data_source) > 0
        with Session(database) as db:
            cancel_execution(db, run_id)
        with pytest.raises(StaleWorkflowError):
            pending.result(timeout=5)
    with Session(database) as db:
        run = db.get(WorkflowExecution, run_id)
        assert run.status == "cancelled" and run.output_json is None
    clean(data_source)


def test_parameter_contract_must_match_registered_query(database, data_source, monkeypatch):
    with pytest.raises(HTTPException) as error:
        fixture(database, data_source, monkeypatch, query="SELECT %(unregistered)s AS label")
    assert error.value.status_code == 422
