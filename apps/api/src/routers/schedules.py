import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.schedule import ScheduleFire, WorkflowSchedule
from src.schemas.schedule import ScheduleCreate, ScheduleUpdate
from src.services import schedules

router = APIRouter()


def configuration(item):
    # Commit expires ORM attributes; materialize the response while the session
    # is open instead of letting generic serialization inspect an empty __dict__.
    return {column.key: getattr(item, column.key) for column in item.__table__.columns}


@router.get("")
def listing(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(WorkflowSchedule)
        .order_by(WorkflowSchedule.created_at, WorkflowSchedule.id)
        .offset(offset)
        .limit(limit)
    ).all()


@router.post("", status_code=201)
def create(body: ScheduleCreate, db: Session = Depends(get_db)):
    return configuration(schedules.create(db, body))


@router.get("/{identity}")
def detail(identity: uuid.UUID, db: Session = Depends(get_db)):
    return schedules.get_schedule(db, identity)


@router.put("/{identity}")
def update(identity: uuid.UUID, body: ScheduleUpdate, db: Session = Depends(get_db)):
    return configuration(schedules.update(db, identity, body))


@router.get("/{identity}/fires")
def fires(
    identity: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    schedules.get_schedule(db, identity)
    return db.scalars(
        select(ScheduleFire)
        .where(ScheduleFire.schedule_id == identity)
        .order_by(ScheduleFire.scheduled_at.desc(), ScheduleFire.id)
        .offset(offset)
        .limit(limit)
    ).all()
