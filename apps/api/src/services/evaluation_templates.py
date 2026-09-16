"""Pin the existing optional router diagnostic ahead of an evaluated business graph."""

import uuid
from copy import deepcopy

from fastapi import HTTPException
from sqlalchemy import select

from src.models.agent_type import AgentType
from src.models.identity import Organization
from src.models.workflow_definition import WorkflowDefinition
from src.schemas.router import RawRouterOutput
from src.services.agent_settings import AgentSettingsError, get_agent_runtime_config
from src.services.business_schemas import SOURCE, graph_schema, obj, reference
from src.services.business_templates import template_id
from src.services.permissions import authorize
from src.services.tenancy import tenant_id
from src.services.workflow_definitions import publish, require_runnable_version


def select_template(db, business_type, mode):
    authorize(db, "workflow.publish")
    db.scalar(select(Organization).where(Organization.id == tenant_id(db)).with_for_update())
    principal = authorize(db, "workflow.publish", lock=True)
    base = db.get(WorkflowDefinition, template_id(tenant_id(db), business_type, mode))
    db.refresh(base)
    source = require_runnable_version(db, base.id, base.published_version_id)
    try:
        router = get_agent_runtime_config(db, AgentType.router)
    except AgentSettingsError as error:
        if str(error).startswith("Active "):
            return base.id
        raise HTTPException(409, str(error)) from error
    identity = uuid.uuid5(source.id, f"evaluation:{router.prompt.id}")
    item = db.get(WorkflowDefinition, identity)
    if item is None:
        graph = deepcopy(source.graph)
        graph["nodes"].insert(
            0,
            {
                "id": "router",
                "type": "llm",
                "input_schema": obj(source=SOURCE),
                "inputs": {"source": reference()},
                "output_schema": graph_schema(RawRouterOutput.model_json_schema()),
                "config": {
                    "prompt_version_id": str(router.prompt.id),
                    "model": router.model,
                    "use_agent_settings": True,
                    "output_validator": "business.router.v1",
                },
            },
        )
        graph["edges"].insert(0, {"source": "router", "target": graph["entry_node"]})
        graph["entry_node"] = "router"
        item = WorkflowDefinition(
            id=identity,
            name=f"Evaluation: {base.name}",
            description="Pinned business graph with router diagnostic.",
            draft_graph=graph,
            created_by_user_id=principal.user_id,
        )
        db.add(item)
        db.flush()
        publish(db, identity, item.draft_revision)
    else:
        db.commit()
    return identity
