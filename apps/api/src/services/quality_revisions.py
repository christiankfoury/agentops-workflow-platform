"""Bounded quality iterations over a declared region, separate from job retries."""

from copy import deepcopy

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from src.models.execution_approval import ExecutionApproval
from src.models.workflow_execution import ExecutionEvent, StepRun
from src.schemas.execution_approval import ApprovalReview
from src.services.graph_expressions import ExecutionError
from src.services.graph_validation import invalid


def validate_policy(graph):
    policy = graph.quality_revision
    if policy is None:
        return
    nodes = {node.id: node for node in graph.nodes}
    following = [edge.target for edge in graph.edges if edge.source == policy.review_node]
    gate = nodes.get(policy.approval_node)
    if (
        nodes[policy.review_node].type != "llm"
        or gate is None
        or gate.type != "approval"
        or gate.id in policy.nodes
        or len(following) != 1
    ):
        invalid(
            ("quality_revision",), "Quality revision requires an LLM review and human approval node"
        )
    next_node = nodes[following[0]]
    review_schema = nodes[policy.review_node].output_schema
    required_types = {
        "approved": {"boolean"},
        "quality_score": {"number", "integer"},
        "issues": {"array"},
        "retry_recommended": {"boolean"},
    }
    if not required_types.keys() <= set(review_schema.required) or any(
        not review_schema.properties[key].types <= kinds for key, kinds in required_types.items()
    ):
        invalid(
            ("quality_revision",),
            "Quality revision requires the structured reviewer output contract",
        )
    issue = review_schema.properties["issues"].items
    issue_fields = {"claim", "problem", "severity"}
    if (
        issue.types != {"object"}
        or set(issue.properties) != issue_fields
        or set(issue.required) != issue_fields
        or any(field.types != {"string"} for field in issue.properties.values())
    ):
        invalid(
            ("quality_revision",),
            "Quality revision issues require claim, problem and severity strings",
        )
    if next_node.id != gate.id and not (
        next_node.type == "condition"
        and any(edge.source == next_node.id and edge.target == gate.id for edge in graph.edges)
    ):
        invalid(
            ("quality_revision",),
            "Quality revision review must lead to its approval directly or through one condition",
        )
    if any(nodes[key].type in {"approval", "delay", "tool"} for key in policy.nodes):
        invalid(
            ("quality_revision",),
            "Quality revision region must contain bounded computation without waits or effects",
        )


def affected_nodes(graph):
    if not graph.quality_revision:
        return set()
    pending, affected = [graph.quality_revision.entry_node], set()
    while pending:
        key = pending.pop()
        if key in affected:
            continue
        affected.add(key)
        pending.extend(edge.target for edge in graph.edges if edge.source == key)
    return affected


def iteration_for(run, graph, node_id):
    return (
        run.checkpoint_json.get("quality", {}).get("iteration", 0)
        if node_id in affected_nodes(graph)
        else 0
    )


def revision_context(run, graph, node_id):
    policy = graph.quality_revision
    if not policy:
        return {}
    quality = run.checkpoint_json.get("quality", {})
    if node_id in policy.nodes:
        return {
            **deepcopy(quality.get("feedback", {})),
            "quality_reviewer": node_id == policy.review_node,
        }
    if quality.get("status") == "human_required":
        successors = [edge.target for edge in graph.edges if edge.source == policy.review_node]
        if node_id in successors and node_id != policy.approval_node:
            return {
                "forced_route": next(
                    edge.label
                    for edge in graph.edges
                    if edge.source == node_id and edge.target == policy.approval_node
                )
            }
    return {}


def restart(db, run, graph, feedback, *, human=False):
    from src.services.approval_runtime import resolve

    policy = graph.quality_revision
    quality = dict(run.checkpoint_json.get("quality", {}))
    iteration = quality.get("iteration", 0)
    if iteration >= policy.max_revisions:
        raise HTTPException(409, "Quality revision limit reached; edit, approve or reject")
    affected = affected_nodes(graph)
    if db.scalar(
        select(StepRun.id)
        .where(
            StepRun.execution_id == run.id,
            StepRun.node_id.in_(affected),
            StepRun.status.in_(["pending", "running", "retrying", "waiting"]),
        )
        .limit(1)
    ):
        raise ExecutionError("quality_revision_busy", "Revision region has unfinished work")
    for item in db.scalars(
        select(ExecutionApproval).where(
            ExecutionApproval.execution_id == run.id,
            ExecutionApproval.node_id.in_(affected),
            ExecutionApproval.status == "pending",
        )
    ):
        resolve(db, run, item, "invalidated")
    quality.update(
        iteration=iteration + 1,
        status="revising",
        feedback={**quality.get("feedback", {}), **deepcopy(feedback)},
        human_retries=quality.get("human_retries", 0) + int(human),
    )
    edges = {
        key: value
        for key, value in run.checkpoint_json.get("edges", {}).items()
        if graph.edges[int(key)].source not in affected
    }
    run.checkpoint_json = {**run.checkpoint_json, "quality": quality, "edges": edges}
    db.add(
        ExecutionEvent(
            execution_id=run.id,
            entity_type="workflow_executions",
            entity_id=run.id,
            from_status=run.status,
            to_status=run.status,
            details={
                "reason": "quality_revision",
                "iteration": iteration + 1,
                "human_requested": human,
                "nodes": policy.nodes,
                "feedback": feedback,
            },
        )
    )


def after_review(db, run, step, graph):
    policy = graph.quality_revision
    if not policy or step.node_id != policy.review_node:
        return
    try:
        review = ApprovalReview.model_validate(step.output_json)
    except ValidationError as error:
        raise ExecutionError(
            "review_invalid", "Reviewer output violates the quality contract"
        ) from error
    quality = dict(run.checkpoint_json.get("quality", {}))
    iteration = quality.get("iteration", 0)
    threshold = run.runtime_config[step.node_id]["reviewer_approval_threshold"]
    accepted = (
        review.approved
        and review.quality_score >= threshold
        and not any(issue.severity in {"high", "critical"} for issue in review.issues)
    )
    quality["history"] = [
        *quality.get("history", []),
        {"iteration": iteration, "review": deepcopy(step.output_json), "accepted": accepted},
    ]
    quality["status"] = "accepted" if accepted else "human_required"
    run.checkpoint_json = {**run.checkpoint_json, "quality": quality}
    if not accepted and review.retry_recommended and iteration < policy.max_revisions:
        restart(db, run, graph, {"review": step.output_json})


def human_retry_policy(run, graph, step):
    policy = graph.quality_revision
    if not policy or policy.approval_node != step.node_id:
        return False
    quality = run.checkpoint_json.get("quality", {})
    node = next(node for node in graph.nodes if node.id == step.node_id)
    if (
        quality.get("iteration", 0) >= policy.max_revisions
        or quality.get("human_retries", 0) >= node.config.max_review_retries
    ):
        raise HTTPException(409, "Quality revision limit reached; edit, approve or reject")
    return True
