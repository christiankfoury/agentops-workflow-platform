import hashlib
import json

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.models.execution_start import ExecutionStart
from src.models.workflow_execution import ExecutionEvent, WorkflowExecution
from src.schemas.workflow_graph import WorkflowGraph
from src.services.audit import record_audit
from src.services.execution_records import execution
from src.services.graph_validation import validate_data
from src.services.permissions import authorize
from src.services.workflow_definitions import (
    definition,
    require_runnable_version,
    validation_errors,
)


def fingerprint(body):
    # Hash the requested version selection, not a newly resolved published pointer.
    request = body.model_dump(mode="json", exclude={"idempotency_key"})
    return hashlib.sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def existing_start(db, key, digest):
    receipt = db.scalar(select(ExecutionStart).where(ExecutionStart.key == key))
    if receipt is None:
        return None
    if receipt.fingerprint != digest:
        raise HTTPException(409, "Idempotency key was already used for a different request")
    return execution(db, receipt.execution_id)


def start_execution(db, body):
    """Persist a pending start only; no in-process dispatch or queue claim."""
    try:
        principal = authorize(db, "workflow.start", lock=True)
        digest = fingerprint(body)
        accepted = existing_start(db, body.idempotency_key, digest)
        if accepted:
            db.commit()
            return accepted
        item = definition(db, body.definition_id, lock=True)
        # A competing start may have committed while this request waited for publication's lock.
        accepted = existing_start(db, body.idempotency_key, digest)
        if accepted:
            db.commit()
            return accepted
        selected_id = body.version_id or item.published_version_id
        if selected_id is None:
            raise HTTPException(409, "Workflow definition has no published version")
        selected = require_runnable_version(db, item.id, selected_id)
        try:
            validate_data(body.input, WorkflowGraph.model_validate(selected.graph).input_schema)
        except ValidationError as error:
            raise HTTPException(422, validation_errors(error)) from error
        run = WorkflowExecution(
            version_id=selected.id, input_json=body.input, created_by_user_id=principal.user_id
        )
        db.add(run)
        db.flush()
        db.add(ExecutionStart(key=body.idempotency_key, fingerprint=digest, execution_id=run.id))
        db.add(
            ExecutionEvent(
                execution_id=run.id,
                entity_type="workflow_executions",
                entity_id=run.id,
                to_status="pending",
            )
        )
        record_audit(
            db,
            principal,
            "workflow.start",
            "workflow_execution",
            run.id,
            version_id=str(selected.id),
            definition_id=str(item.id),
        )
        db.commit()
        return run
    except IntegrityError:
        # The organization/key unique constraint arbitrates starts across definitions too.
        db.rollback()
        try:
            authorize(db, "workflow.start", lock=True)
            accepted = existing_start(db, body.idempotency_key, digest)
            if accepted:
                db.commit()
                return accepted
            raise
        except BaseException:
            db.rollback()
            raise
    except BaseException:
        db.rollback()
        raise
