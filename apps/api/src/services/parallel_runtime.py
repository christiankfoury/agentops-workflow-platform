"""Run-serialized scheduling with independently owned branch jobs and attempts."""

from sqlalchemy import func, select

from src.models.workflow_execution import TERMINAL, StepAttempt, StepRun
from src.services.execution_records import add_step
from src.services.graph_expressions import ExecutionError, resolve_bindings
from src.services.parallel_graph import branch_paths
from src.services.quality_revisions import iteration_for
from src.services.workflow_state import transition_execution_entity as transition


def cancel_siblings(db, run, *, code="branch_failed"):
    from src.services.approval_runtime import close_pending

    close_pending(db, run, "cancelled")
    for step in db.scalars(
        select(StepRun).where(
            StepRun.execution_id == run.id,
            StepRun.status.not_in(TERMINAL),
        )
    ).all():
        for attempt in db.scalars(
            select(StepAttempt).where(
                StepAttempt.step_run_id == step.id,
                StepAttempt.status.not_in(TERMINAL),
            )
        ).all():
            attempt.error_code = code
            attempt.error_message = "Another branch ended the execution"
            transition(db, run, attempt, "cancelled")
        step.next_attempt_at = None
        step.error_code = code
        step.error_message = "Another branch ended the execution"
        transition(db, run, step, "cancelled")


def schedule_parallel(db, run):
    from src.services.durable_queue import enqueue, jobs, terminate_jobs
    from src.services.graph_interpreter import context_for, graph_for, rows_for, set_edges

    if run.status in TERMINAL:
        terminate_jobs(db, run, "cancelled", run.error_code or "branch_failed")
        return
    graph = graph_for(db, run)
    paths = branch_paths(graph)
    rows = rows_for(db, run, graph)
    edges = dict(run.checkpoint_json.get("edges", {}))
    active = (
        db.connection()
        .execute(
            select(jobs.c.node_id, jobs.c.iteration).where(
                jobs.c.execution_id == run.id,
                jobs.c.status.in_(["queued", "running"]),
            )
        )
        .all()
    )
    targets = {(row.node_id, row.iteration) for row in active}
    retries = run.checkpoint_json.get("parallel_approval_retries", {})
    ready = []
    remaining = {node.id: node for node in graph.nodes if node.id not in rows}
    while remaining:
        skipped = False
        for key, node in list(remaining.items()):
            incoming = [str(i) for i, edge in enumerate(graph.edges) if edge.target == key]
            if key != graph.entry_node and any(edge not in edges for edge in incoming):
                continue
            if key == graph.entry_node or any(edges[edge] == "selected" for edge in incoming):
                iteration = iteration_for(run, graph, key)
                if (key, iteration) not in targets:
                    ready.append((node, iteration, None))
                del remaining[key]
                continue
            step = add_step(
                db, run, key, branch=paths[key], iteration=iteration_for(run, graph, key)
            )
            transition(db, run, step, "skipped")
            rows[key] = step
            for i, edge in enumerate(graph.edges):
                if edge.source == key:
                    edges[str(i)] = "skipped"
            del remaining[key]
            skipped = True
        if not skipped:
            break
    set_edges(run, edges)
    for node in graph.nodes:
        step = rows.get(node.id)
        if node.id in retries:
            iteration = retries[node.id]["iteration"]
            if (node.id, iteration) not in targets:
                ready.append((node, iteration, None))
        elif step and step.status == "retrying" and (node.id, step.iteration) not in targets:
            ready.append((node, step.iteration, step.next_attempt_at))
    if ready and run.status == "waiting":
        transition(db, run, run, "running")
    sequence = db.connection().scalar(
        select(func.max(jobs.c.sequence)).where(
            jobs.c.execution_id == run.id,
        )
    )
    sequence = 0 if sequence is None else sequence + 1
    for node, iteration, due in ready:
        enqueue(
            db,
            run,
            sequence,
            node_id=node.id,
            iteration=iteration,
            branch=paths[node.id],
            due_at=due,
        )
        sequence += 1
    if ready or active:
        return
    if any(step.status == "waiting" for step in rows.values()):
        if run.status == "running":
            transition(db, run, run, "waiting")
        return
    try:
        if remaining or any(step.status not in TERMINAL for step in rows.values()):
            raise ExecutionError("graph_stalled", "Parallel graph has no ready or waiting work")
        run.output_json = resolve_bindings(
            graph.outputs, *context_for(run, rows), graph.output_schema
        )
    except (ExecutionError, ValueError) as error:
        cancel_siblings(db, run)
        run.error_code = error.code if isinstance(error, ExecutionError) else "output_invalid"
        run.error_message = str(error)[:4000]
        transition(db, run, run, "failed")
    else:
        transition(db, run, run, "completed")
