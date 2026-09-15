import os
import subprocess
import sys
import time
import uuid

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from alembic import command
from src.models.durable_job import DurableJob
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.services import durable_queue as queue
from src.services.worker_leases import recover_expired
from src.worker import run_worker
from tests.test_parallel_runtime import forked, graph
from tests.test_workflow_transactions_postgres import database as database


def test_killed_branch_recovers_without_overwriting_sibling_or_duplicating_join(database, tmp_path):
    payload = graph()
    payload["nodes"][1]["retry"] = {"max_attempts": 2, "initial_delay_seconds": 0}
    identity = forked(database, payload)
    claims = queue.claim_jobs(database, "branches", 2)
    with Session(database) as db:
        by_node = {db.get(DurableJob, claim.id).node_id: claim for claim in claims}
    assert queue.process_claim(database, by_node["right"])
    claim = by_node["left"]
    ready = tmp_path / "ready"
    schema = database.get_execution_options()["schema_translate_map"][None]
    script = """
import sys, time
from pathlib import Path
from uuid import UUID
from src.database import engine
from src.services.durable_queue import Claim, process_claim
from src.services.execution_registry import ExecutorRegistry
ready = Path(sys.argv[1])
claim = Claim(UUID(sys.argv[2]), UUID(sys.argv[3]), UUID(sys.argv[4]),
              int(sys.argv[5]), UUID(sys.argv[6]))
registry = ExecutorRegistry()
def blocked(value):
    ready.write_text('ready')
    time.sleep(60)
    return value
registry.handlers[('builtin.identity', 1)] = blocked
process_claim(engine, claim, registry)
"""
    env = {
        **os.environ,
        "DATABASE_URL": os.environ["WORKFLOW_TEST_DATABASE_URL"],
        "PGOPTIONS": f"-c search_path={schema}",
        "IDENTITY_ENABLED": "false",
        "WORKER_LEASE_SECONDS": "0.5",
        "WORKER_HEARTBEAT_SECONDS": "0.05",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            script,
            str(ready),
            str(claim.id),
            str(claim.organization_id),
            str(identity),
            str(claim.sequence),
            str(claim.token),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        limit = time.monotonic() + 15
        while not ready.exists() and process.poll() is None and time.monotonic() < limit:
            time.sleep(0.02)
        assert ready.exists(), "Child worker did not reach the branch I/O boundary"
        time.sleep(0.2)  # Observe a short child lease before killing this owned fixture process.
        process.kill()
        process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
    limit, recovered = time.monotonic() + 5, 0
    while not recovered and time.monotonic() < limit:
        recovered = recover_expired(database)
        time.sleep(0.02)
    assert recovered == 1
    assert not queue.process_claim(database, claim)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"left": 2, "right": 3}
        assert db.get(DurableJob, claim.id).recovery_count == 1
        steps = {step.node_id: step for step in db.scalars(select(StepRun))}
        for key, expected in [("left", 2), ("right", 1), ("join", 1)]:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(StepAttempt)
                    .where(StepAttempt.step_run_id == steps[key].id)
                )
                == expected
            )
        assert (
            db.scalar(
                select(StepAttempt).where(StepAttempt.error_code == "worker_abandoned")
            ).output_json
            is None
        )
        assert (
            db.scalar(
                select(func.count()).select_from(DurableJob).where(DurableJob.node_id == "join")
            )
            == 1
        )


def test_parallel_job_migration_preserves_linear_receipts_and_guards_history():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required")
    engine = create_engine(url)
    schema = "migration81_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.downgrade(config, "f080_execution_approvals")
            from tests.generic_migration_fixtures import pre_deadline_execution

            with Session(conn) as db:
                old = pre_deadline_execution(db)
            conn.execute(
                text("""INSERT INTO durable_jobs
                (id, organization_id, execution_id, sequence, status)
                SELECT gen_random_uuid(), organization_id, id, 0, 'queued' FROM workflow_executions
                WHERE id=:id"""),
                {"id": old},
            )
            conn.commit()
            command.upgrade(config, "head")
            assert conn.execute(
                text("SELECT node_id, iteration, branch FROM durable_jobs")
            ).one() == (None, 0, "main")
            conn.commit()
            scoped = engine.execution_options(schema_translate_map={None: schema})
            assert run_worker(scoped, drain=True, poll_seconds=0.01) == 0
            identity = forked(scoped)
            # Raw SQL also cannot retarget a queued branch receipt.
            with pytest.raises(Exception, match="identity and terminal history are immutable"):
                conn.execute(
                    text("""UPDATE durable_jobs SET branch='other'
                        WHERE execution_id=:id AND node_id IS NOT NULL"""),
                    {"id": identity},
                )
            conn.rollback()
            assert run_worker(scoped, capacity=2, drain=True, poll_seconds=0.01) == 0
            with pytest.raises(RuntimeError, match="Retain execution parallel history"):
                command.downgrade(config, "f080_execution_approvals")
            conn.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
