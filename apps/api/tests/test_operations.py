from datetime import timedelta
from threading import Event

import pytest
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from src.models.tenant import DEFAULT_ORGANIZATION_ID
from src.models.workflow_execution import ExecutionEvent, StepAttempt
from src.services import durable_queue as queue
from src.services import operations as ops
from src.services.execution_cancellation import cancel_execution
from src.services.execution_recovery import recover
from src.services.identity import Principal
from src.services.operations_pulse import pulse
from src.services.tenancy import bind_tenant
from src.services.worker_leases import recover_expired
from src.services.worker_presence import beat, presence, workers
from tests.test_durable_delays import graph as delay_graph
from tests.test_execution_recovery import drain
from tests.test_graph_interpreter import start
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_worker_leases import expire
from tests.test_workflow_transactions_postgres import database as database


def snapshot(database, owner=DEFAULT_ORGANIZATION_ID):
    with database.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        return ops.snapshot(conn, owner)


def test_claim_recovery_completion_totals_match_persisted_history(database):
    with Session(database) as db:
        identity = start(db).id
    assert snapshot(database)["claims"] == 0
    claim = queue.claim_jobs(database, "first-private-host")[0]
    beat(database, "first-private-host", 3)
    initial = snapshot(database)
    assert initial["claims"] == initial["jobs"]["running"] == 1
    assert initial["workers"] == {"running": 1}
    assert initial["queue_wait"]["samples"] == 1
    expire(database, claim)
    assert snapshot(database)["jobs"]["stale"] == 1
    assert recover_expired(database) == 1
    retry = snapshot(database)
    assert retry["jobs"]["retrying"] == retry["lease_recoveries"] == 1
    drain(database)
    result = snapshot(database)
    with Session(database) as db:
        assert result["claims"] == db.scalar(
            select(func.count())
            .select_from(
                ExecutionEvent,
            )
            .where(
                ExecutionEvent.entity_type == "durable_jobs", ExecutionEvent.to_status == "running"
            )
        )
        assert (
            sum(result["attempts"].values())
            == db.scalar(
                select(func.count()).select_from(StepAttempt),
            )
            == 4
        )
        assert pulse(db, "execution", identity)["terminal"]
    assert result["completed_in_window"] == result["runs"]["completed"] == 1
    assert result["queue_wait"]["samples"] == result["claims"]
    exported = ops.prometheus(result)
    assert "first-private-host" not in exported and str(identity) not in exported
    # Four node attempts plus a terminal checkpoint, and one abandoned claim.
    assert "agentops_claims 6" in exported


def test_dead_letter_abandonment_and_recovery_are_distinct(database, monkeypatch):
    with Session(database) as db:
        identity = start(db).id
    claim = queue.claim_jobs(database, "crashed")[0]
    with monkeypatch.context() as patch:

        def crash(*_):
            raise RuntimeError("Controlled crash")

        patch.setattr(queue, "execute_work", crash)
        with pytest.raises(RuntimeError):
            queue.process_claim(database, claim)
    expire(database, claim)
    recover_expired(database)
    result = snapshot(database)
    assert result["jobs"]["dead_letter"] == result["abandoned_attempts"] == 1
    assert result["attempts"] == {"failed": 1}
    with Session(database) as db:
        recover(db, identity, "Explicit linked recovery")
    drain(database)
    assert snapshot(database)["linked_recoveries"] == 1
    with database.connect() as conn:
        assert (
            ops.job_page(conn, DEFAULT_ORGANIZATION_ID, "dead_letter")["items"][0]["id"] == claim.id
        )
        page = ops.job_page(conn, DEFAULT_ORGANIZATION_ID, limit=1)
        assert page["next_offset"] == 1
        assert "claim_token" not in page["items"][0]


def test_waits_and_change_tokens_do_not_count_as_active_jobs(database):
    with Session(database) as db:
        identity = start(db, delay_graph(), {}).id
        before = pulse(db, "execution", identity)
    drain(database)
    result = snapshot(database)
    assert result["waiting_steps"] == 1
    assert result["jobs"].get("running", 0) == 0
    with Session(database) as db:
        waiting = pulse(db, "execution", identity)
        assert waiting["token"] != before["token"] and waiting["interval_ms"] == 15000
        assert not waiting["terminal"]
        cancel_execution(db, identity, "End wait fixture")
        assert pulse(db, "execution", identity)["terminal"]


