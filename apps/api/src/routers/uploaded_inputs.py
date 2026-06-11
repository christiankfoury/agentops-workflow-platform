import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import get_llm_client
from src.models.uploaded_input import InputType, UploadedInput
from src.schemas.uploaded_input import (
    UploadedInputCreate,
    UploadedInputRead,
    WorkflowDetectionRead,
    WorkflowDetectionRequest,
)
from src.services.llm_client import LLMClient
from src.services.router_agent import RouterRunError, detect_workflow_type

router = APIRouter()

MAX_UPLOAD_BYTES = 250 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
}


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


@router.post("/upload", response_model=UploadedInputRead, status_code=201)
async def upload_input_file(
    title: str = Form(..., min_length=1, max_length=255),
    input_type: InputType = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadedInput:
    title = title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Input title is required")

    file_name = (file.filename or "").strip()
    extension = _file_extension(file_name)
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail="Only .txt, .md, and .csv uploads are supported",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail="Uploaded file must be 250 KB or smaller")

    raw_text = _decode_uploaded_text(content)
    if not raw_text:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    uploaded_input = UploadedInput(
        title=title,
        input_type=input_type,
        raw_text=raw_text,
        notes=_clean_optional_text(notes),
        file_name=file_name,
        file_type=file.content_type or ALLOWED_UPLOAD_EXTENSIONS[extension],
        file_size=len(content),
    )
    db.add(uploaded_input)
    db.commit()
    db.refresh(uploaded_input)
    return uploaded_input


@router.post("/detect-workflow", response_model=WorkflowDetectionRead)
def detect_uploaded_input_workflow(
    body: WorkflowDetectionRequest,
    db: Session = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
) -> WorkflowDetectionRead:
    try:
        detection = detect_workflow_type(
            db,
            title=body.title,
            raw_text=body.raw_text,
            notes=body.notes,
            llm_client=llm_client,
        )
    except RouterRunError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return WorkflowDetectionRead(
        workflow_type=detection.workflow_type,
        confidence=detection.confidence,
        reasoning_summary=detection.reasoning_summary,
        recommended_action=detection.recommended_action,
    )


@router.get("/{input_id}", response_model=UploadedInputRead)
def get_uploaded_input(input_id: uuid.UUID, db: Session = Depends(get_db)) -> UploadedInput:
    uploaded_input = db.query(UploadedInput).filter(UploadedInput.id == input_id).first()
    if uploaded_input is None:
        raise HTTPException(status_code=404, detail="Uploaded input not found")
    return uploaded_input


def _file_extension(file_name: str) -> str:
    if "." not in file_name:
        return ""
    return f".{file_name.rsplit('.', 1)[-1].lower()}"


def _decode_uploaded_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig").strip()
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=422, detail="Uploaded file must be UTF-8 text") from e


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None
