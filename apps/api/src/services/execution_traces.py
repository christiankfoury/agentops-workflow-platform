"""Read-only debugger projections. Never combine generic and legacy usage."""

import json
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import load_only

from src.models.agent_step import AgentStep
from src.models.execution_approval import ExecutionApproval
from src.models.tool import ToolExecution
from src.models.workflow_definition import WorkflowVersion
from src.models.workflow_execution import ExecutionEvent, StepAttempt, StepRun, WorkflowExecution
from src.models.workflow_run import WorkflowRun
from src.schemas.tool import SENSITIVE_KEYS
from src.services.execution_records import execution

COMMON = ("id", "status", "created_at", "started_at", "completed_at", "error_code")
RUN = (*COMMON, "version_id", "legacy_run_id", "state_revision", "deadline_at", "cancel_requested")
FIELDS = {
    "steps": (
        *COMMON,
        "node_id",
        "step_type",
        "branch",
        "iteration",
        "waiting_reason",
        "wake_at",
        "next_attempt_at",
        "recovered_from_id",
    ),
    "attempts": (*COMMON, "step_run_id", "number", "deadline_at", "error_classification"),
    "events": ("id", "entity_type", "entity_id", "from_status", "to_status", "created_at"),
    "tools": (
        "id",
        "step_run_id",
        "attempt_id",
        "call_id",
        "version_id",
        "status",
        "attempts",
        "error_code",
        "latency_ms",
        "created_at",
        "updated_at",
    ),
    "approvals": (
        "id",
        "step_run_id",
        "node_id",
        "iteration",
        "revision",
        "status",
        "version_id",
        "created_at",
        "expires_at",
        "resolved_at",
        "decided_by_user_id",
        "replacement_id",
    ),
}
MODELS = dict(
    steps=StepRun,
    attempts=StepAttempt,
    events=ExecutionEvent,
    tools=ToolExecution,
    approvals=ExecutionApproval,
)
LEGACY = (
    "id",
    "agent_name",
    "agent_type",
    "step_order",
    "status",
    "model",
    "prompt_version_id",
    "tokens_input",
    "tokens_output",
    "total_tokens",
    "cost",
    "latency_ms",
    "retry_count",
    "created_at",
    "completed_at",
)


def fields(item, names):
    return {key: getattr(item, key) for key in names}


def preview(value, limit=2000):
    """Bound structure before encoding; redact known credential fields and URL userinfo.

    This is a debugger view, not an export or a guarantee against secrets embedded
    in arbitrary prose. Credential values are never fetched to build it.
    """
    remaining, characters, clipped = [8000], [limit * 2], [False]

    def text_value(value):
        value = re.sub(r"(https?://)[^\s/@]+(?::[^\s/@]*)?@", r"\1[REDACTED]@", value)
        if len(value) > characters[0]:
            clipped[0] = True
            value = value[: characters[0]]
        characters[0] -= len(value)
        return value

    def clean(item, depth=0):
        remaining[0] -= 1
        if remaining[0] < 0 or depth > 24:
            clipped[0] = True
            return "[preview limit]"
        if isinstance(item, dict):
            result = {}
            for key, child in item.items():
                if remaining[0] <= 0 or characters[0] <= 0:
                    clipped[0] = True
                    break
                sensitive = str(key).lower().replace("-", "_") in (
                    SENSITIVE_KEYS
                    | {
                        "secret_alias",
                        "previous_secret_alias",
                        "claim_token",
                        "reservation_token",
                        "credential_digest",
                    }
                )
                result[text_value(str(key))] = clean(
                    "[REDACTED]" if sensitive else child, depth + 1
                )
            return result
        if isinstance(item, list):
            result = []
            for child in item:
                if remaining[0] <= 0 or characters[0] <= 0:
                    clipped[0] = True
                    break
                result.append(clean(child, depth + 1))
            return result
        if isinstance(item, str):
            item = text_value(item)
        return item

    text = json.dumps(clean(value), ensure_ascii=False, default=str, indent=2)
    return {"text": text[:limit], "truncated": clipped[0] or len(text) > limit, "limit": limit}


def page(db, query, serialize, offset, limit):
    rows = db.scalars(query.offset(offset).limit(limit + 1)).all()
    return {
        "items": [serialize(row) for row in rows[:limit]],
        "offset": offset,
        "next_offset": offset + limit if len(rows) > limit else None,
    }


def listing(db, offset, limit):
    query = select(WorkflowExecution).options(
        load_only(*(getattr(WorkflowExecution, k) for k in RUN))
    )
    return page(
        db,
        query.order_by(WorkflowExecution.created_at.desc(), WorkflowExecution.id),
        lambda row: fields(row, RUN),
        offset,
        limit,
    )


def overview(db, identity):
    run = execution(db, identity)
    version = db.scalar(select(WorkflowVersion).where(WorkflowVersion.id == run.version_id))
    if version is None:
        raise HTTPException(404, "Pinned version not found")
    # Read topology from the immutable version, never the current definition draft.
    graph = version.graph
    latest = db.scalars(
        select(StepRun)
        .where(StepRun.execution_id == identity)
        .distinct(StepRun.node_id)
        .order_by(StepRun.node_id, StepRun.iteration.desc(), StepRun.created_at.desc(), StepRun.id)
        .options(load_only(*(getattr(StepRun, k) for k in FIELDS["steps"])))
    ).all()
    edges = run.checkpoint_json.get("edges", {})
    return {
        "source": "generic",
        "run": fields(run, RUN),
        "version": fields(version, ("id", "definition_id", "number", "name", "graph_hash")),
        "graph": {
            "entry_node": graph["entry_node"],
            "nodes": [{"id": node["id"], "type": node["type"]} for node in graph["nodes"]],
            "edges": [
                {**edge, "state": edges.get(str(i), "pending")}
                for i, edge in enumerate(graph.get("edges", []))
            ],
        },
        "latest_steps": [fields(row, FIELDS["steps"]) for row in latest],
        "checkpoint": preview(
            {key: run.checkpoint_json.get(key) for key in ("quality", "parallel_regions")}
        ),
        "usage_source": "Per-attempt usage only; legacy projections and events are excluded.",
    }


