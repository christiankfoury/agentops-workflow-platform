import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event

import pytest
from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.config import settings
from src.models.audit_event import AuditEvent
from src.models.tenant import DEFAULT_ORGANIZATION_ID
from src.models.tool import ToolCredential, ToolExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.tool import CredentialCreate, EffectResolution, ToolContract, ToolCreate
from src.schemas.workflow_definition import DefinitionCreate
from src.services import tool_catalog as catalog
from src.services import tool_effects as effects
from src.services import workflow_definitions as definitions
from src.services.durable_queue import claim_jobs, jobs
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.execution_starts import start_execution
from src.services.graph_expressions import ExecutionError
from src.services.graph_interpreter import prepare_next
from src.services.worker_leases import recover_claim
from tests.test_worker_leases import expire
from tests.test_workflow_transactions_postgres import database as database

SCHEMA = {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]}


def test_uncertain_effect_timestamp_cannot_extend_recovery_retention(database, monkeypatch):
    fixture = setup(database, monkeypatch)

    def lost(**_):
        raise effects.ToolFailure("tool_unavailable")

    with pytest.raises(ExecutionError):
        invoke(database, fixture, effects.ToolAdapter(lost))
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        assert effect.status == "unknown"
        effect.created_at += timedelta(hours=1)
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()


def prepare(database, claim):
    with Session(database) as db:

        def attach(_run, work):
            db.connection().execute(
                update(jobs).where(jobs.c.id == claim.id).values(attempt_id=work.attempt_id)
            )

        work = prepare_next(db, claim.execution_id, on_checkpoint=attach)
        return work.attempt_id


def setup(database, monkeypatch, *, side_effecting=True, credential=False, timeout=30):
    # Ledger tests supply isolated fixture adapters; production catalog-policy
    # validation and HTTP dispatch are covered by test_http_tool_runtime.
    from src.services import tool_runtime

    monkeypatch.setattr(tool_runtime, "validate_references", lambda *_, **__: None)
    monkeypatch.setitem(DEFAULT_REGISTRY.executors, "tool", lambda *_: None)
    monkeypatch.setattr(settings, "worker_lease_seconds", 120)
    with Session(database) as db:
        credential_id = None
        if credential:
            credential_id = catalog.create_credential(
                db, CredentialCreate(name="Fixture credential", source_alias="fixture")
            ).id
            monkeypatch.setattr(
                settings,
                "tool_credential_values",
                {f"{DEFAULT_ORGANIZATION_ID}/fixture": SecretStr("fixture-secret-value")},
            )
        contract = ToolContract(
            adapter="http",
            input_schema=SCHEMA,
            output_schema=SCHEMA,
            side_effecting=side_effecting,
            timeout_seconds=timeout,
            credential_ref=credential_id,
            retry={"max_attempts": 3, "retryable_errors": ["tool_unavailable"]},
        )
        version = catalog.create(db, ToolCreate(name="Fixture", contract=contract))
        definition = definitions.create_definition(
            db,
            DefinitionCreate(
                name="Tool fixture",
                graph={
                    "entry_node": "action",
                    "nodes": [
                        {
                            "id": "action",
                            "type": "tool",
                            "input_schema": SCHEMA,
                            "output_schema": SCHEMA,
                            "inputs": {"value": {"op": "literal", "value": "one"}},
                            "config": {"tool_id": str(version.definition_id), "version": 1},
                            "retry": {"max_attempts": 3, "initial_delay_seconds": 0},
                        }
                    ],
                },
            ),
        )
        definitions.publish(db, definition.id, 1)
        start_execution(
            db,
            ExecutionStartRequest(definition_id=definition.id, idempotency_key="fixture", input={}),
        )
        version_id = version.id
    claim = claim_jobs(database, "fixture")[0]
    return claim, prepare(database, claim), version_id, credential_id


def invoke(database, fixture, adapter, value="one"):
    claim, attempt, version, _ = fixture
    return effects.execute_tool(
        database, claim, attempt, version, {"value": value}, adapters={"http": adapter}
    )


def restart(database, fixture):
    claim, _, version, credential = fixture
    expire(database, claim)
    assert recover_claim(database, claim)
    next_claim = claim_jobs(database, "replacement")[0]
    return next_claim, prepare(database, next_claim), version, credential


