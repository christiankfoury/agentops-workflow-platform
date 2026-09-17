"""Stable logical identity across recovery runs; never copy approval decisions."""

from copy import deepcopy

from sqlalchemy import select

from src.models.execution_recovery import ExecutionRecovery
from src.models.llm_conversation import LLMConversation
from src.models.tool import ToolExecution
from src.models.workflow_execution import StepRun
from src.services.graph_expressions import ExecutionError


def ancestors(db, identity):
    result = [identity]
    for _ in range(100):
        parent = db.scalar(
            select(ExecutionRecovery.source_id).where(
                ExecutionRecovery.execution_id == result[-1],
            )
        )
        if parent is None:
            return result
        if parent in result:
            break
        result.append(parent)
    raise ExecutionError("recovery_limit", "Recovery lineage exceeds its safety bound")


def source_step(db, run, node_id, branch, iteration):
    for identity in ancestors(db, run.id)[1:]:
        row = db.scalar(
            select(StepRun).where(
                StepRun.execution_id == identity,
                StepRun.node_id == node_id,
                StepRun.branch == branch,
                StepRun.iteration == iteration,
            )
        )
        if row is not None:
            return row
    return None


def step_history(db, step):
    result = [step]
    while result[-1].recovered_from_id:
        prior = db.get(StepRun, result[-1].recovered_from_id)
        if prior is None or len(result) >= 100 or prior.id in {row.id for row in result}:
            raise ExecutionError("recovery_limit", "Logical recovery provenance is unavailable")
        result.append(prior)
    return result


def effect_identity(db, step, call_id, fingerprint, *, approved_call=False, version_id=None):
    history = step_history(db, step)
    if approved_call and len(history) > 1:
        # LLM write calls are bound to an approval UUID. A fresh approval must not
        # manufacture a second logical action for the same approved arguments.
        prior = db.scalar(
            select(ToolExecution)
            .where(
                ToolExecution.step_run_id.in_([row.id for row in history]),
                ToolExecution.request_fingerprint == fingerprint,
                ToolExecution.call_id.like("approval:%"),
            )
            .order_by(ToolExecution.created_at)
            .limit(1)
        )
        if prior:
            return prior.effect_key
        if db.scalar(
            select(ToolExecution.id)
            .where(
                ToolExecution.step_run_id.in_([row.id for row in history[1:]]),
                ToolExecution.call_id.like("approval:%"),
                ToolExecution.version_id == version_id,
            )
            .limit(1)
        ):
            raise ExecutionError(
                "tool_input_conflict", "Recovery cannot change an approved logical action"
            )
    from src.services.tool_effects import digest

    return digest([str(history[-1].id), call_id])


def inherited_conversation(db, step_id, fingerprint, deadline):
    step = db.get(StepRun, step_id)
    for prior in step_history(db, step)[1:]:
        row = db.scalar(select(LLMConversation).where(LLMConversation.step_run_id == prior.id))
        if row is None:
            continue
        if row.fingerprint != fingerprint:
            raise ExecutionError(
                "tool_input_conflict", "Recovery inputs changed; use a new start and approval"
            )
        state = deepcopy(row.state)
        # The explicit recovery has a new time window. Spent cost, provider rounds,
        # call identities and unknown reservations remain charged to this lineage.
        state["deadline"] = deadline
        return state
    return None
