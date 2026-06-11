from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.models.agent_setting import AgentSetting
from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.schemas.agent_setting import AgentSettingRead, AgentSettingUpdate
from src.services.agent_settings import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT_SECONDS
from src.services.llm_client import DEFAULT_MAX_TOKENS

router = APIRouter()


@router.get("", response_model=list[AgentSettingRead])
def list_agent_settings(db: Session = Depends(get_db)) -> list[AgentSettingRead]:
    return [_read_effective_setting(db, agent_type) for agent_type in AgentType]


@router.put("/{agent_type}", response_model=AgentSettingRead)
def update_agent_setting(
    agent_type: AgentType,
    body: AgentSettingUpdate,
    db: Session = Depends(get_db),
) -> AgentSettingRead:
    if body.active_prompt_version_id is not None:
        prompt = (
            db.query(PromptVersion)
            .filter(PromptVersion.id == body.active_prompt_version_id)
            .first()
        )
        if prompt is None:
            raise HTTPException(status_code=404, detail="Prompt version not found")
        if prompt.agent_type != agent_type:
            raise HTTPException(
                status_code=422,
                detail="Prompt version agent type does not match setting agent type",
            )

    setting = db.query(AgentSetting).filter(AgentSetting.agent_type == agent_type).first()
    if setting is None:
        setting = AgentSetting(agent_type=agent_type)
        db.add(setting)

    setting.model = body.model
    setting.temperature = body.temperature
    setting.max_tokens = body.max_tokens
    setting.timeout_seconds = body.timeout_seconds
    setting.max_retries = body.max_retries
    setting.active_prompt_version_id = body.active_prompt_version_id
    setting.reviewer_approval_threshold = body.reviewer_approval_threshold
    setting.human_approval_threshold = body.human_approval_threshold
    db.commit()
    db.refresh(setting)
    return _read_effective_setting(db, agent_type)


def _read_effective_setting(db: Session, agent_type: AgentType) -> AgentSettingRead:
    setting = db.query(AgentSetting).filter(AgentSetting.agent_type == agent_type).first()
    prompt = _active_prompt(db, agent_type, setting)
    return AgentSettingRead(
        id=setting.id if setting is not None else None,
        agent_type=agent_type,
        model=setting.model if setting is not None else settings.openai_model,
        temperature=setting.temperature if setting is not None else None,
        max_tokens=setting.max_tokens if setting is not None else DEFAULT_MAX_TOKENS,
        timeout_seconds=(
            setting.timeout_seconds if setting is not None else DEFAULT_TIMEOUT_SECONDS
        ),
        max_retries=setting.max_retries if setting is not None else DEFAULT_MAX_RETRIES,
        active_prompt_version_id=(
            setting.active_prompt_version_id
            if setting is not None and setting.active_prompt_version_id is not None
            else (prompt.id if prompt is not None else None)
        ),
        active_prompt_name=prompt.name if prompt is not None else None,
        reviewer_approval_threshold=(
            setting.reviewer_approval_threshold if setting is not None else None
        ),
        human_approval_threshold=(
            setting.human_approval_threshold if setting is not None else None
        ),
    )


def _active_prompt(
    db: Session,
    agent_type: AgentType,
    setting: AgentSetting | None,
) -> PromptVersion | None:
    if setting is not None and setting.active_prompt_version_id is not None:
        prompt = (
            db.query(PromptVersion)
            .filter(PromptVersion.id == setting.active_prompt_version_id)
            .first()
        )
        if prompt is not None and prompt.agent_type == agent_type:
            return prompt
    return (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == agent_type,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .order_by(PromptVersion.version.desc(), PromptVersion.created_at.desc())
        .first()
    )
