"""Worker-owned effect ledger. Remote exactly-once behavior requires adapter guarantees."""

import hashlib
import json
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from time import monotonic
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config import settings
from src.models.identity import Organization
from src.models.tool import ToolCredential, ToolDefinition, ToolExecution, ToolVersion
from src.models.workflow_execution import StepAttempt, StepRun, WorkflowExecution
from src.schemas.tool import ToolContract, bounded, redact
from src.services.audit import record_audit
from src.services.durable_queue import jobs, locked_claim
from src.services.execution_control import AbortSignal
from src.services.execution_records import execution, pinned_node
from src.services.graph_expressions import ExecutionError
from src.services.graph_validation import validate_data
from src.services.identity import Principal
from src.services.permissions import authorize
from src.services.retry_runtime import runtime_now
from src.services.tenancy import bind_tenant
from src.services.tool_catalog import get


@dataclass(frozen=True)
class Reconciliation:
    outcome: Literal["succeeded", "absent", "unknown"]
    result: dict | None = None


@dataclass(frozen=True)
class ToolAdapter:
    invoke: Callable
    recovery: Literal["none", "idempotent", "reconcile"] = "none"
    reconcile: Callable | None = None
    side_effecting: bool | Callable = True

    def __post_init__(self):
        if self.recovery not in {"none", "idempotent", "reconcile"}:
            raise ValueError("Adapter recovery guarantee is invalid")


# Registration is server code, never graph/API input. Concrete adapters follow in 87–89.
ADAPTERS: dict[str, ToolAdapter] = {}
ERROR_CODES = {
    "tool_timeout",
    "tool_unavailable",
    "tool_rate_limit",
    "tool_response_invalid",
    "tool_denied",
    "tool_failed",
    "tool_disabled",
    "tool_deadline",
    "tool_owner_lost",
    "execution_aborted",
    "tool_credential_changed",
    "tool_credential_unavailable",
    "tool_credential_revoked",
}


class ToolFailure(Exception):
    def __init__(self, code="tool_failed", *, uncertain=True):
        self.code = code if code in ERROR_CODES else "tool_failed"
        self.uncertain = uncertain
        super().__init__(self.code)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@contextmanager
def serialized_claim(db, claim):
    """Serialize metadata against lifecycle changes without advancing its checkpoint."""
    if db.info.get("workflow_transaction"):
        raise ValueError("Tool metadata requires its own short transaction")
    try:
        run = db.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == claim.execution_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if run is None:
            raise ExecutionError("tool_owner_lost", "Worker execution is unavailable")
        yield run
        db.commit()
    except BaseException:
        db.rollback()
        raise


def worker_attempt(db, claim, attempt_id):
    row = locked_claim(db, claim)
    attempt = db.get(StepAttempt, attempt_id)
    step = db.get(StepRun, attempt.step_run_id) if attempt else None
    if (
        row is None
        or row["attempt_id"] != attempt_id
        or attempt is None
        or attempt.status != "running"
        or step.execution_id != claim.execution_id
    ):
        raise ExecutionError("tool_owner_lost", "Tool requires a live owned worker attempt")
    now = runtime_now(db)
    run = execution(db, claim.execution_id)
    if (attempt.deadline_at and now >= attempt.deadline_at) or (
        run.deadline_at and now >= run.deadline_at
    ):
        raise ExecutionError("tool_deadline", "Tool execution deadline has elapsed")
    return step


