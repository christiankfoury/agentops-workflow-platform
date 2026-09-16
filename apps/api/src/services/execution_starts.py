import hashlib
import json
from datetime import timedelta

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.models.execution_start import ExecutionStart
from src.models.workflow_execution import ExecutionEvent, WorkflowExecution
from src.schemas.workflow_graph import WorkflowGraph
from src.services.audit import record_audit
from src.services.durable_queue import enqueue
from src.services.execution_config import snapshot_config
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


def start_execution(db, body, *, legacy_run=None):
    """Atomically accept a pending execution and its first durable job."""
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
        graph = WorkflowGraph.model_validate(selected.graph)
        try:
            validate_data(body.input, graph.input_schema)
        except ValidationError as error:
            raise HTTPException(422, validation_errors(error)) from error
        if legacy_run is not None:
            legacy_run.created_by_user_id = principal.user_id
            db.add(legacy_run)
            db.flush()
        run = WorkflowExecution(
            version_id=selected.id,
            input_json=body.input,
            created_by_user_id=principal.user_id,
            legacy_run_id=legacy_run.id if legacy_run is not None else None,
            business_type=legacy_run.workflow_type.value if legacy_run is not None else None,
            run_mode=legacy_run.run_mode.value if legacy_run is not None else None,
            runtime_config=snapshot_config(db, selected, graph),
            deadline_at=db.scalar(select(func.clock_timestamp()))
            + timedelta(
                seconds=graph.overall_timeout_seconds,
            ),
        )
        db.add(run)
        db.flush()
        db.add(ExecutionStart(key=body.idempotency_key, fingerprint=digest, execution_id=run.id))
        enqueue(db, run, 0)
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
        if legacy_run is not None:
            from src.services.business_projection import sync

            sync(db, run)
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
