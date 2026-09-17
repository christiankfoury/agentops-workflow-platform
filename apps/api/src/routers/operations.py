import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.services import operations, operations_pulse
from src.services.permissions import authorize
from src.services.tenancy import tenant_id

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Kind = Literal[
    "all",
    "queued",
    "running",
    "failed",
    "completed",
    "cancelled",
    "retrying",
    "dead_letter",
    "stale",
]
View = Literal["execution", "run", "approval", "executions", "runs", "approvals", "operations"]


def summary(db):
    authorize(db, "read")
    owner = tenant_id(db)
    # End the read-only authorization transaction before taking a consistent
    # snapshot. Holding it while borrowing another connection can starve the pool.
    db.rollback()
    conn = db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    return operations.snapshot(conn, owner)


@router.get("")
def overview(db: Database):
    return summary(db)


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(db: Database):
    return PlainTextResponse(
        operations.prometheus(summary(db)), media_type="text/plain; version=0.0.4"
    )


@router.get("/jobs")
def jobs(
    db: Database,
    kind: Kind = "all",
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 25,
):
    authorize(db, "read")
    return operations.job_page(db.connection(), tenant_id(db), kind, offset, limit)


@router.get("/pulse")
def pulse(db: Database, kind: View, identity: uuid.UUID | None = None):
    authorize(db, "read")
    return operations_pulse.pulse(db, kind, identity)
