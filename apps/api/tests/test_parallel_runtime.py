import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event, Lock

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.durable_job import DurableJob
from src.models.execution_approval import ExecutionApproval
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.services import durable_queue as queue
from src.services.delay_runtime import wake_due_delays
from src.services.execution_cancellation import cancel_execution
from src.services.execution_deadlines import enforce_deadlines
from src.services.execution_registry import ExecutorRegistry
from src.services.graph_expressions import ExecutionError
from src.services.workflow_transactions import StaleWorkflowError
from src.worker import run_worker
from tests.test_execution_approvals import decision
from tests.test_execution_approvals import graph as approval_graph
from tests.test_execution_approvals import inputs as approval_inputs
from tests.test_graph_interpreter import start
from tests.test_workflow_graph import NUMBER, code, edge, literal, obj, ref
from tests.test_workflow_transactions_postgres import database as database


def graph():
    return {
        "entry_node": "fork",
        "output_schema": obj(left=NUMBER, right=NUMBER),
        "outputs": {"left": ref("left", "join"), "right": ref("right", "join")},
        "nodes": [
            {
                "id": "fork",
                "type": "parallel",
                "config": {
                    "mode": "fork",
                    "join_node": "join",
                    "branches": [
                        {"name": "left", "entry_node": "left"},
                        {"name": "right", "entry_node": "right"},
                    ],
                },
            },
            code(
                "left",
                input_schema=obj(value=NUMBER),
                output_schema=obj(value=NUMBER),
                inputs={"value": literal(2)},
            ),
            code(
                "right",
                input_schema=obj(value=NUMBER),
                output_schema=obj(value=NUMBER),
                inputs={"value": literal(3)},
            ),
            {
                "id": "join",
                "type": "parallel",
                "config": {"mode": "join", "fork_node": "fork"},
                "input_schema": obj(left=NUMBER, right=NUMBER),
                "output_schema": obj(left=NUMBER, right=NUMBER),
                "inputs": {"left": ref("value", "left"), "right": ref("value", "right")},
            },
        ],
        "edges": [
            edge("fork", "left", "left"),
            edge("fork", "right", "right"),
            edge("left", "join"),
            edge("right", "join"),
        ],
    }


def forked(database, payload=None):
    with Session(database) as db:
        identity = start(db, payload or graph(), {}).id
    assert queue.process_claim(database, queue.claim_jobs(database, "fork")[0])
    return identity


def test_parallel_jobs_finish_with_one_join_and_persisted_branch_paths(database):
    identity = forked(database)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == "completed" and run.output_json == {"left": 2, "right": 3}
        assert run.checkpoint_json["parallel_regions"]["fork"]["status"] == "joined"
        steps = {step.node_id: step for step in db.scalars(select(StepRun))}
        assert steps["left"].branch == "main/fork:left"
        assert steps["right"].branch == "main/fork:right"
        assert steps["join"].branch == "main"
        assert db.scalar(select(func.count()).select_from(DurableJob)) == 4
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 4


def test_out_of_order_sibling_completions_do_not_invalidate_each_other(database):
    identity = forked(database)
    claims = queue.claim_jobs(database, "branches", 2)
    with Session(database) as db:
        by_node = {db.get(DurableJob, claim.id).node_id: claim for claim in claims}
    both, release = Barrier(2), Event()
    registry = ExecutorRegistry()

    def handler(value):
        both.wait(timeout=10)
        if value["value"] == 2:
            assert release.wait(15)
        return value

    registry.handlers[("builtin.identity", 1)] = handler
    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(queue.process_claim, database, by_node["left"], registry)
        right = pool.submit(queue.process_claim, database, by_node["right"], registry)
        try:
            assert right.result(timeout=15)
            assert queue.claim_jobs(database, "early-join") == []
            assert not queue.process_claim(database, by_node["right"], registry)
        finally:
            release.set()
        assert left.result(timeout=15)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"left": 2, "right": 3}
        assert (
            db.scalar(
                select(func.count()).select_from(DurableJob).where(DurableJob.node_id == "join")
            )
            == 1
        )


