import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.uploaded_input import UploadedInput
from src.schemas.uploaded_input import UploadedInputCreate, UploadedInputRead

router = APIRouter()


@router.post("", response_model=UploadedInputRead, status_code=201)
def create_uploaded_input(
    body: UploadedInputCreate, db: Session = Depends(get_db)
) -> UploadedInput:
    uploaded_input = UploadedInput(
        organization_id=body.organization_id,
        created_by_user_id=body.created_by_user_id,
        title=body.title,
        input_type=body.input_type,
        raw_text=body.raw_text,
        notes=body.notes,
        file_name=body.file_name,
        file_type=body.file_type,
        file_size=body.file_size,
    )
    db.add(uploaded_input)
    db.commit()
    db.refresh(uploaded_input)
    return uploaded_input


@router.get("/{input_id}", response_model=UploadedInputRead)
def get_uploaded_input(input_id: uuid.UUID, db: Session = Depends(get_db)) -> UploadedInput:
    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == input_id).first()
    if uploaded_input is None:
        raise HTTPException(status_code=404, detail="Uploaded input not found")
    return uploaded_input