def test_worker_expiry_stop_and_global_visibility(database):
    beat(database, "idle-private-host", 4)
    assert snapshot(database)["workers"] == {}
    assert snapshot(database, None)["workers"] == {"running": 1}
    with database.begin() as conn:
        conn.execute(update(workers).values(expires_at=func.now() - timedelta(seconds=1)))
    assert snapshot(database, None)["workers"] == {}
    with presence(database, "owned", 2, Event()):
        assert snapshot(database, None)["workers"] == {"running": 1}
    beat(database, "owned", 2)  # A late heartbeat cannot resurrect a stopped worker.
    assert snapshot(database, None)["workers"] == {}


def test_operations_api_never_exposes_other_tenants(database, tenants, tenant_client):
    ids = []
    for owner in tenants:
        actor = prepare(database, owner)
        with Session(database) as db:
            bind_tenant(db, owner["org"])
            db.info["principal"] = Principal("admin", actor, owner["org"])
            ids.append(start(db).id)
    response = tenant_client.get("/operations")
    assert response.status_code == 200
    assert response.json()["jobs"]["queued"] == 1
    page = tenant_client.get("/operations/jobs").json()
    assert [row["execution_id"] for row in page["items"]] == [str(ids[0])]
    assert str(ids[1]) not in str(page)
    assert tenant_client.get("/operations/jobs?limit=51").status_code == 422
    assert tenant_client.get("/operations/jobs?kind=secret").status_code == 422
    assert (
        tenant_client.get(f"/operations/pulse?kind=execution&identity={ids[1]}").status_code == 404
    )
    assert (
        tenant_client.get(f"/operations/pulse?kind=execution&identity={ids[0]}").status_code == 200
    )
    metrics = tenant_client.get("/operations/metrics")
    assert metrics.status_code == 200 and 'agentops_jobs{status="queued"} 1' in metrics.text
    assert str(tenants[1]["org"]) not in metrics.text and "secret" not in metrics.text
    tenant_client.headers.pop("authorization")
    assert tenant_client.get("/operations").status_code == 401
    assert tenant_client.get("/operations/metrics").status_code == 401


def test_foreign_worker_presence_and_approval_pulses_stay_private(database, tenants, tenant_client):
    owner = tenants[1]
    actor = prepare(database, owner)
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        db.info["principal"] = Principal("admin", actor, owner["org"])
        start(db)
    queue.claim_jobs(database, "private-other-tenant-host")
    beat(database, "private-other-tenant-host", 32)
    data = tenant_client.get("/operations").json()
    assert sum(data["jobs"].values()) == 0 and data["workers"] == {}
    assert data["claims"] == sum(data["attempts"].values()) == 0
    assert snapshot(database, None)["workers"] == {"running": 1}
    other, own = owner["approval"], tenants[0]["approval"]
    base = "/operations/pulse?kind=approval&identity="
    assert tenant_client.get(base + str(other)).status_code == 404
    result = tenant_client.get(base + str(own))
    assert result.status_code == 200 and result.json()["terminal"]
    metrics = tenant_client.get("/operations/metrics?organization_id=" + str(owner["org"])).text
    assert "private-other-tenant-host" not in metrics and "agentops_claims 0" in metrics


def test_snapshot_reuses_a_bounded_connection_pool(database):
    from src.routers.operations import summary

    engine = create_engine(database.url, pool_size=1, max_overflow=0, pool_timeout=0.2)
    scoped = engine.execution_options(**database.get_execution_options())
    try:
        with Session(scoped) as db:
            db.scalar(select(1))  # The request already owns an authorization connection.
            assert summary(db)["claims"] == 0
            assert db.connection().get_isolation_level() == "REPEATABLE READ"
    finally:
        engine.dispose()


def test_live_legacy_list_pagination_and_run_filter_stay_scoped(database, tenants, tenant_client):
    from src.models.human_approval import HumanApproval

    owner = tenants[0]
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        db.add_all([HumanApproval(workflow_run_id=owner["run"]) for _ in range(28)])
        db.commit()
    page1 = tenant_client.get("/human-approvals?limit=26&offset=0").json()
    page2 = tenant_client.get("/human-approvals?limit=26&offset=26").json()
    assert len(page1) == 26 and len(page2) == 3
    assert not ({row["id"] for row in page1} & {row["id"] for row in page2})
    for path in ("/human-approvals", "/workflow-runs"):
        assert tenant_client.get(path + "?limit=51").status_code == 422
        assert tenant_client.get(path + "?limit=1&offset=-1").status_code == 422
    rows = tenant_client.get("/workflow-runs?limit=1&offset=0").json()
    assert len(rows) == 1 and rows[0]["id"] == str(owner["run"])
    assert tenant_client.get("/workflow-runs?limit=1&offset=1").json() == []
    path = "/human-approvals?limit=1&status=pending&workflow_run_id="
    assert len(tenant_client.get(path + str(owner["run"])).json()) == 1
    assert tenant_client.get(path + str(tenants[1]["run"])).json() == []
