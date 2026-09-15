import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.execution_approval import ExecutionApproval
from src.schemas.execution_approval import (
    ApprovalDecision,
    ApprovalDecisionRead,
    ExecutionApprovalRead,
)
from src.services.approval_runtime import decide_approval
from src.services.execution_records import execution

router = APIRouter()


@router.get("", response_model=list[ExecutionApprovalRead])
def list_approvals(
    execution_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    execution(db, execution_id)
    return db.scalars(
        select(ExecutionApproval)
        .where(ExecutionApproval.execution_id == execution_id)
        .order_by(ExecutionApproval.created_at, ExecutionApproval.id)
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/{approval_id}", response_model=ExecutionApprovalRead)
def detail(approval_id: uuid.UUID, db: Session = Depends(get_db)):
    item = db.scalar(select(ExecutionApproval).where(ExecutionApproval.id == approval_id))
    if item is None:
        raise HTTPException(404, "Execution approval not found")
    return item


@router.post("/{approval_id}/decide", response_model=ApprovalDecisionRead)
def decide(approval_id: uuid.UUID, body: ApprovalDecision, db: Session = Depends(get_db)):
    return decide_approval(db, approval_id, body)
