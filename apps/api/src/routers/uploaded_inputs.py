import csv
import io
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.dependencies import get_llm_client
from src.models.uploaded_input import InputType, UploadedInput
from src.schemas.uploaded_input import (
    UploadedInputCreate,
    UploadedInputRead,
    WorkflowDetectionRead,
    WorkflowDetectionRequest,
)
from src.security import ROLE_ADMIN, ROLE_OPERATOR, require_role
from src.services.llm_client import LLMClient
from src.services.router_agent import RouterRunError, detect_workflow_type

router = APIRouter()

ALLOWED_UPLOAD_EXTENSIONS = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
}
ALLOWED_UPLOAD_CONTENT_TYPES = {
    ".txt": {"application/octet-stream", "text/plain"},
    ".md": {"application/octet-stream", "text/markdown", "text/plain"},
    ".csv": {"application/csv", "application/octet-stream", "application/vnd.ms-excel", "text/csv"},
}
INCIDENT_EVENT_PATTERN = re.compile(
    
        r"^\s*(?P<time>(?:\d{1,2}:\d{2}(?:\s?(?:AM|PM|am|pm))?|"
        r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?))"
        r"\s*(?:-|:)\s*(?P<event>.+?)\s*$"
    
)


@router.post("", response_model=UploadedInputRead, status_code=201)
def create_uploaded_input(
    body: UploadedInputCreate,
    db: Session = Depends(get_db),
    _principal: object = Depends(require_role(ROLE_OPERATOR, ROLE_ADMIN)),
) -> UploadedInput:
    raw_text = _normalize_and_validate_input_text(body.raw_text, body.input_type)
    uploaded_input = UploadedInput(
        organization_id=body.organization_id,
        created_by_user_id=body.created_by_user_id,
        title=body.title,
        input_type=body.input_type,
        raw_text=raw_text,
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
    _principal: object = Depends(require_role(ROLE_OPERATOR, ROLE_ADMIN)),
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
    if not _is_allowed_content_type(extension, file.content_type):
        raise HTTPException(
            status_code=422,
            detail="Uploaded file content type does not match the allowed file type",
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"Uploaded file must be {settings.max_upload_bytes // 1024} KB or smaller",
        )

    raw_text = _normalize_and_validate_input_text(
        _extract_uploaded_text(content, input_type, extension),
        input_type,
    )
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
    _principal: object = Depends(require_role(ROLE_OPERATOR, ROLE_ADMIN)),
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


def _is_allowed_content_type(extension: str, content_type: str | None) -> bool:
    if content_type is None:
        return True
    normalized = content_type.split(";", 1)[0].strip().lower()
    return normalized in ALLOWED_UPLOAD_CONTENT_TYPES[extension]


def _extract_uploaded_text(content: bytes, input_type: InputType, extension: str) -> str:
    text = _decode_uploaded_text(content)
    if input_type == InputType.customer_feedback and extension == ".csv":
        return _parse_customer_feedback_csv(text)
    return text


def _decode_uploaded_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig").strip()
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=422, detail="Uploaded file must be UTF-8 text") from e


def _parse_customer_feedback_csv(value: str) -> str:
    reader = csv.DictReader(io.StringIO(value))
    fieldnames = [field.strip().lower() for field in reader.fieldnames or [] if field]
    if "feedback" not in fieldnames:
        raise HTTPException(
            status_code=422,
            detail="Customer feedback CSV uploads must include a feedback column",
        )

    parsed_rows: list[str] = []
    for index, row in enumerate(reader, start=1):
        normalized = {
            (key or "").strip().lower(): (item or "").strip()
            for key, item in row.items()
        }
        feedback = normalized.get("feedback", "")
        if not feedback:
            continue
        details = [
            f"customer_id={normalized['customer_id']}"
            if normalized.get("customer_id")
            else None,
            f"date={normalized['date']}" if normalized.get("date") else None,
            f"rating={normalized['rating']}" if normalized.get("rating") else None,
            f"source={normalized['source']}" if normalized.get("source") else None,
        ]
        prefix = "; ".join(detail for detail in details if detail is not None)
        parsed_rows.append(
            f"Feedback {index}: {prefix}. {feedback}" if prefix else f"Feedback {index}: {feedback}"
        )

    if not parsed_rows:
        raise HTTPException(
            status_code=422,
            detail="Customer feedback CSV uploads must include at least one feedback row",
        )
    return "\n".join(parsed_rows)


def _normalize_input_text(value: str, input_type: InputType) -> str:
    if input_type == InputType.incident_log:
        return _parse_incident_log(value)
    return value


def _normalize_and_validate_input_text(value: str, input_type: InputType) -> str:
    normalized = _normalize_input_text(value, input_type)
    if len(normalized) > settings.max_input_chars:
        raise HTTPException(
            status_code=422,
            detail=f"Input text must be {settings.max_input_chars} characters or fewer",
        )
    return normalized


def _parse_incident_log(value: str) -> str:
    parsed_events: list[str] = []
    ambiguous_lines: list[str] = []
    for line in (item.strip() for item in value.splitlines()):
        if not line:
            continue
        match = INCIDENT_EVENT_PATTERN.match(line)
        if match is None:
            ambiguous_lines.append(line)
            continue
        parsed_events.append(
            "Event {index}: time={time}; event={event}; raw_line={raw_line}".format(
                index=len(parsed_events) + 1,
                time=match.group("time").strip(),
                event=match.group("event").strip(),
                raw_line=line,
            )
        )

    if not parsed_events:
        return value

    output = ["Parsed incident events:", *parsed_events]
    if ambiguous_lines:
        output.extend(["Ambiguous incident log lines:", *[f"- {line}" for line in ambiguous_lines]])
    return "\n".join(output)


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None
