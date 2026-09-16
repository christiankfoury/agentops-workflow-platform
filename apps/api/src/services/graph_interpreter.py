"""One deterministic checkpoint at a time, with fenced result commits."""

from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select

from src.models.workflow_definition import WorkflowVersion
from src.models.workflow_execution import TERMINAL, StepAttempt, StepRun, WorkflowExecution
from src.schemas.workflow_graph import StepDefinition, WorkflowGraph
from src.services.execution_control import AbortSignal
from src.services.execution_records import add_attempt, add_step, execution
from src.services.execution_registry import DEFAULT_REGISTRY, NodeResult
from src.services.graph_expressions import ExecutionError, resolve_bindings
from src.services.graph_validation import validate_data
from src.services.parallel_graph import branch_paths, has_parallel
from src.services.quality_revisions import (
    affected_nodes,
    after_review,
    iteration_for,
    revision_context,
)
from src.services.retry_runtime import expire_execution, fail_attempt, runtime_now
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
    deadline_at: datetime | None = None
    control: AbortSignal = field(default_factory=AbortSignal, compare=False, repr=False)
    parallel: bool = False
    runtime_config: dict = field(default_factory=dict)
    revision_context: dict = field(default_factory=dict)


def graph_for(db, run):
    version = db.scalar(select(WorkflowVersion).where(WorkflowVersion.id == run.version_id))
    if version is None:
        raise ExecutionError("version_missing", "Pinned workflow version is missing")
    return WorkflowGraph.model_validate(version.graph)


def rows_for(db, run, graph=None):
    rows = db.scalars(
        select(StepRun).where(StepRun.execution_id == run.id).order_by(StepRun.iteration)
    ).all()
    graph = graph or graph_for(db, run)
    paths = branch_paths(graph)
    affected = affected_nodes(graph)
    if any(
        row.branch != paths.get(row.node_id)
        or (row.iteration != 0 and row.step_type != "approval" and row.node_id not in affected)
        for row in rows
    ):
        raise ExecutionError("unsupported_checkpoint", "Branch/revision execution is unavailable")
    return {
        row.node_id: row for row in rows if row.iteration >= iteration_for(run, graph, row.node_id)
    }


def context_for(run, rows):
    return deepcopy(run.input_json or {}), {
        key: deepcopy(row.output_json) for key, row in rows.items() if row.status == "completed"
    }


def set_edges(run, edges):
    run.checkpoint_json = {**run.checkpoint_json, "edges": edges}


def fail_execution(db, run, error, step=None, attempt=None):
    if attempt is not None:
        attempt.error_classification = "permanent"
    for entity in [attempt, step, run]:
        if entity is not None:
            if entity is run and run.checkpoint_json.get("parallel_mode"):
                from src.services.parallel_runtime import cancel_siblings

                cancel_siblings(db, run)
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


def prepare_next(
    db,
    execution_id,
    registry=DEFAULT_REGISTRY,
    *,
    on_checkpoint=None,
    target_node=None,
    target_iteration=0,
):
    """Commit a prepared attempt before executor work; callers must not nest this."""
    if db.info.get("workflow_transaction"):
        raise ValueError("Prepare a checkpoint outside an existing workflow transaction")
    run = execution(db, execution_id)
    if run.status in TERMINAL or run.status in {"waiting", "retrying"}:
        return None
    graph = graph_for(db, run)
    parallel = has_parallel(graph) or graph.quality_revision is not None
    registry.validate(graph)
    rows = rows_for(db, run, graph)
    resumable = [
        row
        for row in rows.values()
        if row.status == "retrying"
        and (not parallel or target_node is None or row.node_id == target_node)
    ]
    if not parallel and (
        len(resumable) > 1
        or any(row.status not in TERMINAL | {"retrying"} for row in rows.values())
    ):
        return None
    observed_now = runtime_now(db)
    if (
        resumable
        and resumable[0].next_attempt_at
        and observed_now < resumable[0].next_attempt_at
        and (run.deadline_at is None or observed_now < run.deadline_at)
    ):
        return None
    work = None
    with workflow_transaction(db, run):
        now = runtime_now(db)
        if run.deadline_at and now >= run.deadline_at:
            expire_execution(db, run)
            if on_checkpoint:
                on_checkpoint(run, None)
            return None
        if run.status == "pending":
            transition(db, run, run, "running")
        if parallel:
            run.checkpoint_json = {**run.checkpoint_json, "parallel_mode": True}
        edges = dict(run.checkpoint_json.get("edges", {}))
        try:
            approval_retry = (
                run.checkpoint_json.get("parallel_approval_retries", {}).get(target_node)
                if parallel
                else run.checkpoint_json.get("approval_retry")
            )
            node = (
                next(node for node in graph.nodes if node.id == target_node)
                if parallel and target_node
                else next(node for node in graph.nodes if node.id == approval_retry["node_id"])
                if approval_retry
                else next(node for node in graph.nodes if node.id == resumable[0].node_id)
                if resumable
                else next_node(db, run, graph, rows, edges)
            )
            set_edges(run, edges)
            context = context_for(run, rows)
            if node is None:
                run.output_json = resolve_bindings(graph.outputs, *context, graph.output_schema)
                transition(db, run, run, "completed")
            else:
                step = (
                    resumable[0]
                    if resumable
                    else add_step(
                        db,
                        run,
                        node.id,
                        iteration=target_iteration
                        if parallel
                        else (approval_retry["iteration"] if approval_retry else 0),
                        branch=branch_paths(graph)[node.id],
                    )
                )
                attempt = add_attempt(db, run, step)
                step.error_code = step.error_message = None
                step.next_attempt_at = None
                transition(db, run, step, "running")
                transition(db, run, attempt, "running")
                try:
                    inputs = resolve_bindings(node.inputs, *context, node.input_schema)
                    step.input_json = attempt.input_json = inputs
                    if node.type == "delay":
                        from src.services.delay_runtime import schedule_delay

                        schedule_delay(db, run, step, attempt, node, now)
                    elif node.type == "approval":
                        from src.services.approval_runtime import register_approval

                        register_approval(db, run, step, attempt, node, now, approval_retry)
                        if approval_retry and parallel:
                            run.checkpoint_json = {
                                **run.checkpoint_json,
                                "parallel_approval_retries": {
                                    key: value
                                    for key, value in run.checkpoint_json.get(
                                        "parallel_approval_retries", {}
                                    ).items()
                                    if key != target_node
                                },
                            }
                        elif approval_retry:
                            run.checkpoint_json = {
                                key: value
                                for key, value in run.checkpoint_json.items()
                                if key != "approval_retry"
                            }
                    else:
                        work = WorkItem(
                            run.id,
                            step.id,
                            attempt.id,
                            0,
                            node,
                            inputs,
                            context,
                            attempt.deadline_at,
                            parallel=parallel,
                            runtime_config=deepcopy(run.runtime_config.get(node.id, {})),
                            revision_context=revision_context(run, graph, node.id),
                        )
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
        work.control.raise_if_aborted()
        if work.node.type == "llm":
            from src.services.llm_execution import execute_llm

            result = execute_llm(work, registry.llm_factory, registry.output_validators)
        elif work.node.type == "condition" and "forced_route" in work.revision_context:
            result = NodeResult({}, route=work.revision_context["forced_route"])
        else:
            result = registry.execute(work.node, work.inputs, work.context, work.control)
        work.control.raise_if_aborted()
        if work.revision_context.get("quality_reviewer"):
            from src.schemas.execution_approval import ApprovalReview

            try:
                ApprovalReview.model_validate(result.output)
            except ValidationError as error:
                failure = ExecutionError(
                    "review_invalid", "Reviewer output violates the quality contract"
                )
                failure.llm_metadata = result.llm_metadata
                raise failure from error
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