def query_records(db, identity, kind, step_id=None):
    execution(db, identity)
    model = MODELS[kind]
    if step_id is not None:
        if (
            db.scalar(
                select(StepRun.id).where(StepRun.id == step_id, StepRun.execution_id == identity)
            )
            is None
        ):
            raise HTTPException(404, "Step run not found")
    if kind == "attempts" and step_id is None:
        raise HTTPException(422, "Select a step to inspect attempts")
    if kind in {"attempts", "tools"}:
        query = (
            select(model)
            .join(StepRun, StepRun.id == model.step_run_id)
            .where(StepRun.execution_id == identity)
        )
    else:
        query = select(model).where(model.execution_id == identity)
    if step_id is not None:
        query = (
            query.where((model.id if kind == "steps" else model.step_run_id) == step_id)
            if (kind != "events")
            else query.where(model.entity_id == step_id)
        )
    return query, model


def records(db, identity, kind, step_id, offset, limit):
    query, model = query_records(db, identity, kind, step_id)
    names = FIELDS[kind]
    query = query.options(load_only(*(getattr(model, key) for key in names)))
    if kind == "attempts":
        query = query.order_by(model.number, model.id)
    else:
        query = query.order_by(model.created_at, model.id)
    return page(db, query, lambda row: fields(row, names), offset, limit)


def detail(db, identity, kind, record_id, step_id=None):
    query, model = query_records(db, identity, kind, step_id)
    item = db.scalar(query.where(model.id == record_id))
    if item is None:
        raise HTTPException(404, "Trace record not found")
    result = {"record": fields(item, FIELDS[kind]), "payloads": {}}
    payloads = {
        "steps": ("input_json", "output_json", "error_message"),
        "attempts": ("input_json", "output_json", "error_message"),
        "events": ("details",),
        "tools": ("request_json", "result_json", "reconciliation"),
        "approvals": ("payload_json", "review_json", "human_feedback"),
    }[kind]
    result["payloads"] = {key: preview(getattr(item, key), 64000) for key in payloads}
    if kind == "steps":
        run = execution(db, identity)
        version = db.scalar(select(WorkflowVersion).where(WorkflowVersion.id == run.version_id))
        node = next((n for n in version.graph["nodes"] if n["id"] == item.node_id), None)
        result["payloads"].update(
            node=preview(node, 64000), runtime=preview(run.runtime_config.get(item.node_id), 64000)
        )
    if kind == "attempts":
        from src.services.llm_tool_execution import attempt_metadata

        metadata = attempt_metadata(db, item)
        result["usage"] = (
            None
            if metadata is None
            else {
                key: metadata.get(key)
                for key in (
                    "model",
                    "prompt_version_id",
                    "prompt_version",
                    "input_tokens",
                    "output_tokens",
                    "total_tokens",
                    "estimated_cost_usd",
                    "usage_complete",
                    "latency_ms",
                    "unconfirmed_cost_reservation_usd",
                )
            }
        )
        result["payloads"]["llm_usage"] = preview(metadata, 64000)
    return result


def run_payload(db, identity):
    run = execution(db, identity)
    return {
        key: preview(getattr(run, key), 64000)
        for key in ("input_json", "output_json", "error_message", "cancel_reason")
    }


def legacy_run(db, identity):
    run = db.scalar(select(WorkflowRun).where(WorkflowRun.id == identity))
    if run is None:
        raise HTTPException(404, "Historical run not found")
    canonical = db.scalar(
        select(WorkflowExecution.id).where(WorkflowExecution.legacy_run_id == identity)
    )
    return run, canonical


def legacy_overview(db, identity):
    run, canonical = legacy_run(db, identity)
    if canonical:
        return {"source": "generic", "execution_id": canonical}
    return {
        "source": "legacy",
        "run": fields(
            run,
            (
                "id",
                "status",
                "workflow_type",
                "run_mode",
                "created_at",
                "completed_at",
                "total_tokens",
                "total_cost",
                "latency_ms",
            ),
        ),
        "usage_source": "Historical run totals; AgentStep breakdowns are not extra charges.",
    }


def legacy_steps(db, identity, offset, limit, record_id=None):
    _, canonical = legacy_run(db, identity)
    if canonical:
        raise HTTPException(409, "Use the canonical generic execution trace")
    query = select(AgentStep).where(AgentStep.workflow_run_id == identity)
    if record_id:
        item = db.scalar(query.where(AgentStep.id == record_id))
        if item is None:
            raise HTTPException(404, "Historical step not found")
        return {
            "record": fields(item, LEGACY),
            "payloads": {
                key: preview(getattr(item, key), 64000)
                for key in ("input_json", "output_json", "error_message")
            },
        }
    query = query.options(load_only(*(getattr(AgentStep, key) for key in LEGACY)))
    return page(
        db,
        query.order_by(AgentStep.step_order, AgentStep.id),
        lambda row: fields(row, LEGACY),
        offset,
        limit,
    )
