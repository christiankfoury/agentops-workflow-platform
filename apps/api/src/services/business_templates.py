"""Shared tenant-serialized installation and atomic business-run acceptance."""

import uuid

from fastapi import HTTPException
from sqlalchemy import select

from src.models.agent_type import AgentType
from src.models.identity import Organization
from src.models.prompt_version import PromptVersion
from src.models.workflow_definition import WorkflowDefinition
from src.models.workflow_run import RunMode, WorkflowRun
from src.schemas.execution_start import ExecutionStartRequest
from src.services.agent_settings import AgentSettingsError, get_agent_runtime_config
from src.services.execution_starts import start_execution
from src.services.permissions import authorize
from src.services.prompt_versions import DEFAULT_PROMPTS
from src.services.tenancy import tenant_id
from src.services.workflow_definitions import publish


def template_id(organization_id, business_type, mode):
    return uuid.uuid5(organization_id, f"builtin.{business_type.value}.{mode}")


def install_templates(
    db, business_type, label, kinds, baseline_prompt, graph, *, prompt_label=None
):
    """Admin-only, idempotent installation; never overwrite an edited published template."""
    installed = []
    for mode in [RunMode.multi_agent, RunMode.baseline]:
        authorize(db, "workflow.publish")
        db.scalar(select(Organization).where(Organization.id == tenant_id(db)).with_for_update())
        principal = authorize(db, "workflow.publish", lock=True)
        identity = template_id(tenant_id(db), business_type, mode)
        item = db.get(WorkflowDefinition, identity)
        if item and item.published_version_id:
            installed.append(item)
            db.commit()
            continue
        prompts = {}
        for kind in ["baseline"] if mode == RunMode.baseline else kinds:
            agent_type = AgentType.writer if kind == "baseline" else AgentType(kind)
            try:
                if kind == "baseline":
                    raise AgentSettingsError("Dedicated baseline prompt")
                prompts[kind] = get_agent_runtime_config(db, agent_type).prompt
            except AgentSettingsError as error:
                if kind != "baseline" and not str(error).startswith("Active "):
                    raise HTTPException(409, str(error)) from error
                name = f"{prompt_label or label} template {kind}"
                prompt = db.scalar(
                    select(PromptVersion).where(
                        PromptVersion.name == name,
                        PromptVersion.agent_type == agent_type,
                        PromptVersion.version == 1,
                    )
                )
                if prompt is None:
                    template = (
                        baseline_prompt
                        if kind == "baseline"
                        else next(
                            entry["template"]
                            for entry in DEFAULT_PROMPTS
                            if entry["agent_type"] == agent_type
                        )
                    )
                    prompt = PromptVersion(
                        agent_type=agent_type,
                        name=name,
                        version=1,
                        template=template,
                        is_active=False,
                        created_by_user_id=principal.user_id,
                    )
                    db.add(prompt)
                    db.flush()
                prompts[kind] = prompt
        if item is None:
            item = WorkflowDefinition(
                id=identity,
                name=f"{label} — {mode.value}",
                description=f"Published {business_type.value} workflow template.",
                draft_graph=graph(prompts, mode),
                created_by_user_id=principal.user_id,
            )
            db.add(item)
            db.flush()
        publish(db, item.id, item.draft_revision)
        installed.append(item)
    return installed


def start_business(db, source, mode, business_type, label, key, *, commit=True, definition_id=None):
    authorize(db, "workflow.start", lock=True)
    if source is None or source.input_type.value != business_type.value:
        raise HTTPException(422, f"A {label} input is required")
    definition_id = definition_id or template_id(tenant_id(db), business_type, mode)
    if db.get(WorkflowDefinition, definition_id) is None:
        raise HTTPException(
            409, f"An administrator must install the {label} templates before starting"
        )
    legacy = WorkflowRun(
        id=uuid.uuid4(), workflow_type=business_type, run_mode=mode, input_id=source.id
    )
    start_execution(
        db,
        ExecutionStartRequest(
            definition_id=definition_id,
            idempotency_key=f"{key}:{legacy.id}",
            input={"title": source.title, "raw_text": source.raw_text, "notes": source.notes or ""},
        ),
        legacy_run=legacy,
        commit=commit,
    )
    return legacy
