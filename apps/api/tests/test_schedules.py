import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.durable_job import DurableJob
from src.models.identity import ServicePrincipal, User
from src.models.schedule import ScheduleFire
from src.models.tenant import DEFAULT_ORGANIZATION_ID
from src.models.workflow_execution import WorkflowExecution
from src.schemas.schedule import ScheduleCreate, ScheduleUpdate
from src.schemas.workflow_definition import DefinitionUpdate
from src.services import execution_starts, schedules, workflow_definitions
from src.services.execution_deadlines import enforce_deadlines
from src.services.identity import Principal
from src.services.tenancy import bind_tenant, tenant_id
from src.worker import run_worker
from tests.test_execution_starts import count, definition
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_graph import NUMBER, obj
from tests.test_workflow_transactions_postgres import database as database

BASE = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def clock(monkeypatch):
    value = [BASE]
    monkeypatch.setattr(schedules, "runtime_now", lambda _: value[0])
    return value


def setup(db, **updates):
    owner = tenant_id(db)
    user = User(
        issuer="schedule-fixture", subject=str(uuid.uuid4()), display_name="Timer", kind="service"
    )
    db.add(user)
    db.flush()
    principal = ServicePrincipal(
        user_id=user.id, organization_id=owner, role="operator", scopes=["workflow.start"]
    )
    db.add(principal)
    db.flush()
    item = definition(db)
    data = dict(
        name="Timer",
        definition_id=item.id,
        service_principal_id=principal.id,
        cron="* * * * *",
        timezone="UTC",
        input={"value": 1},
    )
    data.update(updates)
    return schedules.create(db, ScheduleCreate(**data))


def edit(db, item, **updates):
    data = {name: getattr(item, name) for name in ScheduleCreate.model_fields}
    data.update(expected_revision=item.revision, **updates)
    return schedules.update(db, item.id, ScheduleUpdate(**data))


def test_replicas_accept_one_fire_and_run_then_complete_in_worker(database, clock):
    with Session(database) as db:
        item = setup(db)
        identity, due = item.id, item.next_fire_at
    barrier = Barrier(3)

    def fire(_):
        barrier.wait(timeout=10)
        return schedules.fire_due_schedules(database, now=due)

    with ThreadPoolExecutor(max_workers=3) as pool:
        assert sum(pool.map(fire, range(3))) == 1
    with Session(database) as db:
        assert count(db, ScheduleFire) == count(db, WorkflowExecution) == count(db, DurableJob) == 1
        receipt = db.scalar(select(ScheduleFire))
        actor = db.get(ServicePrincipal, receipt.service_principal_id)
        assert db.get(WorkflowExecution, receipt.execution_id).created_by_user_id == actor.user_id
        assert schedules.get_schedule(db, identity).next_fire_at > due
    assert schedules.fire_due_schedules(database, now=due) == 0
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.scalar(select(WorkflowExecution)).status == "completed"


def test_downtime_coalesces_once_and_active_work_suppresses_overlap(database, clock):
    with Session(database) as db:
        identity = setup(db).id
    later = BASE + timedelta(days=10)
    assert schedules.fire_due_schedules(database, now=later) == 1
    assert schedules.fire_due_schedules(database, now=later) == 0
    assert schedules.fire_due_schedules(database, now=later + timedelta(minutes=1)) == 1
    with Session(database) as db:
        receipts = db.scalars(select(ScheduleFire).order_by(ScheduleFire.scheduled_at)).all()
        assert [r.status for r in receipts] == ["accepted", "skipped"]
        assert receipts[0].coalesced and receipts[1].error_code == "active_run"
        assert count(db, WorkflowExecution) == 1
        assert schedules.get_schedule(db, identity).next_fire_at == later + timedelta(minutes=2)


def test_pause_resume_and_routing_edits_reset_pending_tick(database, clock):
    with Session(database) as db:
        item = setup(db)
        identity, original_due = item.id, item.next_fire_at
        edit(db, item, enabled=False)
    clock[0] += timedelta(days=2)
    assert schedules.fire_due_schedules(database, now=clock[0]) == 0
    with Session(database) as db:
        item = edit(db, schedules.get_schedule(db, identity), enabled=True)
        assert item.next_fire_at == original_due
    assert schedules.fire_due_schedules(database, now=clock[0]) == 1
    with Session(database) as db:
        assert db.scalar(select(ScheduleFire)).coalesced
        item = schedules.get_schedule(db, identity)
        previous = item.next_fire_at
        clock[0] += timedelta(days=1)
        item = edit(db, item, input={"value": 2})
        assert item.next_fire_at > clock[0] > previous
        stale = {name: getattr(item, name) for name in ScheduleCreate.model_fields}
        with pytest.raises(HTTPException) as error:
            schedules.update(db, identity, ScheduleUpdate(**stale, expected_revision=1))
        assert error.value.status_code == 409


