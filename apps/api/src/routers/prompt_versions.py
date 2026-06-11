import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.schemas.prompt_version import PromptVersionCreate, PromptVersionRead
from src.services.prompt_versions import activate_prompt_version, deactivate_matching_prompts

router = APIRouter()


@router.get("", response_model=list[PromptVersionRead])
def list_prompt_versions(
    agent_type: AgentType | None = None,
    name: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> list[PromptVersion]:
    query = db.query(PromptVersion)
    if agent_type is not None:
        query = query.filter(PromptVersion.agent_type == agent_type)
    if name is not None:
        query = query.filter(PromptVersion.name == name)
    if is_active is not None:
        query = query.filter(PromptVersion.is_active == is_active)
    return (
        query.order_by(
            PromptVersion.agent_type.asc(),
            PromptVersion.name.asc(),
            PromptVersion.version.desc(),
        )
        .all()
    )


@router.get("/{prompt_version_id}", response_model=PromptVersionRead)
def get_prompt_version(
    prompt_version_id: uuid.UUID, db: Session = Depends(get_db)
) -> PromptVersion:
    prompt = db.query(PromptVersion).filter(PromptVersion.id == prompt_version_id).first()
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return prompt


@router.post("", response_model=PromptVersionRead, status_code=201)
def create_prompt_version(
    body: PromptVersionCreate, db: Session = Depends(get_db)
) -> PromptVersion:
    prompt = PromptVersion(
        agent_type=body.agent_type,
        name=body.name,
        version=body.version,
        template=body.template,
        is_active=body.is_active,
        notes=body.notes,
        created_by_user_id=body.created_by_user_id,
    )
    if body.is_active:
        deactivate_matching_prompts(db, body.agent_type, body.name)

    try:
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="Prompt version already exists") from e

    return prompt


@router.post("/{prompt_version_id}/activate", response_model=PromptVersionRead)
def activate_prompt(
    prompt_version_id: uuid.UUID, db: Session = Depends(get_db)
) -> PromptVersion:
    prompt = db.query(PromptVersion).filter(PromptVersion.id == prompt_version_id).first()
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return activate_prompt_version(db, prompt)
