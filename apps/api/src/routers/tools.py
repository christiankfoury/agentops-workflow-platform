import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.tool import ToolCredential, ToolDefinition, ToolExecution, ToolVersion
from src.schemas.tool import (
    ActiveUpdate,
    CredentialCreate,
    EffectResolution,
    ToolCreate,
    ToolPublish,
)
from src.services import tool_catalog as catalog

router = APIRouter()


@router.get("")
def list_tools(db: Session = Depends(get_db)):
    return [catalog.public(item) for item in db.scalars(select(ToolDefinition))]


@router.post("", status_code=201)
def create_tool(body: ToolCreate, db: Session = Depends(get_db)):
    return catalog.public(catalog.create(db, body))


@router.post("/credentials", status_code=201)
def create_credential(body: CredentialCreate, db: Session = Depends(get_db)):
    return catalog.public(catalog.create_credential(db, body))


@router.patch("/credentials/{identity}")
def set_credential(identity: uuid.UUID, body: ActiveUpdate, db: Session = Depends(get_db)):
    return catalog.public(catalog.set_active(db, ToolCredential, identity, body.active))


@router.get("/versions/{identity}")
def read_version(identity: uuid.UUID, db: Session = Depends(get_db)):
    return catalog.public(catalog.get(db, ToolVersion, identity))


@router.get("/executions/{identity}")
def read_execution(identity: uuid.UUID, db: Session = Depends(get_db)):
    return catalog.public(catalog.get(db, ToolExecution, identity))


@router.post("/executions/{identity}/resolve")
def resolve_execution(identity: uuid.UUID, body: EffectResolution, db: Session = Depends(get_db)):
    from src.services.tool_effects import resolve

    return catalog.public(resolve(db, identity, body))


@router.post("/{identity}/versions", status_code=201)
def publish_tool(identity: uuid.UUID, body: ToolPublish, db: Session = Depends(get_db)):
    return catalog.public(catalog.publish(db, identity, body))


@router.get("/{identity}/versions")
def list_versions(identity: uuid.UUID, db: Session = Depends(get_db)):
    catalog.get(db, ToolDefinition, identity)
    return [
        catalog.public(item)
        for item in db.scalars(
            select(ToolVersion)
            .where(ToolVersion.definition_id == identity)
            .order_by(ToolVersion.number)
        )
    ]


@router.patch("/{identity}")
def set_tool(identity: uuid.UUID, body: ActiveUpdate, db: Session = Depends(get_db)):
    return catalog.public(catalog.set_active(db, ToolDefinition, identity, body.active))
