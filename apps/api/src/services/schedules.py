"""Replica-safe schedule firing through the shared durable start transaction."""

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.schedule import ScheduleFire, WorkflowSchedule
from src.models.workflow_execution import TERMINAL, WorkflowExecution
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.workflow_graph import WorkflowGraph
from src.services.audit import record_audit
from src.services.cron_schedule import next_fire
from src.services.execution_starts import start_execution
from src.services.graph_validation import validate_data
from src.services.identity import Principal
from src.services.permissions import authorize
from src.services.retry_runtime import runtime_now
from src.services.tenancy import bind_tenant
from src.services.webhooks import principal_for
from src.services.workflow_definitions import definition, require_runnable_version, version

log = logging.getLogger(__name__)


def get_schedule(db, identity, *, lock=False):
    query = select(WorkflowSchedule).where(WorkflowSchedule.id == identity)
    if lock:
        query = query.with_for_update()
    item = db.scalar(query.execution_options(populate_existing=True))
    if item is None:
        raise HTTPException(404, "Schedule not found")
    return item


def validate_target(db, body):
    item = definition(db, body.definition_id)
    principal_for(db, body.service_principal_id, active=body.enabled)
    if body.version_id:
        version(db, item.id, body.version_id)
    if body.enabled:
        selected = body.version_id or item.published_version_id
        if selected is None:
            raise HTTPException(409, "Schedule requires a published workflow version")
        chosen = require_runnable_version(db, item.id, selected)
        try:
            validate_data(body.input, WorkflowGraph.model_validate(chosen.graph).input_schema)
        except ValueError as error:
            raise HTTPException(422, "Schedule input does not match the workflow schema") from error


def create(db, body):
    actor = authorize(db, "trigger.manage", lock=True)
    validate_target(db, body)
    try:
        due = next_fire(body.cron, body.timezone, runtime_now(db))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    item = WorkflowSchedule(**body.model_dump(), next_fire_at=due)
    db.add(item)
    db.flush()
    record_audit(db, actor, "schedule.create", "workflow_schedule", item.id, revision=item.revision)
    db.commit()
    return item


def update(db, identity, body):
    actor = authorize(db, "trigger.manage", lock=True)
    item = get_schedule(db, identity, lock=True)
    if item.revision != body.expected_revision:
        raise HTTPException(409, "Schedule configuration changed; reload before editing")
    validate_target(db, body)
    data = body.model_dump(exclude={"expected_revision"})
    reset = any(
        getattr(item, key) != value for key, value in data.items() if key not in {"name", "enabled"}
    )
    if reset:
        try:
            item.next_fire_at = next_fire(body.cron, body.timezone, runtime_now(db))
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
    for key, value in data.items():
        setattr(item, key, value)
    item.revision += 1
    record_audit(
        db,
        actor,
        "schedule.update",
        "workflow_schedule",
        item.id,
        revision=item.revision,
        enabled=item.enabled,
        pending_tick_reset=reset,
    )
    db.commit()
    return item


def fire_schedule(engine, identity, owner, *, now=None):
    with Session(engine) as db:
        bind_tenant(db, owner)
        try:
            item = db.scalar(
                select(WorkflowSchedule)
                .where(WorkflowSchedule.id == identity, WorkflowSchedule.enabled.is_(True))
                .with_for_update(skip_locked=True)
            )
            if item is None:
                return False
            moment = now or runtime_now(db)
            if item.next_fire_at > moment:
                return False
            due = item.next_fire_at
            upcoming = next_fire(item.cron, item.timezone, moment)
            fire = ScheduleFire(
                id=uuid.uuid4(),
                schedule_id=item.id,
                revision=item.revision,
                scheduled_at=due,
                decided_at=moment,
                coalesced=next_fire(item.cron, item.timezone, due) <= moment,
                status="rejected",
                service_principal_id=item.service_principal_id,
            )
            actor = Principal("system", organization_id=owner)
            try:
                with db.begin_nested():
                    actor = principal_for(db, item.service_principal_id)
                    db.info["principal"] = actor
                    active = (
                        db.get(WorkflowExecution, item.active_execution_id)
                        if item.active_execution_id
                        else None
                    )
                    if active is not None and active.status not in TERMINAL:
                        fire.status, fire.error_code = "skipped", "active_run"
                    else:
                        run = start_execution(
                            db,
                            ExecutionStartRequest(
                                definition_id=item.definition_id,
                                version_id=item.version_id,
                                input=item.input,
                                idempotency_key=f"schedule:{fire.id}",
                            ),
                            commit=False,
                        )
                        fire.status, fire.execution_id, fire.version_id = (
                            "accepted",
                            run.id,
                            run.version_id,
                        )
                        item.active_execution_id = run.id
            except HTTPException as error:
                fire.error_code = (
                    "principal_unavailable"
                    if error.status_code == 403
                    else "input_invalid"
                    if error.status_code == 422
                    else "workflow_unavailable"
                )
            item.next_fire_at, item.last_fire_at = upcoming, moment
            item.last_status, item.last_error_code = fire.status, fire.error_code
            db.add(fire)
            db.flush()
            record_audit(
                db,
                actor,
                "schedule.fire",
                "schedule_fire",
                fire.id,
                schedule_id=str(item.id),
                revision=fire.revision,
                outcome=fire.status,
                error_code=fire.error_code,
                scheduled_at=due.isoformat(),
                coalesced=fire.coalesced,
            )
            db.commit()
            return True
        except BaseException:
            db.rollback()
            raise


def fire_due_schedules(engine, limit=32, *, now=None):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Schedule batch must be between 1 and 100")
    table = WorkflowSchedule.__table__
    with engine.connect() as conn:
        moment = now or conn.scalar(select(func.clock_timestamp()))
        # Discovery contains only server-owned IDs; each claim binds its own tenant.
        rows = conn.execute(
            select(table.c.id, table.c.organization_id)
            .where(table.c.enabled.is_(True), table.c.next_fire_at <= moment)
            .order_by(table.c.next_fire_at, table.c.id)
            .limit(limit)
        ).all()
    processed = 0
    for identity, owner in rows:
        try:
            processed += fire_schedule(engine, identity, owner, now=now)
        except Exception as error:
            # No raw input/configuration or database exception text enters logs.
            log.error("Schedule %s transaction rolled back: %s", identity, type(error).__name__)
    return processed