def test_duplicate_execution_shares_effect_and_conflicts_on_changed_input(database, monkeypatch):
    from src.models.workflow_execution import WorkflowExecution

    fixture = setup(database, monkeypatch)
    with Session(database) as db:
        revision = db.get(WorkflowExecution, fixture[0].execution_id).state_revision
    calls = []

    def remote(**kwargs):
        calls.append(kwargs["effect_key"])
        return kwargs["arguments"]

    adapter = effects.ToolAdapter(remote)
    assert invoke(database, fixture, adapter) == {"value": "one"}
    assert invoke(database, fixture, adapter) == {"value": "one"}
    with pytest.raises(ExecutionError, match="input changed"):
        invoke(database, fixture, adapter, "different")
    assert len(calls) == 1
    with Session(database) as db:
        assert db.get(WorkflowExecution, fixture[0].execution_id).state_revision == revision
        row = db.scalar(select(ToolExecution))
        assert row.status == "succeeded" and row.attempts == 1


def test_concurrent_duplicate_cannot_dispatch_twice(database, monkeypatch):
    fixture = setup(database, monkeypatch)
    entered, release = Event(), Event()

    def remote(**kwargs):
        entered.set()
        assert release.wait(15)
        return kwargs["arguments"]

    adapter = effects.ToolAdapter(remote)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(invoke, database, fixture, adapter)
        assert entered.wait(10)
        with pytest.raises(ExecutionError, match="already in progress"):
            invoke(database, fixture, adapter)
        release.set()
        assert first.result(timeout=10) == {"value": "one"}


@pytest.mark.parametrize("recovery", ["none", "idempotent", "reconcile"])
def test_response_lost_after_acceptance_is_recovered_or_requires_resolution(
    database, monkeypatch, recovery
):
    fixture = setup(database, monkeypatch)
    remote_effects = {}

    def remote(**kwargs):
        key = kwargs["effect_key"]
        if key not in remote_effects:
            remote_effects[key] = kwargs["arguments"]
            raise SystemExit("Fixture worker death after remote acceptance")
        return remote_effects[key]

    adapter = effects.ToolAdapter(
        remote,
        recovery,
        lambda **kw: effects.Reconciliation("succeeded", remote_effects[kw["effect_key"]]),
    )
    with pytest.raises(SystemExit):
        invoke(database, fixture, adapter)
    replacement = restart(database, fixture)
    if recovery == "none":
        with pytest.raises(ExecutionError, match="resolution"):
            invoke(database, replacement, adapter)
        with Session(database) as db:
            row = db.scalar(select(ToolExecution))
            assert row.status == "unknown"
            effects.resolve(
                db,
                row.id,
                EffectResolution(
                    succeeded=True, result={"value": "one"}, evidence="Fixture receipt verified"
                ),
            )
        assert invoke(database, replacement, adapter) == {"value": "one"}
    else:
        assert invoke(database, replacement, adapter) == {"value": "one"}
    assert len(remote_effects) == 1


def test_crash_before_dispatch_can_resume_without_ambiguity(database, monkeypatch):
    fixture = setup(database, monkeypatch)
    adapter = effects.ToolAdapter(lambda **kw: kw["arguments"])
    claim, attempt, version, _ = fixture
    with Session(database) as db:
        effects.reserve(db, claim, attempt, version, {"value": "one"}, "tool", {"http": adapter})
    replacement = restart(database, fixture)
    assert invoke(database, replacement, adapter) == {"value": "one"}


def test_worker_credential_redaction_and_revocation(database, monkeypatch):
    fixture = setup(database, monkeypatch, credential=True, side_effecting=False)

    def echo(**kwargs):
        assert kwargs["secret"] == "fixture-secret-value"
        return {"value": "echo: " + kwargs["secret"]}

    adapter = effects.ToolAdapter(echo, side_effecting=False)
    assert invoke(database, fixture, adapter) == {"value": "echo: [REDACTED]"}
    with Session(database) as db:
        row = db.scalar(select(ToolExecution))
        evidence = json.dumps(catalog.public(row), default=str)
        audits = db.scalars(select(AuditEvent)).all()
        assert "fixture-secret-value" not in evidence + repr([a.details_json for a in audits])
        assert any(item.action == "tool.credential.use" for item in audits)
        catalog.set_active(db, ToolCredential, fixture[3], False)
    with pytest.raises(ExecutionError, match="credential is unavailable"):
        invoke(database, fixture, adapter)


def test_definite_failure_retries_with_same_key_and_suppresses_private_errors(
    database, monkeypatch
):
    fixture = setup(database, monkeypatch)
    keys = []

    def remote(**kwargs):
        keys.append(kwargs["effect_key"])
        if len(keys) == 1:
            raise effects.ToolFailure("tool_unavailable", uncertain=False)
        return kwargs["arguments"]

    adapter = effects.ToolAdapter(remote)
    with pytest.raises(ExecutionError):
        invoke(database, fixture, adapter)
    assert invoke(database, fixture, adapter) == {"value": "one"}
    assert keys[0] == keys[1]
    claim, attempt, version, _ = fixture

    def private_error(**_):
        raise RuntimeError("a-private-provider-credential")

    with pytest.raises(ExecutionError) as error:
        effects.execute_tool(
            database,
            claim,
            attempt,
            version,
            {"value": "one"},
            call_id="second",
            adapters={"http": effects.ToolAdapter(private_error)},
        )
    assert "a-private-provider-credential" not in str(error.value)
    with Session(database) as db:
        rows = db.scalars(select(ToolExecution)).all()
        assert len({row.effect_key for row in rows}) == 2
        assert "a-private-provider-credential" not in repr([catalog.public(row) for row in rows])
        assert {row.status for row in rows} == {"succeeded", "unknown"}