def waiting_graph(kind):
    payload = graph()
    if kind == "delay":
        node = {"id": "left", "type": "delay", "config": {"seconds": 3600}}
        payload["nodes"][-1]["inputs"]["left"] = literal(2)
    else:
        node = approval_graph()["nodes"][0]
        node["id"] = "left"
        node["inputs"] = {key: literal(value) for key, value in approval_inputs().items()}
    payload["nodes"][1] = node
    return payload


@pytest.mark.parametrize("kind", ["delay", "approval"])
def test_waiting_branch_does_not_occupy_worker_or_block_sibling(database, kind):
    identity = forked(database, waiting_graph(kind))
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == "waiting"
        steps = {step.node_id: step for step in db.scalars(select(StepRun))}
        assert steps["right"].status == "completed"
        assert steps["left"].status == "waiting" and "join" not in steps
        if kind == "delay":
            moment = steps["left"].wake_at
        else:
            item = db.scalar(select(ExecutionApproval))
            approval_id, payload_hash = item.id, item.payload_hash
    if kind == "delay":
        assert wake_due_delays(database, now=moment - timedelta(seconds=1)) == 0
        assert wake_due_delays(database, now=moment) == 1
        assert wake_due_delays(database, now=moment) == 0
    else:
        decision(database, approval_id, payload_hash, "request_retry", human_feedback="Reconsider")
        assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
        with Session(database) as db:
            item = db.scalar(select(ExecutionApproval).where(ExecutionApproval.status == "pending"))
            assert item.iteration == 1
            approval_id, payload_hash = item.id, item.payload_hash
        decision(database, approval_id, payload_hash)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"left": 2, "right": 3}
        assert (
            db.scalar(
                select(func.count()).select_from(DurableJob).where(DurableJob.node_id == "join")
            )
            == 1
        )


@pytest.mark.parametrize("ending", ["failure", "cancel", "deadline"])
def test_branch_failure_cancel_and_deadline_close_sibling_waits(database, ending):
    identity = forked(database, waiting_graph("approval"))
    claims = queue.claim_jobs(database, "branches", 2)
    with Session(database) as db:
        by_node = {db.get(DurableJob, claim.id).node_id: claim for claim in claims}
    assert queue.process_claim(database, by_node["left"])
    if ending == "cancel":
        with Session(database) as db:
            cancel_execution(db, identity, "Stop parallel work")
        assert not queue.process_claim(database, by_node["right"])
    elif ending == "deadline":
        with Session(database) as db:
            deadline = db.get(WorkflowExecution, identity).deadline_at
        assert enforce_deadlines(database, now=deadline) == 1
    else:
        registry = ExecutorRegistry()

        def failure(value):
            raise ExecutionError("output_invalid", "fixture")

        registry.handlers[("builtin.identity", 1)] = failure
        assert queue.process_claim(database, by_node["right"], registry)
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.status == ("cancelled" if ending == "cancel" else "failed")
        assert db.scalar(select(ExecutionApproval)).status == (
            "expired" if ending == "deadline" else "cancelled"
        )
        assert all(
            step.status in {"completed", "failed", "cancelled"}
            for step in db.scalars(select(StepRun))
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(DurableJob)
                .where(DurableJob.status.in_(["running", "queued"]))
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count()).select_from(DurableJob).where(DurableJob.node_id == "join")
            )
            == 0
        )


