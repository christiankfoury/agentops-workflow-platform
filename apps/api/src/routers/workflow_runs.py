import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import get_llm_client
from src.models.agent_step import AgentStep
from src.models.uploaded_input import UploadedInput
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.models.workflow_run import WorkflowRun
from src.schemas.agent_step import AgentStepRead
from src.schemas.workflow_event import WorkflowEventRead
from src.schemas.workflow_run import WorkflowRunCreate, WorkflowRunRead, WorkflowRunTransition
from src.services.customer_feedback_classifier import (
    ClassifierRunError,
    run_customer_feedback_classifier,
)
from src.services.customer_feedback_insight import InsightRunError, run_customer_feedback_insight
from src.services.llm_client import LLMClient
from src.services.sales_analyst import AnalystRunError, run_sales_analyst
from src.services.sales_baseline import BaselineRunError, run_sales_baseline
from src.services.sales_reviewer import ReviewerRunError, run_sales_reviewer
from src.services.sales_writer import WriterRunError, run_sales_writer
from src.services.workflow_events import log_workflow_event
from src.services.workflow_state import InvalidTransitionError, transition

router = APIRouter()


@router.get("", response_model=list[WorkflowRunRead])
def list_workflow_runs(db: Session = Depends(get_db)) -> list[WorkflowRun]:
    return db.query(WorkflowRun).order_by(WorkflowRun.created_at.desc()).all()


@router.get("/{run_id}", response_model=WorkflowRunRead)
def get_workflow_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> WorkflowRun:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.get("/{run_id}/agent-steps", response_model=list[AgentStepRead])
def list_agent_steps(run_id: uuid.UUID, db: Session = Depends(get_db)) -> list[AgentStep]:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return (
        db.query(AgentStep)
        .filter(AgentStep.workflow_run_id == run_id)
        .order_by(AgentStep.step_order.asc())
        .all()
    )


@router.get("/{run_id}/events", response_model=list[WorkflowEventRead])
def list_workflow_events(run_id: uuid.UUID, db: Session = Depends(get_db)) -> list[WorkflowEvent]:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return (
        db.query(WorkflowEvent)
        .filter(WorkflowEvent.workflow_run_id == run_id)
        .order_by(WorkflowEvent.created_at.asc(), WorkflowEvent.id.asc())
        .all()
    )


@router.post("/{run_id}/run-analyst", response_model=AgentStepRead)
def run_analyst(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
) -> AgentStep:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        return run_sales_analyst(db, run, llm_client)
    except AnalystRunError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/{run_id}/run-classifier", response_model=AgentStepRead)
def run_classifier(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
) -> AgentStep:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        return run_customer_feedback_classifier(db, run, llm_client)
    except ClassifierRunError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/{run_id}/run-insight", response_model=AgentStepRead)
def run_insight(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
) -> AgentStep:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        return run_customer_feedback_insight(db, run, llm_client)
    except InsightRunError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/{run_id}/run-baseline", response_model=AgentStepRead)
def run_baseline(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
) -> AgentStep:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        return run_sales_baseline(db, run, llm_client)
    except (BaselineRunError, InvalidTransitionError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/{run_id}/run-reviewer", response_model=AgentStepRead)
def run_reviewer(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
) -> AgentStep:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        return run_sales_reviewer(db, run, llm_client)
    except ReviewerRunError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/{run_id}/run-writer", response_model=AgentStepRead)
def run_writer(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
) -> AgentStep:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        return run_sales_writer(db, run, llm_client)
    except (WriterRunError, InvalidTransitionError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("", response_model=WorkflowRunRead, status_code=201)
def create_workflow_run(body: WorkflowRunCreate, db: Session = Depends(get_db)) -> WorkflowRun:
    if body.input_id is not None:
        uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == body.input_id).first()
        if uploaded_input is None:
            raise HTTPException(status_code=422, detail="Uploaded input not found")
        if uploaded_input.input_type != body.workflow_type:
            raise HTTPException(
                status_code=422,
                detail="Uploaded input type must match workflow type",
            )

    run = WorkflowRun(
        workflow_type=body.workflow_type,
        run_mode=body.run_mode,
        input_id=body.input_id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    log_workflow_event(
        db,
        run,
        WorkflowEventType.workflow_started,
        "Workflow run created.",
        metadata={
            "workflow_type": run.workflow_type.value,
            "run_mode": run.run_mode.value,
            "status": run.status.value,
            "input_id": run.input_id,
        },
    )
    return run


@router.patch("/{run_id}/status", response_model=WorkflowRunRead)
def update_workflow_status(
    run_id: uuid.UUID, body: WorkflowRunTransition, db: Session = Depends(get_db)
) -> WorkflowRun:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    try:
        return transition(run, body.status, db)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=422, detail=str(e))