def test_expired_deadline_and_forged_worker_claim_prevent_dispatch(database, monkeypatch):
    from dataclasses import replace
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from src.models.workflow_execution import StepAttempt, WorkflowExecution
    from src.services.workflow_transactions import workflow_transaction

    fixture = setup(database, monkeypatch)
    claim, attempt, version, credential = fixture

    def unexpected(**_):
        pytest.fail("Unauthorized tool dispatch")

    adapter = effects.ToolAdapter(unexpected)
    with pytest.raises(ExecutionError, match="live owned"):
        invoke(database, (replace(claim, token=uuid4()), attempt, version, credential), adapter)
    with Session(database) as db:
        run = db.get(WorkflowExecution, claim.execution_id)
        with workflow_transaction(db, run):
            db.get(StepAttempt, attempt).deadline_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(ExecutionError, match="deadline"):
        invoke(database, fixture, adapter)
    with Session(database) as db:
        assert db.scalars(select(ToolExecution)).all() == []


def test_new_logical_iteration_has_independent_effect_identity(database, monkeypatch):
    from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
    from src.services.execution_records import add_attempt, add_step
    from src.services.workflow_state import transition_execution_entity as transition
    from src.services.workflow_transactions import workflow_transaction

    fixture = setup(database, monkeypatch)
    keys = []

    def remote(**kw):
        keys.append(kw["effect_key"])
        return kw["arguments"]

    adapter = effects.ToolAdapter(remote)
    invoke(database, fixture, adapter)
    claim, attempt_id, version, credential = fixture
    # Exercise the ledger's logical-iteration boundary with explicit checkpoints;
    # graph-driven tool revision dispatch belongs to the adapter integration phase.
    with Session(database) as db:
        run = db.get(WorkflowExecution, claim.execution_id)
        attempt = db.get(StepAttempt, attempt_id)
        previous = db.get(StepRun, attempt.step_run_id)
        with workflow_transaction(db, run):
            transition(db, run, attempt, "completed")
            transition(db, run, previous, "completed")
        step = add_step(db, run, "action", iteration=1)
        attempt = add_attempt(db, run, step)
        with workflow_transaction(db, run):
            transition(db, run, step, "running")
            transition(db, run, attempt, "running")
            db.connection().execute(
                update(jobs).where(jobs.c.id == claim.id).values(attempt_id=attempt.id)
            )
        next_attempt = attempt.id
    invoke(database, (claim, next_attempt, version, credential), adapter)
    assert len(keys) == len(set(keys)) == 2


def test_revocation_between_reservation_and_dispatch_prevents_secret_use(database, monkeypatch):
    fixture = setup(database, monkeypatch, credential=True)
    claim, attempt, version, credential = fixture
    adapter = effects.ToolAdapter(lambda **kw: kw["arguments"])
    with Session(database) as db:
        identity, token, contract, _, _ = effects.reserve(
            db, claim, attempt, version, {"value": "one"}, "tool", {"http": adapter}
        )
    with Session(database) as db:
        catalog.set_active(db, ToolCredential, credential, False)
    with Session(database) as db:
        with pytest.raises(ExecutionError, match="credential is unavailable"):
            effects.dispatch(db, claim, attempt, identity, token, contract)
        assert not db.scalar(select(ToolExecution)).dispatched
        assert not any(a.action == "tool.credential.use" for a in db.scalars(select(AuditEvent)))


@pytest.mark.parametrize("outcome", ["absent", "unknown"])
def test_reconciliation_must_confirm_absence_before_another_write(database, monkeypatch, outcome):
    fixture = setup(database, monkeypatch)
    calls = []

    def remote(**kw):
        calls.append(kw["effect_key"])
        if len(calls) == 1:
            raise effects.ToolFailure("tool_timeout")
        return kw["arguments"]

    adapter = effects.ToolAdapter(remote, "reconcile", lambda **_: effects.Reconciliation(outcome))
    with pytest.raises(ExecutionError):
        invoke(database, fixture, adapter)
    if outcome == "absent":
        assert invoke(database, fixture, adapter) == {"value": "one"}
        assert len(calls) == 2 and calls[0] == calls[1]
    else:
        with pytest.raises(ExecutionError):
            invoke(database, fixture, adapter)
        assert len(calls) == 1
    with Session(database) as db:
        assert db.scalar(select(ToolExecution)).reconciliation["outcome"] == outcome


