"""Sales control flow is published graph data; existing schemas/prompts remain reusable."""

import uuid
from copy import deepcopy

from fastapi import HTTPException
from sqlalchemy import select

from src.config import settings
from src.models.agent_type import AgentType
from src.models.identity import Organization
from src.models.prompt_version import PromptVersion
from src.models.workflow_definition import WorkflowDefinition
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowType
from src.schemas.execution_start import ExecutionStartRequest
from src.schemas.workflow_graph import WorkflowGraph
from src.services.agent_settings import AgentSettingsError, get_agent_runtime_config
from src.services.execution_registry import ensure_executable
from src.services.execution_starts import start_execution
from src.services.permissions import authorize
from src.services.prompt_versions import DEFAULT_PROMPTS
from src.services.sales_analyst import SALES_ANALYSIS_SCHEMA
from src.services.sales_baseline import SALES_BASELINE_SYSTEM_PROMPT
from src.services.sales_reviewer import SALES_REVIEW_SCHEMA
from src.services.tenancy import tenant_id
from src.services.workflow_definitions import publish


def template_id(organization_id, mode):
    return uuid.uuid5(organization_id, f"builtin.sales_report.{mode}")


def obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties)}


STRING = {"type": "string"}
SOURCE = obj(title=STRING, raw_text=STRING, notes=STRING)
REPORT = obj(final_output=STRING)


def graph_schema(schema):
    # The graph type system is deliberately smaller than provider JSON Schema.
    # Reviewer score/severity constraints are enforced by the LLM review validator.
    result = {
        key: deepcopy(value)
        for key, value in schema.items()
        if key in {"type", "required", "additionalProperties"}
    }
    if "properties" in schema:
        result["properties"] = {
            key: graph_schema(value) for key, value in schema["properties"].items()
        }
    if "items" in schema:
        result["items"] = graph_schema(schema["items"])
    return result


REVIEW = graph_schema(SALES_REVIEW_SCHEMA)


def reference(node=None, path=()):
    return {
        "op": "ref",
        "ref": {
            "source": "node" if node else "input",
            **({"node_id": node} if node else {}),
            "path": list(path),
        },
    }


def graph(prompts, mode):
    def llm(key, kind, output, schemas, bindings):
        return {
            "id": key,
            "type": "llm",
            "input_schema": obj(**schemas),
            "inputs": bindings,
            "output_schema": deepcopy(output),
            "config": {
                "prompt_version_id": str(prompts[kind].id),
                "model": settings.openai_model,
                "use_agent_settings": kind != "baseline",
                **(
                    {"output_validator": "business.final_report.v1"}
                    if kind in {"baseline", "writer"}
                    else {}
                ),
            },
            "retry": {
                "max_attempts": 3,
                "retryable_errors": [
                    "provider_connection",
                    "provider_rate_limit",
                    "provider_unavailable",
                    "attempt_timeout",
                ],
            },
        }

    if mode == RunMode.baseline:
        nodes = [llm("baseline", "baseline", REPORT, {"source": SOURCE}, {"source": reference()})]
        edges, policy = [], {}
    else:
        nodes = [
            llm(
                "analyst",
                "analyst",
                SALES_ANALYSIS_SCHEMA,
                {"source": SOURCE},
                {"source": reference()},
            ),
            llm(
                "reviewer",
                "reviewer",
                REVIEW,
                {"source": SOURCE, "analysis": SALES_ANALYSIS_SCHEMA},
                {"source": reference(), "analysis": reference("analyst")},
            ),
            {
                "id": "approval",
                "type": "approval",
                "config": {"max_review_retries": 2},
                "input_schema": obj(payload=SALES_ANALYSIS_SCHEMA, review=REVIEW),
                "output_schema": SALES_ANALYSIS_SCHEMA,
                "inputs": {"payload": reference("analyst"), "review": reference("reviewer")},
            },
            llm(
                "writer",
                "writer",
                REPORT,
                {"source": SOURCE, "approved_analysis": SALES_ANALYSIS_SCHEMA},
                {"source": reference(), "approved_analysis": reference("approval")},
            ),
        ]
        edges = [
            {"source": a, "target": b}
            for a, b in zip(
                ["analyst", "reviewer", "approval"], ["reviewer", "approval", "writer"], strict=True
            )
        ]
        policy = {
            "quality_revision": {
                "entry_node": "analyst",
                "review_node": "reviewer",
                "nodes": ["analyst", "reviewer"],
                "approval_node": "approval",
                "max_revisions": 2,
                "retry_on_low_score": True,
                "retry_on_high_severity": True,
            }
        }
    result = WorkflowGraph.model_validate(
        {
            "entry_node": nodes[0]["id"],
            "input_schema": SOURCE,
            "output_schema": REPORT,
            "outputs": {"final_output": reference(nodes[-1]["id"], ["final_output"])},
            "nodes": nodes,
            "edges": edges,
            **policy,
        }
    )
    ensure_executable(result)
    return result.model_dump(mode="json")


def install(db):
    """Admin-only, idempotent installation; never overwrite an edited published template."""
    installed = []
    for mode in [RunMode.multi_agent, RunMode.baseline]:
        authorize(db, "workflow.publish")
        db.scalar(select(Organization).where(Organization.id == tenant_id(db)).with_for_update())
        principal = authorize(db, "workflow.publish", lock=True)
        identity = template_id(tenant_id(db), mode)
        item = db.get(WorkflowDefinition, identity)
        if item and item.published_version_id:
            installed.append(item)
            db.commit()
            continue
        prompts = {}
        for kind in ["baseline"] if mode == RunMode.baseline else ["analyst", "reviewer", "writer"]:
            agent_type = AgentType.writer if kind == "baseline" else AgentType(kind)
            try:
                if kind == "baseline":
                    raise AgentSettingsError("Dedicated baseline prompt")
                prompts[kind] = get_agent_runtime_config(db, agent_type).prompt
            except AgentSettingsError as error:
                if kind != "baseline" and not str(error).startswith("Active "):
                    raise HTTPException(409, str(error)) from error
                name = f"Sales template {kind}"
                prompt = db.scalar(
                    select(PromptVersion).where(
                        PromptVersion.name == name,
                        PromptVersion.agent_type == agent_type,
                        PromptVersion.version == 1,
                    )
                )
                if prompt is None:
                    template = (
                        SALES_BASELINE_SYSTEM_PROMPT
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
                name=f"Sales report — {mode.value}",
                description="Published sales workflow template.",
                draft_graph=graph(prompts, mode),
                created_by_user_id=principal.user_id,
            )
            db.add(item)
            db.flush()
        publish(db, item.id, item.draft_revision)
        installed.append(item)
    return installed


def start_sales(db, source, mode):
    authorize(db, "workflow.start", lock=True)
    if source is None or source.input_type.value != WorkflowType.sales_report.value:
        raise HTTPException(422, "A sales input is required")
    definition_id = template_id(tenant_id(db), mode)
    if db.get(WorkflowDefinition, definition_id) is None:
        raise HTTPException(
            409, "An administrator must install the sales templates before starting"
        )
    legacy = WorkflowRun(
        id=uuid.uuid4(), workflow_type=WorkflowType.sales_report, run_mode=mode, input_id=source.id
    )
    start_execution(
        db,
        ExecutionStartRequest(
            definition_id=definition_id,
            idempotency_key=f"sales:{legacy.id}",
            input={"title": source.title, "raw_text": source.raw_text, "notes": source.notes or ""},
        ),
        legacy_run=legacy,
    )
    return legacy