def active_credential(db, contract):
    if contract.credential_ref is None:
        return None
    credential = db.scalar(
        select(ToolCredential)
        .where(ToolCredential.id == contract.credential_ref)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    if credential is None or not credential.active:
        raise ExecutionError("tool_credential_revoked", "Tool credential is unavailable")
    return credential


def reserve(db, claim, attempt_id, version_id, arguments, call_id, adapters):
    with serialized_claim(db, claim) as run:
        step = worker_attempt(db, claim, attempt_id)
        if run.status != "running" or run.cancel_requested:
            raise ExecutionError("tool_owner_lost", "Execution cannot dispatch a tool")
        version = get(db, ToolVersion, version_id)
        definition = get(db, ToolDefinition, version.definition_id)
        node = pinned_node(db, run, step.node_id)
        if (
            node.type != "tool"
            or node.config.tool_id != version.definition_id
            or node.config.version != version.number
            or not definition.active
        ):
            raise ExecutionError("tool_contract_mismatch", "Tool is not pinned by this step")
        contract = ToolContract.model_validate(version.contract)
        if node.config.adapter != contract.adapter:
            raise ExecutionError("tool_contract_mismatch", "Tool adapter does not match")
        if not call_id or len(call_id) > 100:
            raise ExecutionError("tool_input_invalid", "Invalid logical tool call identity")
        bounded(arguments)
        validate_data(arguments, contract.input_schema)
        active_credential(db, contract)
        adapter = adapters.get(contract.adapter)
        if adapter is None:
            raise ExecutionError("tool_adapter_unavailable", "Tool adapter is not registered")
        actual_effect = (
            adapter.side_effecting(contract.options)
            if callable(adapter.side_effecting)
            else adapter.side_effecting
        )
        if actual_effect != contract.side_effecting:
            raise ExecutionError("tool_contract_mismatch", "Adapter effect policy does not match")
        key = digest([str(step.id), call_id])
        fingerprint = digest([str(version.id), arguments])
        effect = db.scalar(
            select(ToolExecution)
            .where(ToolExecution.effect_key == key)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if effect is None:
            effect = ToolExecution(
                version_id=version.id,
                step_run_id=step.id,
                attempt_id=attempt_id,
                call_id=call_id,
                effect_key=key,
                request_fingerprint=fingerprint,
                request_json=redact(arguments),
                attempts=0,
            )
            db.add(effect)
            db.flush()
        elif effect.request_fingerprint != fingerprint:
            raise ExecutionError("tool_input_conflict", "Logical tool input changed")
        if effect.status in {"succeeded", "reconciled"}:
            return effect.id, None, contract, adapter, False
        if effect.status == "pending" and effect.claim_token == claim.token:
            raise ExecutionError("tool_in_progress", "Logical tool call is already in progress")
        uncertain = effect.status == "unknown" or (effect.dispatched and effect.status == "pending")
        blocked = (
            uncertain and contract.side_effecting and adapter.recovery == "none"
        ) or effect.attempts >= contract.retry.max_attempts
        if effect.status == "failed" and effect.error_code not in contract.retry.retryable_errors:
            blocked = True
        if blocked:
            if uncertain:
                effect.status = "unknown"
            return effect.id, None, contract, adapter, False
        effect.status = "pending"
        effect.claim_token, effect.reservation_token = claim.token, uuid.uuid4()
        effect.dispatched = False
        effect.error_code = None
        return effect.id, effect.reservation_token, contract, adapter, uncertain


def dispatch(db, claim, attempt_id, effect_id, token, contract):
    with serialized_claim(db, claim) as run:
        worker_attempt(db, claim, attempt_id)
        effect = get(db, ToolExecution, effect_id, lock=True)
        if effect.reservation_token != token or effect.dispatched:
            raise ExecutionError("tool_owner_lost", "Tool reservation changed")
        organization = db.get(Organization, claim.organization_id)
        if run.cancel_requested or run.status != "running" or not organization.active:
            raise ExecutionError("tool_owner_lost", "Execution cannot dispatch a tool")
        version = get(db, ToolVersion, effect.version_id)
        definition = db.scalar(
            select(ToolDefinition)
            .where(ToolDefinition.id == version.definition_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if not definition.active:
            raise ExecutionError("tool_disabled", "Tool is disabled")
        credential = active_credential(db, contract)
        secret = ""
        if credential:
            value = settings.tool_credential_values.get(
                f"{claim.organization_id}/{credential.source_alias}"
            )
            if value is None or not value.get_secret_value():
                raise ExecutionError(
                    "tool_credential_unavailable", "Worker credential is unavailable"
                )
            secret = value.get_secret_value()
            binding = hashlib.pbkdf2_hmac("sha256", secret.encode(), effect.id.bytes, 200_000).hex()
            if effect.credential_digest is not None and effect.credential_digest != binding:
                raise ExecutionError(
                    "tool_credential_changed", "Tool credential changed after dispatch"
                )
            effect.credential_digest = binding
            record_audit(
                db,
                Principal("worker"),
                "tool.credential.use",
                "tool_credential",
                credential.id,
                effect_key=effect.effect_key,
            )
        effect.dispatched = True
        effect.attempts += 1
        now = runtime_now(db)
        remaining = min(
            [
                contract.timeout_seconds,
                *(
                    (deadline - now).total_seconds()
                    for deadline in [run.deadline_at, db.get(StepAttempt, attempt_id).deadline_at]
                    if deadline
                ),
            ]
        )
        if remaining <= 0:
            raise ExecutionError("tool_deadline", "Tool execution deadline has elapsed")
        return secret, effect.effect_key, remaining


def finish(engine, claim, effect_id, token, status, *, result=None, error=None, latency=None):
    with Session(engine) as db:
        bind_tenant(db, claim.organization_id)
        effect = get(db, ToolExecution, effect_id, lock=True)
        if effect.reservation_token != token:
            raise ExecutionError("tool_owner_lost", "Tool outcome was superseded")
        # Confirmed remote receipts remain useful even if the workflow was cancelled.
        # This records an effect only; the workflow's own fence controls its output.
        effect.status, effect.result_json, effect.error_code = status, result, error
        effect.latency_ms, effect.reservation_token = latency, None
        if status == "reconciled":
            effect.reconciliation = {"method": "adapter", "outcome": "succeeded"}
        record_audit(
            db,
            Principal("worker"),
            "tool.outcome",
            "tool_execution",
            effect.id,
            status=status,
            error_code=error,
        )
        db.commit()


def record_reconciliation(engine, claim, effect_id, token, outcome):
    if outcome not in {"succeeded", "absent", "unknown"}:
        raise ToolFailure("tool_response_invalid")
    with Session(engine) as db:
        bind_tenant(db, claim.organization_id)
        effect = get(db, ToolExecution, effect_id, lock=True)
        if effect.reservation_token != token:
            raise ExecutionError("tool_owner_lost", "Tool reconciliation was superseded")
        effect.reconciliation = {"method": "adapter", "outcome": outcome}
        record_audit(
            db, Principal("worker"), "tool.reconcile", "tool_execution", effect.id, outcome=outcome
        )
        db.commit()


def live_effect_owner(db, effect):
    return (
        db.connection()
        .execute(
            select(jobs.c.id).where(
                jobs.c.organization_id == effect.organization_id,
                jobs.c.claim_token == effect.claim_token,
                jobs.c.status == "running",
                jobs.c.lease_expires_at > func.clock_timestamp(),
            )
        )
        .first()
        is not None
    )


def recover_effects(engine):
    """Expose abandoned dispatches even when workflow retry/recovery is exhausted."""
    effects = ToolExecution.__table__
    live = (
        select(jobs.c.id)
        .where(
            jobs.c.organization_id == effects.c.organization_id,
            jobs.c.claim_token == effects.c.claim_token,
            jobs.c.status == "running",
            jobs.c.lease_expires_at > func.clock_timestamp(),
        )
        .exists()
    )
    with engine.connect() as conn:
        candidates = conn.execute(
            select(effects.c.id, effects.c.organization_id)
            .where(
                effects.c.status == "pending",
                effects.c.dispatched.is_(True),
                ~live,
            )
            .limit(100)
        ).all()
    for identity, organization in candidates:
        with Session(engine) as db:
            bind_tenant(db, organization)
            effect = get(db, ToolExecution, identity, lock=True)
            if (
                effect.status == "pending"
                and effect.dispatched
                and not live_effect_owner(db, effect)
            ):
                effect.status = "unknown"
                record_audit(db, Principal("worker"), "tool.uncertain", "tool_execution", identity)
                db.commit()


def execute_tool(
    engine, claim, attempt_id, version_id, arguments, *, call_id="tool", adapters=None, control=None
):
    adapters = ADAPTERS if adapters is None else adapters
    control = control or AbortSignal()
    arguments = deepcopy(arguments)
    with Session(engine) as db:
        bind_tenant(db, claim.organization_id)
        identity, token, contract, adapter, uncertain = reserve(
            db, claim, attempt_id, version_id, arguments, call_id, adapters
        )
        if token is None:
            effect = get(db, ToolExecution, identity)
            if effect.status in {"succeeded", "reconciled"} and not effect.error_code:
                return deepcopy(effect.result_json)
            raise ExecutionError(
                effect.error_code or "tool_resolution_required",
                "Tool needs resolution or its retry budget is exhausted",
            )
    started, dispatched = monotonic(), False
    try:
        control.raise_if_aborted()
        with Session(engine) as db:
            bind_tenant(db, claim.organization_id)
            secret, key, budget = dispatch(db, claim, attempt_id, identity, token, contract)
        dispatched = True
        kwargs = dict(
            arguments=arguments,
            options=deepcopy(contract.options),
            secret=secret,
            effect_key=key,
            timeout_seconds=budget,
            control=control,
        )
        status = "succeeded"
        control.raise_if_aborted()
        if uncertain and contract.side_effecting and adapter.recovery == "reconcile":
            recovery = (
                adapter.reconcile(**kwargs) if adapter.reconcile else Reconciliation("unknown")
            )
            record_reconciliation(engine, claim, identity, token, recovery.outcome)
            if recovery.outcome == "unknown":
                raise ToolFailure()
            if recovery.outcome == "succeeded":
                result, status = recovery.result, "reconciled"
            else:
                uncertain = False  # Adapter proved that no prior or pending effect exists.
                control.raise_if_aborted()
                kwargs["timeout_seconds"] = budget - (monotonic() - started)
                if kwargs["timeout_seconds"] <= 0:
                    raise ToolFailure("tool_timeout")
                result = adapter.invoke(**kwargs)
        else:
            result = adapter.invoke(**kwargs)
        if monotonic() - started > budget:
            raise ToolFailure("tool_timeout")
        try:
            bounded(result)
            result = redact(result, secret)
            validate_data(result, contract.output_schema)
        except (ValueError, TypeError):
            raise ToolFailure("tool_response_invalid") from None
    except Exception as error:
        possible = contract.side_effecting and (
            uncertain or (dispatched and (not isinstance(error, ToolFailure) or error.uncertain))
        )
        code = (
            error.code
            if isinstance(error, (ToolFailure, ExecutionError)) and error.code in ERROR_CODES
            else "tool_failed"
        )
        finish(
            engine,
            claim,
            identity,
            token,
            "unknown" if possible else "failed",
            error=code,
            latency=int((monotonic() - started) * 1000),
        )
        raise ExecutionError(code, "Tool failed; consult its redacted effect record") from None
    finish(
        engine,
        claim,
        identity,
        token,
        status,
        result=result,
        latency=int((monotonic() - started) * 1000),
    )
    control.raise_if_aborted()
    return result


def resolve(db, identity, body):
    principal = authorize(db, "tool.resolve", lock=True)
    effect = get(db, ToolExecution, identity, lock=True)
    if effect.status == "pending" and effect.dispatched and not live_effect_owner(db, effect):
        effect.status = "unknown"
    if effect.status != "unknown":
        raise HTTPException(409, "Only uncertain effects require explicit resolution")
    contract = ToolContract.model_validate(get(db, ToolVersion, effect.version_id).contract)
    result = redact(body.result)
    if body.succeeded:
        try:
            bounded(result)
            validate_data(result, contract.output_schema)
        except (ValueError, TypeError) as error:
            raise HTTPException(422, "Resolution must match the tool output contract") from error
    elif result is not None:
        raise HTTPException(422, "Failed resolution cannot include a successful result")
    effect.status, effect.result_json = "reconciled", result
    effect.error_code = None if body.succeeded else "tool_resolved_failed"
    effect.reservation_token = None
    effect.reconciliation = {
        "method": "operator",
        "succeeded": body.succeeded,
        "evidence": body.evidence,
    }
    record_audit(
        db, principal, "tool.resolve", "tool_execution", effect.id, succeeded=body.succeeded
    )
    db.commit()
    return effect