@pytest.mark.parametrize("pinned", [False, True])
def test_version_selection_is_retained_in_fire_history(database, clock, pinned):
    with Session(database) as db:
        item = setup(db)
        identity, due = item.id, item.next_fire_at
        target = workflow_definitions.definition(db, item.definition_id)
        old = target.published_version_id
        if pinned:
            edit(db, item, version_policy="pinned", version_id=old)
        newer = workflow_definitions.publish(db, target.id, target.draft_revision).id
    assert schedules.fire_due_schedules(database, now=due) == 1
    with Session(database) as db:
        receipt = db.scalar(select(ScheduleFire))
        assert receipt.version_id == (old if pinned else newer)
        target = workflow_definitions.definition(
            db, schedules.get_schedule(db, identity).definition_id
        )
        workflow_definitions.archive(db, target.id, target.draft_revision)
    assert schedules.fire_due_schedules(database, now=due) == 0
    with Session(database) as db:
        assert count(db, ScheduleFire) == 1


@pytest.mark.parametrize("change", ["scope", "principal", "user", "archive"])
def test_revoked_or_unavailable_targets_retain_rejection_without_jobs(database, clock, change):
    with Session(database) as db:
        item = setup(db)
        due = item.next_fire_at
        principal = db.get(ServicePrincipal, item.service_principal_id)
        if change == "scope":
            principal.scopes = []
        elif change == "principal":
            principal.active = False
        elif change == "user":
            db.get(User, principal.user_id).active = False
        else:
            target = workflow_definitions.definition(db, item.definition_id)
            workflow_definitions.archive(db, target.id, target.draft_revision)
        db.commit()
    assert schedules.fire_due_schedules(database, now=due) == 1
    with Session(database) as db:
        assert count(db, WorkflowExecution) == count(db, DurableJob) == 0
        receipt = db.scalar(select(ScheduleFire))
        assert receipt.status == "rejected"
        assert receipt.error_code == (
            "workflow_unavailable" if change == "archive" else "principal_unavailable"
        )


def test_atomic_failure_leaves_original_tick_available(database, clock, monkeypatch):
    with Session(database) as db:
        item = setup(db)
        identity, due = item.id, item.next_fire_at
    enqueue = execution_starts.enqueue

    def fail(*args, **kwargs):
        enqueue(*args, **kwargs)
        raise RuntimeError("injected after queue insertion")

    monkeypatch.setattr(execution_starts, "enqueue", fail)
    with pytest.raises(RuntimeError, match="injected"):
        schedules.fire_schedule(database, identity, DEFAULT_ORGANIZATION_ID, now=due)
    with Session(database) as db:
        assert count(db, ScheduleFire) == count(db, WorkflowExecution) == count(db, DurableJob) == 0
        assert schedules.get_schedule(db, identity).next_fire_at == due
    monkeypatch.setattr(execution_starts, "enqueue", enqueue)
    assert schedules.fire_due_schedules(database, now=due) == 1


