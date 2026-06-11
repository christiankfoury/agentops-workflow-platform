import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.human_approval import HumanApproval
from src.schemas.human_approval import (
    HumanApprovalAction,
    HumanApprovalEdit,
    HumanApprovalRead,
)
from src.services.human_approvals import (
    HumanApprovalError,
    approve_human_approval,
    edit_human_approval,
    reject_human_approval,
    request_human_approval_retry,
)
from src.services.workflow_state import InvalidTransitionError

router = APIRouter()


@router.get("", response_model=list[HumanApprovalRead])
def list_human_approvals(db: Session = Depends(get_db)) -> list[HumanApproval]:
    return db.query(HumanApproval).order_by(HumanApproval.created_at.desc()).all()


@router.get("/{approval_id}", response_model=HumanApprovalRead)
def get_human_approval(
    approval_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> HumanApproval:
    approval = _get_approval_or_404(db, approval_id)
    return approval


@router.post("/{approval_id}/approve", response_model=HumanApprovalRead)
def approve(
    approval_id: uuid.UUID,
    body: HumanApprovalAction | None = None,
    db: Session = Depends(get_db),
) -> HumanApproval:
    approval = _get_approval_or_404(db, approval_id)
    try:
        return approve_human_approval(
            db,
            approval,
            human_feedback=body.human_feedback if body else None,
            approved_by_user_id=body.approved_by_user_id if body else None,
        )
    except (HumanApprovalError, InvalidTransitionError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/{approval_id}/request-retry", response_model=HumanApprovalRead)
def request_retry(
    approval_id: uuid.UUID,
    body: HumanApprovalAction | None = None,
    db: Session = Depends(get_db),
) -> HumanApproval:
    approval = _get_approval_or_404(db, approval_id)
    try:
        return request_human_approval_retry(
            db,
            approval,
            human_feedback=body.human_feedback if body else None,
            approved_by_user_id=body.approved_by_user_id if body else None,
        )
    except (HumanApprovalError, InvalidTransitionError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/{approval_id}/reject", response_model=HumanApprovalRead)
def reject(
    approval_id: uuid.UUID,
    body: HumanApprovalAction | None = None,
    db: Session = Depends(get_db),
) -> HumanApproval:
    approval = _get_approval_or_404(db, approval_id)
    try:
        return reject_human_approval(
            db,
            approval,
            human_feedback=body.human_feedback if body else None,
            approved_by_user_id=body.approved_by_user_id if body else None,
        )
    except (HumanApprovalError, InvalidTransitionError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/{approval_id}/edit", response_model=HumanApprovalRead)
def edit(
    approval_id: uuid.UUID,
    body: HumanApprovalEdit,
    db: Session = Depends(get_db),
) -> HumanApproval:
    approval = _get_approval_or_404(db, approval_id)
    try:
        return edit_human_approval(
            db,
            approval,
            human_feedback=body.human_feedback,
            edited_analysis_json=body.edited_analysis_json,
        )
    except HumanApprovalError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def _get_approval_or_404(db: Session, approval_id: uuid.UUID) -> HumanApproval:
    approval = db.query(HumanApproval).filter(HumanApproval.id == approval_id).first()
    if approval is None:
        raise HTTPException(status_code=404, detail="Human approval not found")
    return approval
