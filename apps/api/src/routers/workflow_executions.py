import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.agent_step import AgentStep
from src.models.durable_job import DurableJob
from src.models.workflow_execution import ExecutionEvent, StepAttempt, StepRun, WorkflowExecution
from src.models.workflow_run import WorkflowRun
from src.schemas.durable_job import JobRead
from src.schemas.execution_cancel import ExecutionCancelRead, ExecutionCancelRequest
from src.schemas.execution_start import ExecutionStartRead, ExecutionStartRequest
from src.schemas.workflow_execution import (
    ExecutionEventRead,
    ExecutionRead,
    LegacyTraceRead,
    StepAttemptRead,
    StepRunRead,
)
from src.services.execution_cancellation import cancel_execution
from src.services.execution_records import execution
from src.services.execution_starts import start_execution

router = APIRouter()


@router.post("", response_model=ExecutionStartRead, status_code=202)
def start(body: ExecutionStartRequest, db: Session = Depends(get_db)):
    return start_execution(db, body)


@router.get("", response_model=list[ExecutionRead])
def list_executions(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(WorkflowExecution)
        .order_by(
            WorkflowExecution.created_at.desc(),
            WorkflowExecution.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/legacy/{run_id}", response_model=LegacyTraceRead)
def legacy_trace(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.scalar(select(WorkflowRun).where(WorkflowRun.id == run_id))
    if run is None:
        raise HTTPException(404, "Historical workflow run not found")
    return {
        "source": "legacy",
        "run": run,
        "agent_steps": db.scalars(
            select(AgentStep)
            .where(
                AgentStep.workflow_run_id == run.id,
            )
            .order_by(AgentStep.step_order, AgentStep.id)
        ).all(),
    }


@router.get("/{execution_id}", response_model=ExecutionRead)
def detail(execution_id: uuid.UUID, db: Session = Depends(get_db)):
    return execution(db, execution_id)


@router.post("/{execution_id}/cancel", response_model=ExecutionCancelRead)
def cancel(execution_id: uuid.UUID, body: ExecutionCancelRequest, db: Session = Depends(get_db)):
    return cancel_execution(db, execution_id, body.reason)


@router.get("/{execution_id}/jobs", response_model=list[JobRead])
def execution_jobs(
    execution_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    execution(db, execution_id)
    return db.scalars(
        select(DurableJob)
        .where(
            DurableJob.execution_id == execution_id,
        )
        .order_by(DurableJob.sequence)
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/{execution_id}/steps", response_model=list[StepRunRead])
def steps(
    execution_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    execution(db, execution_id)
    return db.scalars(
        select(StepRun)
        .where(StepRun.execution_id == execution_id)
        .order_by(
            StepRun.created_at,
            StepRun.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/{execution_id}/steps/{step_id}/attempts", response_model=list[StepAttemptRead])
def attempts(execution_id: uuid.UUID, step_id: uuid.UUID, db: Session = Depends(get_db)):
    from src.services.llm_tool_execution import attempt_metadata

    execution(db, execution_id)
    step = db.scalar(
        select(StepRun).where(StepRun.id == step_id, StepRun.execution_id == execution_id)
    )
    if step is None:
        raise HTTPException(404, "Step run not found")
    rows = db.scalars(
        select(StepAttempt).where(StepAttempt.step_run_id == step_id).order_by(StepAttempt.number)
    ).all()
    return [
        StepAttemptRead.model_validate(row).model_copy(
            update={
                "llm_metadata": attempt_metadata(db, row),
            }
        )
        for row in rows
    ]


@router.get("/{execution_id}/events", response_model=list[ExecutionEventRead])
def events(
    execution_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    execution(db, execution_id)
    return db.scalars(
        select(ExecutionEvent)
        .where(ExecutionEvent.execution_id == execution_id)
        .order_by(ExecutionEvent.created_at, ExecutionEvent.id)
        .offset(offset)
        .limit(limit)
    ).all()