def test_abandoned_effect_remains_resolvable_after_worker_recovery_exhaustion(
    database, monkeypatch
):
    fixture = setup(database, monkeypatch)

    def lost(**_):
        raise SystemExit("Remote acceptance cannot be determined")

    with pytest.raises(SystemExit):
        invoke(database, fixture, effects.ToolAdapter(lost))
    monkeypatch.setattr(settings, "worker_max_recoveries", 0)
    expire(database, fixture[0])
    assert recover_claim(database, fixture[0])
    effects.recover_effects(database)
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        assert effect.status == "unknown"
        effects.resolve(
            db,
            effect.id,
            EffectResolution(
                succeeded=False, evidence="Fixture operator confirmed no remote effect"
            ),
        )
        assert effect.status == "reconciled" and effect.error_code == "tool_resolved_failed"


def test_credential_rotation_cannot_replay_an_ambiguous_effect(database, monkeypatch):
    fixture = setup(database, monkeypatch, credential=True)
    calls = []

    def lost(**kwargs):
        calls.append(kwargs["effect_key"])
        raise effects.ToolFailure("tool_timeout")

    adapter = effects.ToolAdapter(lost, "idempotent")
    with pytest.raises(ExecutionError):
        invoke(database, fixture, adapter)
    monkeypatch.setattr(
        settings,
        "tool_credential_values",
        {f"{DEFAULT_ORGANIZATION_ID}/fixture": SecretStr("different-account-credential")},
    )
    with pytest.raises(ExecutionError) as error:
        invoke(database, fixture, adapter)
    assert error.value.code == "tool_credential_changed" and len(calls) == 1
    with Session(database) as db:
        effect = db.scalar(select(ToolExecution))
        assert effect.status == "unknown"
        assert "credential_digest" not in catalog.public(effect)


def test_confirmed_receipt_is_retained_when_caller_is_aborted(database, monkeypatch):
    from src.services.execution_control import AbortSignal

    fixture = setup(database, monkeypatch)
    control = AbortSignal()

    def accepted(**kwargs):
        control.abort()
        return kwargs["arguments"]

    with pytest.raises(ExecutionError) as error:
        effects.execute_tool(
            database,
            fixture[0],
            fixture[1],
            fixture[2],
            {"value": "one"},
            adapters={"http": effects.ToolAdapter(accepted)},
            control=control,
        )
    assert error.value.code == "execution_aborted"
    with Session(database) as db:
        assert db.scalar(select(ToolExecution)).status == "succeeded"


def test_adapter_timeout_is_bounded_by_the_pinned_attempt_deadline(database, monkeypatch):
    fixture = setup(database, monkeypatch, timeout=120)

    def remote(**kwargs):
        assert 0 < kwargs["timeout_seconds"] <= 60
        return kwargs["arguments"]

    assert invoke(database, fixture, effects.ToolAdapter(remote)) == {"value": "one"}


def test_second_crash_before_reconciliation_retains_original_ambiguity(database, monkeypatch):
    from fastapi import HTTPException

    fixture = setup(database, monkeypatch)
    accepted = {}

    def remote(**kwargs):
        assert not accepted, "Recovery must reconcile the original accepted write"
        accepted[kwargs["effect_key"]] = kwargs["arguments"]
        raise SystemExit("First response lost")

    adapter = effects.ToolAdapter(
        remote,
        "reconcile",
        lambda **kw: effects.Reconciliation("succeeded", accepted[kw["effect_key"]]),
    )
    with pytest.raises(SystemExit):
        invoke(database, fixture, adapter)
    replacement = restart(database, fixture)
    claim, attempt, version, _ = replacement
    with Session(database) as db:
        identity, _, _, _, uncertain = effects.reserve(
            db, claim, attempt, version, {"value": "one"}, "tool", {"http": adapter}
        )
        assert uncertain and db.get(ToolExecution, identity).status == "unknown"
        with pytest.raises(HTTPException) as error:
            effects.resolve(
                db,
                identity,
                EffectResolution(
                    succeeded=True, result={"value": "one"}, evidence="Concurrent manual decision"
                ),
            )
        assert error.value.status_code == 409
    with pytest.raises(ExecutionError, match="already in progress"):
        invoke(database, replacement, adapter)
    # Replacement worker dies before it can perform its reconciliation lookup.
    final_owner = restart(database, replacement)
    assert invoke(database, final_owner, adapter) == {"value": "one"}
    assert len(accepted) == 1
