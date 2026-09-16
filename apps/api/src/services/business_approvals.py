"""Legacy approval URL adapters delegate every mutation to the durable authority."""

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.models.execution_approval import ExecutionApproval
from src.models.human_approval import HumanApproval
from src.schemas.execution_approval import ApprovalDecision
from src.services.approval_runtime import decide_approval


def source_for(db, identity):
    if not isinstance(db, Session):
        return None
    return db.get(ExecutionApproval, identity)


def adapt(db, approval, action, body):
    source = source_for(db, approval.id)
    if source is None:
        return None
    expected = body.expected_payload_hash if body else None
    if expected is None:
        raise HTTPException(409, "Reload this durable approval before deciding")
    try:
        decision = ApprovalDecision(
            action=action,
            expected_payload_hash=expected,
            human_feedback=body.human_feedback if body else None,
            edited_payload=(
                body.edited_analysis_json
                if body.edited_analysis_json is not None
                else source.payload_json
            )
            if action == "edit"
            else None,
        )
    except ValidationError as error:
        raise HTTPException(422, "Decision exceeds durable approval bounds") from error
    result = decide_approval(db, source.id, decision)
    identity = result.replacement_id if action == "edit" else result.id
    projected = db.get(HumanApproval, identity)
    db.refresh(projected)
    return projected