def test_process_crash_after_enqueue_rolls_back_the_entire_fire(database, clock):
    with Session(database) as db:
        item = setup(db)
        identity, due = item.id, item.next_fire_at
    schema = database.get_execution_options()["schema_translate_map"][None]
    script = """
import os, sys, uuid
from datetime import datetime
from src.database import engine
from src.services import execution_starts, schedules
original = execution_starts.enqueue
def crash(db, *args, **kwargs):
    original(db, *args, **kwargs)
    db.flush()
    os._exit(23)
execution_starts.enqueue = crash
schedules.fire_schedule(engine, uuid.UUID(sys.argv[1]), uuid.UUID(sys.argv[2]),
                        now=datetime.fromisoformat(sys.argv[3]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(identity),
            str(DEFAULT_ORGANIZATION_ID),
            due.isoformat(),
        ],
        env={
            **os.environ,
            "DATABASE_URL": os.environ["WORKFLOW_TEST_DATABASE_URL"],
            "PGOPTIONS": f"-c search_path={schema}",
            "IDENTITY_ENABLED": "false",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 23, result.stderr
    with Session(database) as db:
        assert count(db, ScheduleFire) == count(db, WorkflowExecution) == count(db, DurableJob) == 0
        assert schedules.get_schedule(db, identity).next_fire_at == due
    assert schedules.fire_due_schedules(database, now=due) == 1
    assert schedules.fire_due_schedules(database, now=due) == 0


def test_failed_candidate_does_not_block_other_candidates_or_log_payload(
    database, clock, monkeypatch, caplog
):
    with Session(database) as db:
        bad = setup(db)
        bad_id, bad_definition, due = bad.id, bad.definition_id, bad.next_fire_at
        good_id = setup(db).id
    original = schedules.start_execution

    def fail(db, body, **kwargs):
        if body.definition_id == bad_definition:
            raise RuntimeError("private payload must not enter logs")
        return original(db, body, **kwargs)

    monkeypatch.setattr(schedules, "start_execution", fail)
    assert schedules.fire_due_schedules(database, now=due) == 1
    assert str(bad_id) in caplog.text and "private payload" not in caplog.text
    with Session(database) as db:
        assert schedules.get_schedule(db, bad_id).next_fire_at == due
        assert schedules.get_schedule(db, good_id).last_status == "accepted"
    monkeypatch.setattr(schedules, "start_execution", original)
    assert schedules.fire_due_schedules(database, now=due) == 1


def test_due_boundary_and_expired_active_run(database, clock):
    with Session(database) as db:
        item = setup(db)
        due = item.next_fire_at
    assert schedules.fire_due_schedules(database, now=due - timedelta(microseconds=1)) == 0
    assert schedules.fire_due_schedules(database, now=due) == 1
    with Session(database) as db:
        deadline = db.scalar(select(WorkflowExecution)).deadline_at
    enforce_deadlines(database, now=deadline)
    assert schedules.fire_due_schedules(database, now=deadline) == 1
    with Session(database) as db:
        assert count(db, WorkflowExecution) == 2
        assert db.scalars(select(ScheduleFire.status)).all() == ["accepted", "accepted"]


def test_input_is_validated_on_configuration_and_again_after_publication(database, clock):
    with Session(database) as db:
        item = setup(db)
        due = item.next_fire_at
        with pytest.raises(HTTPException) as error:
            edit(db, item, input={"value": "invalid"})
        assert error.value.status_code == 422
        db.rollback()
        target = workflow_definitions.definition(db, item.definition_id)
        graph = {**target.draft_graph, "input_schema": obj(other=NUMBER)}
        target = workflow_definitions.update_draft(
            db,
            target.id,
            DefinitionUpdate(
                name=target.name, graph=graph, expected_revision=target.draft_revision
            ),
        )
        workflow_definitions.publish(db, target.id, target.draft_revision)
    assert schedules.fire_due_schedules(database, now=due) == 1
    with Session(database) as db:
        receipt = db.scalar(select(ScheduleFire))
        assert receipt.status == "rejected" and receipt.error_code == "input_invalid"
        assert count(db, WorkflowExecution) == count(db, DurableJob) == 0


def test_schedule_api_admin_scope_and_tenant_history(database, clock, tenants, tenant_client):
    actor = prepare(database, tenants[0])
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        db.info["principal"] = Principal("admin", actor, tenants[0]["org"])
        item = setup(db)
        identity, due = item.id, item.next_fire_at
        data = ScheduleCreate(**{name: getattr(item, name) for name in ScheduleCreate.model_fields})
        body = data.model_dump(mode="json")
    created = tenant_client.post("/workflow-schedules", json=body)
    assert created.status_code == 201
    saved = created.json()
    assert saved["revision"] == 1 and saved["cron"] == body["cron"]
    assert saved["next_fire_at"] and saved["service_principal_id"] == body["service_principal_id"]
    updated = tenant_client.put(
        f"/workflow-schedules/{saved['id']}",
        json={**body, "name": "Renamed schedule", "expected_revision": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert updated.json()["name"] == "Renamed schedule"
    assert tenant_client.get(f"/workflow-schedules/{saved['id']}").json() == updated.json()
    assert schedules.fire_due_schedules(database, now=due) == 2
    response = tenant_client.get(f"/workflow-schedules/{identity}/fires")
    assert response.status_code == 200 and len(response.json()) == 1
    prepare(database, tenants[0], "operator")
    assert tenant_client.post("/workflow-schedules", json=body).status_code == 403
    with Session(database) as db:
        bind_tenant(db, tenants[1]["org"])
        with pytest.raises(HTTPException) as error:
            schedules.get_schedule(db, identity)
        assert error.value.status_code == 404
        with pytest.raises(HTTPException):
            schedules.validate_target(db, data)


@pytest.mark.parametrize("change", ["publish", "revoke", "disable"])
def test_firing_serializes_with_publication_revocation_and_configuration(database, clock, change):
    with Session(database) as db:
        item = setup(db)
        identity, due = item.id, item.next_fire_at
        definition_id, principal_id = item.definition_id, item.service_principal_id
        old_version = workflow_definitions.definition(db, definition_id).published_version_id
    barrier = Barrier(2)

    def fire():
        barrier.wait(timeout=10)
        return schedules.fire_schedule(database, identity, DEFAULT_ORGANIZATION_ID, now=due)

    def change_target():
        with Session(database) as db:
            barrier.wait(timeout=10)
            if change == "publish":
                item = workflow_definitions.definition(db, definition_id)
                return workflow_definitions.publish(db, item.id, item.draft_revision).id
            if change == "revoke":
                db.get(ServicePrincipal, principal_id).active = False
                db.commit()
            else:
                edit(db, schedules.get_schedule(db, identity), enabled=False)
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        fired, changed = pool.submit(fire), pool.submit(change_target)
        processed, new_version = fired.result(), changed.result()
    with Session(database) as db:
        receipt = db.scalar(select(ScheduleFire))
        assert count(db, ScheduleFire) == int(processed)
        accepted = receipt is not None and receipt.status == "accepted"
        assert count(db, WorkflowExecution) == count(db, DurableJob) == int(accepted)
        if change == "publish":
            assert receipt.version_id in {old_version, new_version}
        elif change == "disable":
            assert not schedules.get_schedule(db, identity).enabled
        elif not accepted:
            assert receipt.error_code == "principal_unavailable"