def test_nested_parallel_regions_have_independent_paths_and_joins(database):
    payload = graph()
    inner = graph()
    names = {node["id"]: "inner_" + node["id"] for node in inner["nodes"]}
    for node in inner["nodes"]:
        node["id"] = names[node["id"]]
        config = node["config"]
        for key in ["join_node", "fork_node"]:
            if key in config:
                config[key] = names[config[key]]
        for branch in config.get("branches", []):
            branch["entry_node"] = names[branch["entry_node"]]
        for expression in node.get("inputs", {}).values():
            if expression["op"] == "ref":
                expression["ref"]["node_id"] = names[expression["ref"]["node_id"]]
    payload["nodes"][0]["config"]["branches"][0]["entry_node"] = "inner_fork"
    payload["nodes"][-1]["inputs"]["left"] = ref("left", "inner_join")
    payload["nodes"] = [node for node in payload["nodes"] if node["id"] != "left"] + inner["nodes"]
    payload["edges"] = [
        edge("fork", "inner_fork", "left"),
        edge("fork", "right", "right"),
        edge("right", "join"),
        edge("inner_join", "join"),
    ]
    payload["edges"] += [
        {**item, "source": names[item["source"]], "target": names[item["target"]]}
        for item in inner["edges"]
    ]
    identity = forked(database, payload)
    assert run_worker(database, capacity=3, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        assert run.output_json == {"left": 2, "right": 3}
        assert all(
            region["status"] == "joined"
            for region in run.checkpoint_json["parallel_regions"].values()
        )
        step = db.scalar(select(StepRun).where(StepRun.node_id == "inner_left"))
        assert step.branch == "main/fork:left/inner_fork:left"


def test_conditional_skips_settle_before_selected_branch_join(database):
    payload = graph()
    payload["nodes"][0]["config"]["branches"][0]["entry_node"] = "choice"
    payload["nodes"] += [
        {
            "id": "choice",
            "type": "condition",
            "config": {"cases": [{"label": "yes", "when": literal(True)}], "default": "no"},
        },
        code("unused"),
    ]
    payload["edges"][0] = edge("fork", "choice", "left")
    payload["edges"] += [
        edge("choice", "left", "yes"),
        edge("choice", "unused", "no"),
        edge("unused", "join"),
    ]
    identity = forked(database, payload)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"left": 2, "right": 3}
        step = db.scalar(select(StepRun).where(StepRun.node_id == "unused"))
        assert step.status == "skipped" and step.branch == "main/fork:left"
        assert (
            db.scalar(
                select(func.count())
                .select_from(StepAttempt)
                .where(StepAttempt.step_run_id == step.id)
            )
            == 0
        )


def test_maximum_fanout_obeys_worker_capacity(database, monkeypatch):
    payload = graph()
    payload["nodes"] = [payload["nodes"][0], payload["nodes"][-1]]
    payload["nodes"][0]["config"]["branches"] = []
    payload["edges"] = []
    for i in range(8):
        key = ["left", "right"][i] if i < 2 else f"branch{i}"
        payload["nodes"][0]["config"]["branches"].append({"name": key, "entry_node": key})
        payload["nodes"].append(
            code(
                key,
                input_schema=obj(value=NUMBER),
                output_schema=obj(value=NUMBER),
                inputs={"value": literal(i + 2)},
            )
        )
        payload["edges"] += [edge("fork", key, key), edge(key, "join")]
    identity = forked(database, payload)
    lock, both = Lock(), Barrier(2)
    active = maximum = calls = 0
    registry = ExecutorRegistry()

    def measured(value):
        nonlocal active, maximum, calls
        with lock:
            active += 1
            calls += 1
            maximum = max(maximum, active)
            first_pair = calls <= 2
        if first_pair:
            both.wait(timeout=15)
        time.sleep(0.03)
        with lock:
            active -= 1
        return value

    registry.handlers[("builtin.identity", 1)] = measured
    monkeypatch.setattr(
        "src.worker.process_claim",
        lambda engine, claim: queue.process_claim(engine, claim, registry),
    )
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    assert maximum == 2 and calls == 8
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"left": 2, "right": 3}


