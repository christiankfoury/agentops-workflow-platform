"""Incident control flow expressed as published graph data."""

from copy import deepcopy

from src.config import settings
from src.models.workflow_run import RunMode, WorkflowType
from src.schemas.workflow_graph import WorkflowGraph
from src.services import business_templates
from src.services.business_outputs import INCIDENT_MODELS
from src.services.business_schemas import REPORT, SOURCE, STRING, graph_schema, obj, reference
from src.services.execution_registry import ensure_executable
from src.services.incident_instructions import INSTRUCTIONS
from src.services.sales_baseline import INCIDENT_BASELINE_SYSTEM_PROMPT

TIMELINE, ROOT_CAUSE, REVIEW = [
    graph_schema(INCIDENT_MODELS[key].model_json_schema())
    for key in ["incident.timeline.v1", "incident.root_cause.v1", "incident.review.v1"]
]


def graph(prompts, mode):
    def llm(kind, output, validator, schemas=None, bindings=None):
        return {
            "id": kind,
            "type": "llm",
            "input_schema": obj(source=SOURCE, instructions=STRING, **(schemas or {})),
            "inputs": {
                "source": reference(),
                "instructions": {
                    "op": "literal",
                    "value": INSTRUCTIONS.get(kind, "Write the report."),
                },
                **(bindings or {}),
            },
            "output_schema": deepcopy(output),
            "config": {
                "prompt_version_id": str(prompts[kind].id),
                "model": settings.openai_model,
                "use_agent_settings": kind != "baseline",
                "output_validator": validator,
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

    policy = {}
    if mode == RunMode.baseline:
        nodes = [llm("baseline", REPORT, "business.final_report.v1")]
    else:
        nodes = [
            llm("timeline", TIMELINE, "incident.timeline.v1"),
            llm(
                "root_cause",
                ROOT_CAUSE,
                "incident.root_cause.v1",
                {"timeline": TIMELINE},
                {"timeline": reference("timeline")},
            ),
            llm(
                "reviewer",
                REVIEW,
                "incident.review.v1",
                {"timeline": TIMELINE, "root_cause": ROOT_CAUSE},
                {"timeline": reference("timeline"), "root_cause": reference("root_cause")},
            ),
            {
                "id": "approval",
                "type": "approval",
                "config": {"max_review_retries": 2, "output_validator": "incident.root_cause.v1"},
                "input_schema": obj(payload=ROOT_CAUSE, review=REVIEW),
                "output_schema": ROOT_CAUSE,
                "inputs": {"payload": reference("root_cause"), "review": reference("reviewer")},
            },
            llm(
                "writer",
                REPORT,
                "business.final_report.v1",
                {"timeline": TIMELINE, "approved_root_cause": ROOT_CAUSE},
                {"timeline": reference("timeline"), "approved_root_cause": reference("approval")},
            ),
        ]
        policy = {
            "quality_revision": {
                "entry_node": "timeline",
                "review_node": "reviewer",
                "nodes": ["timeline", "root_cause", "reviewer"],
                "approval_node": "approval",
                "max_revisions": 2,
                "retry_on_low_score": True,
                "retry_on_high_severity": True,
            }
        }
    payload = WorkflowGraph.model_validate(
        {
            "entry_node": nodes[0]["id"],
            "input_schema": SOURCE,
            "output_schema": REPORT,
            "outputs": {"final_output": reference(nodes[-1]["id"], ["final_output"])},
            "nodes": nodes,
            "edges": [
                {"source": left["id"], "target": right["id"]}
                for left, right in zip(nodes, nodes[1:])
            ],
            **policy,
        }
    )
    ensure_executable(payload)
    return payload.model_dump(mode="json")


def install(db):
    return business_templates.install_templates(
        db,
        WorkflowType.incident_log,
        "Incident log",
        ["timeline", "root_cause", "reviewer", "writer"],
        INCIDENT_BASELINE_SYSTEM_PROMPT,
        graph,
    )


def start_incident(db, source, mode):
    return business_templates.start_business(
        db, source, mode, WorkflowType.incident_log, "incident log", "incident"
    )
