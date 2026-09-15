"""One deterministic checkpoint at a time, with fenced result commits."""

from copy import deepcopy
from dataclasses import dataclass, replace
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select

from src.models.workflow_definition import WorkflowVersion
from src.models.workflow_execution import TERMINAL, StepAttempt, StepRun
from src.schemas.workflow_graph import StepDefinition, WorkflowGraph
from src.services.execution_records import add_attempt, add_step, execution
from src.services.execution_registry import DEFAULT_REGISTRY, NodeResult
from src.services.graph_expressions import ExecutionError, resolve_bindings
from src.services.graph_validation import validate_data
from src.services.workflow_state import transition_execution_entity as transition
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction


@dataclass(frozen=True)
class WorkItem:
    execution_id: UUID
    step_id: UUID
    attempt_id: UUID
    revision: int
    node: StepDefinition
    inputs: dict
    context: tuple[dict, dict]


def graph_for(db, run):
    version = db.scalar(select(WorkflowVersion).where(WorkflowVersion.id == run.version_id))
    if version is None:
        raise ExecutionError("version_missing", "Pinned workflow version is missing")
    return WorkflowGraph.model_validate(version.graph)


def rows_for(db, run):
    rows = db.scalars(select(StepRun).where(StepRun.execution_id == run.id)).all()
    if any(row.branch != "main" or row.iteration != 0 for row in rows):
        raise ExecutionError("unsupported_checkpoint", "Branch/revision execution is unavailable")
    return {row.node_id: row for row in rows}


def context_for(run, rows):
    return deepcopy(run.input_json or {}), {
        key: deepcopy(row.output_json) for key, row in rows.items() if row.status == "completed"
    }


def set_edges(run, edges):
    run.checkpoint_json = {**run.checkpoint_json, "edges": edges}


def fail_execution(db, run, error, step=None, attempt=None):
    for entity in [attempt, step, run]:
        if entity is not None:
            entity.error_code = error.code
            entity.error_message = str(error)[:4000]
            transition(db, run, entity, "failed")


def next_node(db, run, graph, rows, edges):
    """Settle unreachable condition routes before selecting one ready node."""
    remaining = {node.id: node for node in graph.nodes if node.id not in rows}
    while remaining:
        changed = False
        for key, node in list(remaining.items()):
            incoming = [str(i) for i, edge in enumerate(graph.edges) if edge.target == key]
            if key == graph.entry_node:
                return node
            if any(edge not in edges for edge in incoming):
                continue
            if any(edges[edge] == "selected" for edge in incoming):
                return node
            step = add_step(db, run, key)
            transition(db, run, step, "skipped")
            rows[key] = step
            for i, edge in enumerate(graph.edges):
                if edge.source == key:
                    edges[str(i)] = "skipped"
            del remaining[key]
            changed = True
        if not changed:
            break
    if remaining:
        raise ExecutionError("graph_stalled", "No ready node for unresolved graph routes")
    return None


def prepare_next(db, execution_id, registry=DEFAULT_REGISTRY, *, on_checkpoint=None):
    """Commit a prepared attempt before executor work; callers must not nest this."""
    if db.info.get("workflow_transaction"):
        raise ValueError("Prepare a checkpoint outside an existing workflow transaction")
    run = execution(db, execution_id)
    if run.status in TERMINAL or run.status in {"waiting", "retrying"}:
        return None
    graph = graph_for(db, run)
    registry.validate(graph)
    rows = rows_for(db, run)
    if any(row.status not in TERMINAL for row in rows.values()):
        # Recovery of interrupted attempts belongs to the durable worker phases.
        return None
    work = None
    with workflow_transaction(db, run):
        if run.status == "pending":
            transition(db, run, run, "running")
        edges = dict(run.checkpoint_json.get("edges", {}))
        try:
            node = next_node(db, run, graph, rows, edges)
            set_edges(run, edges)
            context = context_for(run, rows)
            if node is None:
                run.output_json = resolve_bindings(graph.outputs, *context, graph.output_schema)
                transition(db, run, run, "completed")
            else:
                step = add_step(db, run, node.id)
                attempt = add_attempt(db, run, step)
                transition(db, run, step, "running")
                transition(db, run, attempt, "running")
                try:
                    inputs = resolve_bindings(node.inputs, *context, node.input_schema)
                except (ExecutionError, ValidationError, ValueError) as error:
                    failure = (
                        error
                        if isinstance(error, ExecutionError)
                        else ExecutionError(
                            "input_invalid",
                            "Node input violates its data contract",
                        )
                    )
                    fail_execution(db, run, failure, step, attempt)
                else:
                    step.input_json = attempt.input_json = inputs
                    work = WorkItem(run.id, step.id, attempt.id, 0, node, inputs, context)
        except (ExecutionError, ValidationError, ValueError) as error:
            failure = (
                error
                if isinstance(error, ExecutionError)
                else ExecutionError(
                    "output_invalid",
                    "Workflow output violates its data contract",
                )
            )
            fail_execution(db, run, failure)
        if on_checkpoint is not None:
            on_checkpoint(run, work)
    return replace(work, revision=run.state_revision) if work else None


