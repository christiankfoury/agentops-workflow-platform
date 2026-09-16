import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.services import execution_traces as traces

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Offset = Annotated[int, Query(ge=0, le=1_000_000)]
Limit = Annotated[int, Query(ge=1, le=50)]
Kind = Literal["steps", "attempts", "events", "tools", "approvals"]


@router.get("")
def listing(db: Database, offset: Offset = 0, limit: Limit = 25):
    return traces.listing(db, offset, limit)


@router.get("/legacy/{identity}")
def legacy(identity: uuid.UUID, db: Database):
    return traces.legacy_overview(db, identity)


@router.get("/legacy/{identity}/steps")
def legacy_steps(identity: uuid.UUID, db: Database, offset: Offset = 0, limit: Limit = 25):
    return traces.legacy_steps(db, identity, offset, limit)


@router.get("/legacy/{identity}/steps/{record_id}")
def legacy_detail(identity: uuid.UUID, record_id: uuid.UUID, db: Database):
    return traces.legacy_steps(db, identity, 0, 1, record_id)


@router.get("/{identity}")
def overview(identity: uuid.UUID, db: Database):
    return traces.overview(db, identity)


@router.get("/{identity}/payloads")
def payloads(identity: uuid.UUID, db: Database):
    return traces.run_payload(db, identity)


@router.get("/{identity}/records/{kind}")
def records(
    identity: uuid.UUID,
    kind: Kind,
    db: Database,
    step_id: uuid.UUID | None = None,
    offset: Offset = 0,
    limit: Limit = 25,
):
    return traces.records(db, identity, kind, step_id, offset, limit)


@router.get("/{identity}/records/{kind}/{record_id}")
def detail(
    identity: uuid.UUID,
    kind: Kind,
    record_id: uuid.UUID,
    db: Database,
    step_id: uuid.UUID | None = None,
):
    return traces.detail(db, identity, kind, record_id, step_id)
