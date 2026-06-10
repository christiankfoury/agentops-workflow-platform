import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.workflow_run import WorkflowRun
from src.schemas.workflow_run import WorkflowRunCreate, WorkflowRunRead

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


@router.post("", response_model=WorkflowRunRead, status_code=201)
def create_workflow_run(body: WorkflowRunCreate, db: Session = Depends(get_db)) -> WorkflowRun:
    run = WorkflowRun(
        workflow_type=body.workflow_type,
        run_mode=body.run_mode,
        input_id=body.input_id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
