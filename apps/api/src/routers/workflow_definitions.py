import difflib
import json
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.workflow_definition import WorkflowDefinition, WorkflowVersion
from src.schemas.workflow_definition import (
    DefinitionCreate,
    DefinitionRead,
    DefinitionUpdate,
    RevisionRequest,
    ValidationResult,
    VersionRead,
)
from src.services import workflow_definitions as service

router = APIRouter()


@router.post("/templates/incident/install", response_model=list[DefinitionRead])
def install_incident_templates(db: Session = Depends(get_db)):
    from src.services.incident_template import install

    return install(db)


@router.post("/templates/customer-feedback/install", response_model=list[DefinitionRead])
def install_feedback_templates(db: Session = Depends(get_db)):
    from src.services.feedback_template import install

    return install(db)


@router.post("/templates/sales/install", response_model=list[DefinitionRead])
def install_sales_templates(db: Session = Depends(get_db)):
    from src.services.sales_template import install

    return install(db)


@router.get("", response_model=list[DefinitionRead])
def list_definitions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(WorkflowDefinition)
        .order_by(
            WorkflowDefinition.created_at.desc(),
            WorkflowDefinition.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()


@router.post("", response_model=DefinitionRead, status_code=201)
def create(body: DefinitionCreate, db: Session = Depends(get_db)):
    return service.create_definition(db, body)


@router.get("/{definition_id}", response_model=DefinitionRead)
def detail(definition_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.definition(db, definition_id)


@router.put("/{definition_id}/draft", response_model=DefinitionRead)
def update(definition_id: uuid.UUID, body: DefinitionUpdate, db: Session = Depends(get_db)):
    return service.update_draft(db, definition_id, body)


@router.post("/{definition_id}/validate", response_model=ValidationResult)
def validate(definition_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.validate_draft(service.definition(db, definition_id).draft_graph, db)


@router.post("/{definition_id}/publish", response_model=VersionRead, status_code=201)
def publish(definition_id: uuid.UUID, body: RevisionRequest, db: Session = Depends(get_db)):
    return service.publish(db, definition_id, body.expected_revision)


@router.post("/{definition_id}/archive", response_model=DefinitionRead)
def archive(definition_id: uuid.UUID, body: RevisionRequest, db: Session = Depends(get_db)):
    return service.archive(db, definition_id, body.expected_revision)


@router.get("/{definition_id}/versions", response_model=list[VersionRead])
def versions(
    definition_id: uuid.UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service.definition(db, definition_id)
    return db.scalars(
        select(WorkflowVersion)
        .where(
            WorkflowVersion.definition_id == definition_id,
        )
        .order_by(WorkflowVersion.number.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/{definition_id}/versions/{version_id}", response_model=VersionRead)
def version(definition_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.version(db, definition_id, version_id)


@router.get("/{definition_id}/versions/{version_id}/capabilities", response_model=ValidationResult)
def capabilities(definition_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)):
    return service.validate_draft(service.version(db, definition_id, version_id).graph, db)


@router.post("/{definition_id}/versions/{version_id}/archive", response_model=DefinitionRead)
def archive_version(
    definition_id: uuid.UUID,
    version_id: uuid.UUID,
    body: RevisionRequest,
    db: Session = Depends(get_db),
):
    return service.archive(db, definition_id, body.expected_revision, version_id)


@router.get("/{definition_id}/versions/{version_id}/diff")
def version_diff(
    definition_id: uuid.UUID,
    version_id: uuid.UUID,
    compare_to: uuid.UUID,
    db: Session = Depends(get_db),
):
    before = service.version(db, definition_id, compare_to)
    after = service.version(db, definition_id, version_id)

    def content(item):
        return json.dumps(
            {
                "name": item.name,
                "description": item.description,
                "graph": item.graph,
                "prompt_snapshots": item.prompt_snapshots,
            },
            sort_keys=True,
            indent=2,
        ).splitlines()

    return {
        "before": before.id,
        "after": after.id,
        "diff": "\n".join(
            difflib.unified_diff(
                content(before),
                content(after),
                fromfile=f"version-{before.number}",
                tofile=f"version-{after.number}",
                lineterm="",
            )
        ),
    }