def complete_work(
    db, work, result: NodeResult | None = None, error: ExecutionError | None = None, *, now=None
):
    """May share a caller-owned run transaction with later durable job scheduling."""
    run = execution(db, work.execution_id)
    if work.parallel and not db.info.get("workflow_transaction"):
        run = db.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == run.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    if not work.parallel and run.state_revision != work.revision:
        raise StaleWorkflowError("Prepared execution changed before its result arrived")
    with workflow_transaction(db, run, expected_revision=None if work.parallel else work.revision):
        step = db.scalar(
            select(StepRun)
            .where(StepRun.id == work.step_id, StepRun.execution_id == run.id)
            .execution_options(populate_existing=True)
        )
        attempt = db.scalar(
            select(StepAttempt)
            .where(StepAttempt.id == work.attempt_id, StepAttempt.step_run_id == work.step_id)
            .execution_options(populate_existing=True)
        )
        if (
            step is None
            or attempt is None
            or step.status != "running"
            or attempt.status != "running"
            or run.status in TERMINAL
            or run.cancel_requested
        ):
            raise StaleWorkflowError("Prepared step or attempt is no longer running")
        now = now or runtime_now(db)
        metadata = (
            getattr(error, "llm_metadata", None)
            if error
            else result.llm_metadata
            if result
            else None
        )
        if metadata:
            from src.models.workflow_execution import ExecutionEvent

            attempt.llm_metadata = deepcopy(metadata)
            db.add(
                ExecutionEvent(
                    execution_id=run.id,
                    entity_type="step_attempts",
                    entity_id=attempt.id,
                    from_status=attempt.status,
                    to_status=attempt.status,
                    details={"reason": "llm_usage", **metadata},
                )
            )
        if run.deadline_at and now >= run.deadline_at:
            error = ExecutionError("run_deadline", "Workflow deadline expired")
        elif attempt.deadline_at and now >= attempt.deadline_at:
            error = ExecutionError("attempt_timeout", "Step attempt deadline expired")
        if error:
            fail_attempt(db, run, step, attempt, error, now)
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
            if work.node.type == "parallel":
                config = work.node.config
                key = work.node.id if config.mode == "fork" else config.fork_node
                regions = dict(run.checkpoint_json.get("parallel_regions", {}))
                regions[key] = (
                    {
                        "status": "forked",
                        "join_node": config.join_node,
                        "branches": [branch.name for branch in config.branches],
                    }
                    if config.mode == "fork"
                    else {**regions[key], "status": "joined"}
                )
                run.checkpoint_json = {**run.checkpoint_json, "parallel_regions": regions}
            after_review(db, run, step, graph)
    return run


def advance_checkpoint(db, execution_id, registry=DEFAULT_REGISTRY):
    graph = graph_for(db, execution(db, execution_id))
    if has_parallel(graph) or graph.quality_revision:
        raise ExecutionError(
            "durable_worker_required",
            "Parallel graphs and quality revisions require durable workers",
        )
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
    graph = graph_for(db, execution(db, execution_id))
    for _ in range(sum(node.retry.max_attempts for node in graph.nodes) + 1):
        run = execution(db, execution_id)
        before = run.state_revision
        run = advance_checkpoint(db, execution_id, registry)
        if run.status in TERMINAL or run.state_revision == before:
            return run
    raise ExecutionError("checkpoint_limit", "Execution exceeded the graph checkpoint bound")
