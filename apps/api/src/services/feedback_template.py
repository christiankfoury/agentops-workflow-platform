"""Customer feedback control flow expressed as published graph data."""

from copy import deepcopy

from src.config import settings
from src.models.workflow_run import RunMode, WorkflowType
from src.schemas.workflow_graph import WorkflowGraph
from src.services import business_templates
from src.services.business_outputs import FEEDBACK_MODELS
from src.services.business_schemas import REPORT, SOURCE, STRING, graph_schema, obj, reference
from src.services.execution_registry import ensure_executable
from src.services.feedback_instructions import INSTRUCTIONS
from src.services.sales_baseline import CUSTOMER_FEEDBACK_BASELINE_SYSTEM_PROMPT

CLASSIFICATION, INSIGHT, REVIEW = [
    graph_schema(FEEDBACK_MODELS[key].model_json_schema())
    for key in ["feedback.classification.v1", "feedback.insight.v1", "feedback.review.v1"]
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
            llm("classifier", CLASSIFICATION, "feedback.classification.v1"),
            llm(
                "insight",
                INSIGHT,
                "feedback.insight.v1",
                {"classification": CLASSIFICATION},
                {"classification": reference("classifier")},
            ),
            llm(
                "reviewer",
                REVIEW,
                "feedback.review.v1",
                {"insights": INSIGHT},
                {"insights": reference("insight")},
            ),
            {
                "id": "approval",
                "type": "approval",
                "config": {"max_review_retries": 2, "output_validator": "feedback.insight.v1"},
                "input_schema": obj(payload=INSIGHT, review=REVIEW),
                "output_schema": INSIGHT,
                "inputs": {"payload": reference("insight"), "review": reference("reviewer")},
            },
            llm(
                "writer",
                REPORT,
                "business.final_report.v1",
                {"approved_insights": INSIGHT},
                {"approved_insights": reference("approval")},
            ),
        ]
        policy = {
            "quality_revision": {
                "entry_node": "classifier",
                "review_node": "reviewer",
                "nodes": ["classifier", "insight", "reviewer"],
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
        WorkflowType.customer_feedback,
        "Customer feedback",
        ["classifier", "insight", "reviewer", "writer"],
        CUSTOMER_FEEDBACK_BASELINE_SYSTEM_PROMPT,
        graph,
    )


def start_feedback(db, source, mode):
    return business_templates.start_business(
        db, source, mode, WorkflowType.customer_feedback, "customer feedback", "feedback"
    )
