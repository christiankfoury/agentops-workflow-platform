"""Engine-owned retry decisions using pinned policy and retained attempt numbers."""

import random
from datetime import timedelta

from sqlalchemy import func, select

from src.models.workflow_execution import TERMINAL, StepAttempt, StepRun
from src.services.execution_records import pinned_node
from src.services.workflow_state import transition_execution_entity as transition

PERMANENT_ERRORS = {
    "llm_tool_call_invalid",
    "llm_call_limit",
    "llm_round_limit",
    "llm_cost_limit",
    "llm_budget_unavailable",
    "llm_conversation_limit",
    "provider_rejected",
    "provider_refused",
    "provider_incomplete",
    "provider_response_invalid",
    "configuration_missing",
    "review_invalid",
    "quality_revision_busy",
    "binding_missing",
    "input_invalid",
    "output_invalid",
    "expression_range",
    "route_invalid",
    "unsupported_executor",
    "graph_stalled",
    "run_deadline",
    "tool_approval_required",
    "tool_denied",
    "tool_input_invalid",
    "tool_response_invalid",
    "tool_contract_mismatch",
    "tool_input_conflict",
    "tool_credential_changed",
    "tool_credential_revoked",
    "tool_resolution_required",
}


def runtime_now(db):
    return db.scalar(select(func.clock_timestamp()))


def retry_decision(
    policy,
    number,
    code,
    now,
    deadline=None,
    *,
    sample=None,
    abandoned=False,
    retry_not_before=None,
):
    retryable = code not in PERMANENT_ERRORS and (
        code in policy.retryable_errors or (abandoned and code == "worker_abandoned")
    )
    classification = "retryable" if retryable else "permanent"
    if deadline is not None and now >= deadline:
        return "permanent", None, "run_deadline"
    if not retryable:
        return classification, None, code
    if number >= policy.max_attempts:
        return classification, None, "retry_exhausted"
    sample = random.random() if sample is None else sample
    if not 0 <= sample <= 1:
        raise ValueError("Jitter sample must be between zero and one")
    base = min(
        policy.max_delay_seconds,
        policy.initial_delay_seconds * policy.backoff_factor ** (number - 1),
    )
    delay = min(
        policy.max_delay_seconds,
        base * (1 - policy.jitter_fraction + 2 * policy.jitter_fraction * sample),
    )
    due = now + timedelta(seconds=delay)
    if retry_not_before is not None:
        due = max(due, retry_not_before)
    if deadline is not None and due >= deadline:
        return classification, None, "run_deadline"
    return classification, due, code


def fail_attempt(db, run, step, attempt, error, now):
    policy = pinned_node(db, run, step.node_id).retry
    classification, due, code = retry_decision(
        policy,
        attempt.number,
        error.code,
        now,
        run.deadline_at,
        retry_not_before=error.retry_not_before,
    )
    attempt.error_classification = classification
    attempt.error_code = error.code
    attempt.error_message = str(error)[:4000]
    transition(db, run, attempt, "failed")
    step.error_code = code
    step.error_message = str(error)[:4000] if code == error.code else code.replace("_", " ")
    step.next_attempt_at = due
    if due is not None:
        transition(db, run, step, "retrying")
    else:
        transition(db, run, step, "failed")
        run.error_code = code
        run.error_message = step.error_message
        if run.checkpoint_json.get("parallel_mode"):
            from src.services.parallel_runtime import cancel_siblings

            cancel_siblings(db, run)
        transition(db, run, run, "failed")


def expire_execution(db, run):
    from src.services.approval_runtime import close_pending

    close_pending(db, run, "expired")
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
            attempt.error_classification = "permanent"
            attempt.error_code = "run_deadline"
            attempt.error_message = "Workflow deadline expired"
            transition(db, run, attempt, "failed")
        step.next_attempt_at = None
        step.error_code = "run_deadline"
        step.error_message = "Workflow deadline expired"
        transition(db, run, step, "failed")
    run.error_code = "run_deadline"
    run.error_message = "Workflow deadline expired"
    transition(db, run, run, "failed")
