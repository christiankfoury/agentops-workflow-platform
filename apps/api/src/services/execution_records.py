import hashlib
import json
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from src.models.workflow_definition import WorkflowVersion
from src.models.workflow_execution import ExecutionEvent, StepAttempt, StepRun, WorkflowExecution
from src.schemas.workflow_graph import WorkflowGraph
from src.services.workflow_transactions import workflow_transaction


def execution(db, identity):
    run = db.scalar(select(WorkflowExecution).where(WorkflowExecution.id == identity))
    if run is None:
        raise HTTPException(404, "Workflow execution not found")
    return run


def pinned_node(db, run, node_id):
    version = db.scalar(select(WorkflowVersion).where(WorkflowVersion.id == run.version_id))
    if version is None:
        raise ValueError("Pinned workflow version is missing")
    graph = WorkflowGraph.model_validate(version.graph)
    node = next((node for node in graph.nodes if node.id == node_id), None)
    if node is None:
        raise ValueError("Node is absent from the pinned workflow version")
    return node


def add_step(db, run, node_id, *, branch="main", iteration=0, inputs=None):
    with workflow_transaction(db, run):
        if run.status not in {"pending", "running"}:
            raise ValueError("Execution cannot add a step in its current state")
        if not branch or len(branch) > 256 or type(iteration) is not int or iteration < 0:
            raise ValueError("Invalid branch/iteration identity")
        node = pinned_node(db, run, node_id)
        key = hashlib.sha256(
            json.dumps([str(run.id), node_id, branch, iteration]).encode()
        ).hexdigest()
        step = StepRun(
            execution_id=run.id,
            node_id=node.id,
            step_type=node.type,
            branch=branch,
            iteration=iteration,
            idempotency_key=key,
            input_json=inputs,
        )
        db.add(step)
        db.flush()
        db.add(
            ExecutionEvent(
                execution_id=run.id,
                entity_type="step_runs",
                entity_id=step.id,
                to_status="pending",
            )
        )
    return step


def add_attempt(db, run, step):
    with workflow_transaction(db, run):
        db.refresh(step)
        if (
            step.execution_id != run.id
            or run.status != "running"
            or step.status
            not in {
                "pending",
                "retrying",
            }
        ):
            raise ValueError("Step is not ready for a new attempt")
        active = db.scalar(
            select(StepAttempt.id)
            .where(
                StepAttempt.step_run_id == step.id,
                StepAttempt.status.in_(["pending", "running"]),
            )
            .limit(1)
        )
        if active:
            raise ValueError("A step already has an active attempt")
        number = (
            db.scalar(
                select(func.max(StepAttempt.number)).where(
                    StepAttempt.step_run_id == step.id,
                )
            )
            or 0
        ) + 1
        node = pinned_node(db, run, step.node_id)
        if number > node.retry.max_attempts:
            raise ValueError("Step attempt limit reached")
        deadline = db.scalar(select(func.clock_timestamp())) + timedelta(
            seconds=node.timeout_seconds
        )
        if run.deadline_at:
            deadline = min(deadline, run.deadline_at)
        attempt = StepAttempt(
            step_run_id=step.id,
            number=number,
            input_json=step.input_json,
            idempotency_key=step.idempotency_key,
            deadline_at=deadline,
        )
        db.add(attempt)
        db.flush()
        db.add(
            ExecutionEvent(
                execution_id=run.id,
                entity_type="step_attempts",
                entity_id=attempt.id,
                to_status="pending",
                details={"number": number},
            )
        )
    return attempt