def execute_work(work, registry=DEFAULT_REGISTRY):
    """No database session or lock crosses this boundary."""
    try:
        result = registry.execute(work.node, work.inputs, work.context)
        validate_data(result.output, work.node.output_schema)
        WorkflowGraph.payload_bounds({"output": result.output})
        if work.node.type == "condition" and result.route not in {
            *(case.label for case in work.node.config.cases),
            work.node.config.default,
        }:
            raise ExecutionError("route_invalid", "Condition did not select a declared route")
        return result
    except ExecutionError:
        raise
    except (ValidationError, ValueError, TypeError, OverflowError) as error:
        raise ExecutionError("output_invalid", "Node output violates its data contract") from error


def complete_work(db, work, result: NodeResult | None = None, error: ExecutionError | None = None):
    """May share a caller-owned run transaction with later durable job scheduling."""
    run = execution(db, work.execution_id)
    if run.state_revision != work.revision:
        raise StaleWorkflowError("Prepared execution changed before its result arrived")
    with workflow_transaction(db, run, expected_revision=work.revision):
        step = db.scalar(
            select(StepRun).where(StepRun.id == work.step_id, StepRun.execution_id == run.id)
        )
        attempt = db.scalar(
            select(StepAttempt).where(
                StepAttempt.id == work.attempt_id, StepAttempt.step_run_id == work.step_id
            )
        )
        if (
            step is None
            or attempt is None
            or step.status != "running"
            or attempt.status != "running"
        ):
            raise StaleWorkflowError("Prepared step or attempt is no longer running")
        if error:
            fail_execution(db, run, error, step, attempt)
        else:
            if result is None:
                raise ValueError("A result or typed failure is required")
            attempt.output_json = step.output_json = deepcopy(result.output)
            transition(db, run, attempt, "completed")
            transition(db, run, step, "completed")
            graph = graph_for(db, run)
            edges = dict(run.checkpoint_json.get("edges", {}))
            for i, edge in enumerate(graph.edges):
                if edge.source == step.node_id:
                    edges[str(i)] = (
                        "selected"
                        if step.step_type != "condition" or edge.label == result.route
                        else "skipped"
                    )
            set_edges(run, edges)
    return run


def advance_checkpoint(db, execution_id, registry=DEFAULT_REGISTRY):
    work = prepare_next(db, execution_id, registry)
    if work is None:
        return execution(db, execution_id)
    try:
        result = execute_work(work, registry)
    except ExecutionError as error:
        return complete_work(db, work, error=error)
    return complete_work(db, work, result=result)


def run_deterministic_execution(db, execution_id, registry=DEFAULT_REGISTRY):
    """Bounded local runner; durable workers will consume individual checkpoints."""
    for _ in range(101):
        run = execution(db, execution_id)
        before = run.state_revision
        run = advance_checkpoint(db, execution_id, registry)
        if run.status in TERMINAL or run.state_revision == before:
            return run
    raise ExecutionError("checkpoint_limit", "Execution exceeded the graph checkpoint bound")