@pytest.mark.parametrize("action", ["approve", "cancel"])
def test_branch_decision_during_sibling_io_preserves_or_fences_result(database, action):
    identity = forked(database, waiting_graph("approval"))
    claims = queue.claim_jobs(database, "branches", 2)
    with Session(database) as db:
        by_node = {db.get(DurableJob, claim.id).node_id: claim for claim in claims}
    entered, release = Event(), Event()
    registry = ExecutorRegistry()

    def blocked(value):
        entered.set()
        assert release.wait(20)
        return value

    registry.handlers[("builtin.identity", 1)] = blocked
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(queue.process_claim, database, by_node["right"], registry)
        try:
            assert entered.wait(10)
            assert queue.process_claim(database, by_node["left"])
            with Session(database) as db:
                assert db.get(WorkflowExecution, identity).status == "running"
                item = db.scalar(select(ExecutionApproval))
                approval_id, payload_hash = item.id, item.payload_hash
            if action == "approve":
                decision(database, approval_id, payload_hash)
            else:
                with Session(database) as db:
                    cancel_execution(db, identity)
        finally:
            release.set()
        if action == "cancel":
            with pytest.raises(StaleWorkflowError):
                future.result(timeout=10)
        else:
            assert future.result(timeout=10)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowExecution, identity)
        if action == "approve":
            assert run.output_json == {"left": 2, "right": 3}
        else:
            assert run.status == "cancelled" and run.output_json is None
            assert db.scalar(select(StepRun).where(StepRun.node_id == "right")).output_json is None


@pytest.mark.parametrize("malformed", ["binding", "join", "fanout"])
def test_parallel_contract_rejects_malformed_regions_and_excess_fanout(malformed):
    from pydantic import ValidationError

    from src.schemas.workflow_graph import WorkflowGraph

    payload = graph()
    if malformed == "binding":
        payload["nodes"][1]["inputs"]["value"] = ref("value", "right")
    elif malformed == "join":
        payload["nodes"][-1]["config"]["fork_node"] = "right"
    else:
        payload["nodes"][0]["config"]["branches"] *= 5
    with pytest.raises(ValidationError):
        WorkflowGraph.model_validate(payload)


def test_branch_retry_preserves_completed_sibling_and_targets_one_node(database):
    payload = graph()
    payload["nodes"][1]["retry"] = {
        "max_attempts": 2,
        "initial_delay_seconds": 0,
        "retryable_errors": ["handler_failed"],
    }
    identity = forked(database, payload)
    claims = queue.claim_jobs(database, "branches", 2)
    with Session(database) as db:
        by_node = {db.get(DurableJob, claim.id).node_id: claim for claim in claims}
    assert queue.process_claim(database, by_node["right"])
    registry = ExecutorRegistry()

    def failure(value):
        raise ValueError("transient fixture failure")

    registry.handlers[("builtin.identity", 1)] = failure
    assert queue.process_claim(database, by_node["left"], registry)
    with Session(database) as db:
        jobs = db.scalars(select(DurableJob).where(DurableJob.status == "queued")).all()
        assert len(jobs) == 1 and jobs[0].node_id == "left" and jobs[0].iteration == 0
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"left": 2, "right": 3}
        assert db.scalar(select(func.count()).select_from(StepAttempt)) == 5


def test_two_branch_approval_retries_preserve_each_checkpoint(database):
    payload = waiting_graph("approval")
    right = approval_graph()["nodes"][0]
    right["id"] = "right"
    value = approval_inputs()
    value["payload"]["value"] = 3
    right["inputs"] = {key: literal(item) for key, item in value.items()}
    payload["nodes"][2] = right
    identity = forked(database, payload)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        pending = [(item.id, item.payload_hash) for item in db.scalars(select(ExecutionApproval))]
    for item_id, digest in pending:
        decision(database, item_id, digest, "request_retry", human_feedback="Recheck this branch")
    with Session(database) as db:
        assert set(
            db.get(WorkflowExecution, identity).checkpoint_json["parallel_approval_retries"]
        ) == {"left", "right"}
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        items = db.scalars(
            select(ExecutionApproval).where(ExecutionApproval.status == "pending")
        ).all()
        assert len(items) == 2 and all(item.iteration == 1 for item in items)
        pending = [(item.id, item.payload_hash) for item in items]
    for item_id, digest in pending:
        decision(database, item_id, digest)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(WorkflowExecution, identity).output_json == {"left": 2, "right": 3}
