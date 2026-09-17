"""Reproducible real PostgreSQL/process/HTTP failures with per-identity evidence."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.config import settings
from src.models.durable_job import DurableJob
from src.models.execution_approval import ExecutionApproval
from src.models.schedule import ScheduleFire
from src.models.tool import ToolExecution
from src.models.workflow_definition import WorkflowVersion
from src.models.workflow_execution import WorkflowExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.tool import EffectResolution
from src.services import durable_queue as queue
from src.services import schedules, tool_effects
from src.services import worker_leases as leases
from src.services.execution_cancellation import cancel_execution
from src.services.execution_recovery import controls, recover
from src.services.execution_starts import start_execution
from src.services.workflow_transactions import StaleWorkflowError
from src.worker import run_worker
from tests.reliability_evidence import evidence as evidence
from tests.reliability_evidence import reconcile
from tests.reliability_fixtures import outage_database, wait_for
from tests.reliability_fixtures import sink as sink
from tests.test_execution_approvals import decision, pending
from tests.test_graph_interpreter import branching_graph, start
from tests.test_http_tool_runtime import approve
from tests.test_http_tool_runtime import fixture as http_fixture
from tests.test_parallel_runtime import forked
from tests.test_schedules import clock as clock
from tests.test_schedules import setup as schedule_setup
from tests.test_worker_leases import expire, retry_graph
from tests.test_workflow_transactions_postgres import database as database


@contextmanager
def process(database, root, boundary):
    root.mkdir()
    schema = database.get_execution_options()["schema_translate_map"][None]
    env = {
        **os.environ,
        "DATABASE_URL": os.environ["WORKFLOW_TEST_DATABASE_URL"],
        "PGOPTIONS": f"-c search_path={schema}",
        "ENVIRONMENT": "development",
        "IDENTITY_ENABLED": "false",
        "OPENAI_API_KEY": "",
        "WORKER_LEASE_SECONDS": "1",
        "WORKER_HEARTBEAT_SECONDS": "0.05",
    }
    child = subprocess.Popen(
        [sys.executable, "-m", "tests.reliability_worker", boundary, str(root)],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for(lambda: (root / "ready").exists() or child.poll() is not None)
        assert child.poll() is None, child.communicate(timeout=5)
        yield child
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)


def drain(database, capacity=2):
    assert run_worker(database, capacity=capacity, drain=True, poll_seconds=0.02) == 0


@pytest.mark.parametrize(
    "boundary,exhaust", [("before", False), ("during", False), ("after", False), ("during", True)]
)
def test_process_death_and_dead_letter(database, evidence, tmp_path, boundary, exhaust):
    with Session(database) as db:
        identity = start(db, branching_graph() if exhaust else retry_graph()).id
    evidence.accept(identity)
    evidence.mark("accepted")
    with process(database, tmp_path / "worker", boundary) as child:
        evidence.mark("worker_at_boundary", boundary=boundary, pid=child.pid)
        since = evidence.mark("kill_requested", capture=False)
        child.kill()
        child.communicate(timeout=10)
        evidence.mark("worker_dead", returncode=child.returncode)
    if boundary != "after":
        wait_for(lambda: leases.recover_expired(database) == 1, 10)
    drain(database)
    expected = {identity: "completed"}
    if exhaust:
        with Session(database) as db:
            assert db.get(WorkflowExecution, identity).error_code == "recovery_exhausted"
        evidence.mark("dead_letter_retained")
        with Session(database) as db:
            child_id = recover(db, identity, "Phase 99 explicit dead-letter recovery").id
        evidence.accept(child_id)
        drain(database)
        expected = {identity: "failed", child_id: "completed"}
    evidence.finish(expected, since=since)


def test_expired_parallel_claim_duplicate_delivery_and_join(database, evidence):
    identity = forked(database)
    evidence.accept(identity)
    claims = queue.claim_jobs(database, "two-branches", 2)
    assert len(claims) == 2
    evidence.mark("branches_claimed")
    since = evidence.mark("lease_expired", capture=False)
    expire(database, claims[0])
    barrier = Barrier(2)

    def reclaim(_):
        barrier.wait(timeout=10)
        return leases.recover_claim(database, claims[0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(reclaim, range(2))) == 1
    assert not queue.process_claim(database, claims[0])
    assert queue.process_claim(database, claims[1])
    assert not queue.process_claim(database, claims[1])
    drain(database)
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"left": 2, "right": 3}
        assert (
            db.scalar(
                select(func.count()).select_from(DurableJob).where(DurableJob.node_id == "join")
            )
            == 1
        )
    evidence.finish(
        {identity: "completed"},
        since=since,
        duplicate_deliveries_prevented=2,
        competing_reclaims_prevented=1,
    )
    broken = deepcopy(evidence.record)
    broken["frames"][-1]["state"]["jobs"].pop()
    with pytest.raises(AssertionError, match="admission mismatch"):
        reconcile(broken)


@pytest.mark.parametrize("idempotent,resolve", [(True, False), (False, False), (False, True)])
def test_timeout_after_effect(database, evidence, sink, monkeypatch, idempotent, resolve):
    identity, *_ = http_fixture(
        database,
        sink,
        monkeypatch,
        write=True,
        path="/timeout",
        idempotent=idempotent,
        timeout_seconds=0.2,
    )
    evidence.accept(identity, {"value": "one"})
    approve(database)
    since = evidence.mark("approved_before_timeout")
    drain(database)
    evidence.mark("after_timeout_and_automatic_recovery")
    expected = {identity: "completed" if idempotent else "failed"}
    unknown = int(not idempotent)
    if not idempotent:
        with Session(database) as db:
            assert db.scalar(select(ToolExecution)).status == "unknown"
            assert not controls(db, identity)["can_recover"]
            with pytest.raises(HTTPException):
                recover(db, identity, "Must not replay an unresolved write")
        assert len(sink.calls) == 1
    if resolve:
        evidence.mark("unknown_blocks_recovery")
        with Session(database) as db:
            effect = db.scalar(select(ToolExecution))
            tool_effects.resolve(
                db,
                effect.id,
                EffectResolution(
                    succeeded=True,
                    result={"status": 200, "body": {"value": "one"}},
                    evidence="Observed the single write in this disposable Phase 99 sink",
                ),
            )
            child_id = recover(db, identity, "Verified sink receipt; request fresh approval").id
        evidence.accept(child_id)
        drain(database)
        with Session(database) as db:
            gate = db.scalar(
                select(ExecutionApproval).where(
                    ExecutionApproval.execution_id == child_id,
                    ExecutionApproval.status == "pending",
                )
            )
            decision_id, payload_hash = gate.id, gate.payload_hash
        decision(database, decision_id, payload_hash)
        drain(database)
        expected[child_id], unknown = "completed", 0
        assert len(sink.calls) == 1
    evidence.finish(expected, since=since, sink=sink, idempotent=idempotent, unknown=unknown)


def test_crash_between_effect_and_receipt(database, evidence, sink, monkeypatch):
    identity, *_ = http_fixture(
        database, sink, monkeypatch, write=True, path="/write", idempotent=True
    )
    evidence.accept(identity, {"value": "one"})
    approve(database)
    claim = queue.claim_jobs(database, "receipt-loss")[0]
    since = evidence.mark("before_injected_receipt_commit_loss")

    def interrupted(*args, **kwargs):
        raise SystemExit("Injected process-loss boundary before receipt commit")

    with monkeypatch.context() as patch:
        patch.setattr(tool_effects, "finish", interrupted)
        with pytest.raises(SystemExit):
            queue.process_claim(database, claim)
    assert len(sink.effects) == 1
    evidence.mark("effect_observed_receipt_pending")
    expire(database, claim)
    assert leases.recover_claim(database, claim)
    drain(database)
    evidence.finish({identity: "completed"}, since=since, sink=sink)


@pytest.mark.parametrize("iteration", range(3))
def test_approval_cancel_race(database, evidence, iteration):
    identity, approval_id, payload_hash = pending(database)
    evidence.accept(identity)
    since = evidence.mark("approval_wait_before_race", iteration=iteration)
    barrier = Barrier(2)

    def compete(action):
        barrier.wait(timeout=10)
        try:
            if action == "approve":
                decision(database, approval_id, payload_hash)
            else:
                with Session(database) as db:
                    cancel_execution(db, identity, "Phase 99 approval/cancel race")
            return "committed"
        except (HTTPException, StaleWorkflowError):
            assert action == "approve"
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(compete, ["approve", "cancel"]))
    drain(database)
    evidence.finish({identity: "cancelled"}, since=since, decision_outcomes=outcomes)


def test_scheduler_replica_race(database, evidence, clock):
    with Session(database) as db:
        due = schedule_setup(db).next_fire_at
    since = evidence.mark("before_three_scheduler_replicas")
    barrier = Barrier(3)

    def fire(_):
        barrier.wait(timeout=10)
        return schedules.fire_due_schedules(database, now=due)

    with ThreadPoolExecutor(max_workers=3) as pool:
        assert sum(pool.map(fire, range(3))) == 1
    with Session(database) as db:
        receipt = db.scalar(select(ScheduleFire))
        identity = receipt.execution_id
        assert db.scalar(select(func.count()).select_from(ScheduleFire)) == 1
    evidence.accept(identity)
    assert schedules.fire_due_schedules(database, now=due) == 0
    drain(database)
    evidence.finish({identity: "completed"}, since=since, duplicate_schedule_fires_prevented=3)


def test_overlapping_graceful_worker_replacement(database, evidence, tmp_path):
    with Session(database) as db:
        identities = [start(db, retry_graph()).id for _ in range(8)]
    for identity in identities:
        evidence.accept(identity)
    old_root, new_root = tmp_path / "old", tmp_path / "new"
    with process(database, old_root, "rolling") as old:
        since = evidence.mark("old_worker_busy", pid=old.pid)
        with process(database, new_root, "replacement") as replacement:
            old.stdin.write("stop\n")
            old.stdin.flush()
            wait_for(lambda: (old_root / "stop-requested").exists())
            (old_root / "release").write_text("complete the in-flight checkpoint")
            _, errors = old.communicate(timeout=30)
            assert old.returncode == 0, errors

            def completed():
                with Session(database) as db:
                    return all(
                        db.get(WorkflowExecution, key).status == "completed" for key in identities
                    )

            wait_for(completed, 60)
            replacement.stdin.write("stop\n")
            replacement.stdin.flush()
            _, errors = replacement.communicate(timeout=30)
            assert replacement.returncode == 0, errors
            evidence.mark("both_workers_drained", old_pid=old.pid, new_pid=replacement.pid)
    with Session(database) as db:
        assert sum(db.scalars(select(DurableJob.recovery_count))) == 0
    evidence.finish(dict.fromkeys(identities, "completed"), since=since, workers_replaced=1)


def test_real_database_service_outage(evidence, monkeypatch):
    with outage_database() as (database, owned, ready, infrastructure):
        evidence.database = database
        monkeypatch.setattr(settings, "worker_lease_seconds", 0.5)
        monkeypatch.setattr(settings, "worker_heartbeat_seconds", 0.05)
        with Session(database) as db:
            identity = start(db, retry_graph()).id
            version_id = db.get(WorkflowExecution, identity).version_id
            definition_id = db.get(WorkflowVersion, version_id).definition_id
        evidence.accept(identity)
        claim = queue.claim_jobs(database, "lost-database-owner")[0]
        since = evidence.mark("database_stop_requested", **infrastructure)
        owned("stop")
        try:
            with pytest.raises(OperationalError):
                with Session(database) as db:
                    start_execution(
                        db,
                        ExecutionStartRequest(
                            definition_id=definition_id,
                            input={"value": 7},
                            idempotency_key="outage",
                        ),
                    )
            with pytest.raises(OperationalError):
                run_worker(database, drain=True, poll_seconds=0.02)
            evidence.mark("database_unavailable_admission_and_worker_failed", capture=False)
        finally:
            owned("start")
            database.dispose()
            wait_for(ready, 60)
        evidence.mark("database_ready")
        assert not leases.renew_lease(database, claim)
        assert leases.recover_expired(database) == 1
        drain(database)
        evidence.finish({identity: "completed"}, since=since, unaccepted_outage_requests=1)
