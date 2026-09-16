"""Published sales workflow graphs."""

from copy import deepcopy

from src.config import settings
from src.models.workflow_run import RunMode, WorkflowType
from src.schemas.workflow_graph import WorkflowGraph
from src.services import business_templates
from src.services.business_schemas import REPORT, SOURCE, graph_schema, obj, reference
from src.services.execution_registry import ensure_executable
from src.services.sales_analyst import SALES_ANALYSIS_SCHEMA
from src.services.sales_baseline import SALES_BASELINE_SYSTEM_PROMPT
from src.services.sales_reviewer import SALES_REVIEW_SCHEMA


def template_id(organization_id, mode):
    return business_templates.template_id(organization_id, WorkflowType.sales_report, mode)


REVIEW = graph_schema(SALES_REVIEW_SCHEMA)


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
    return business_templates.install_templates(
        db,
        WorkflowType.sales_report,
        "Sales report",
        ["analyst", "reviewer", "writer"],
        SALES_BASELINE_SYSTEM_PROMPT,
        graph,
        prompt_label="Sales",
    )


def start_sales(db, source, mode):
    return business_templates.start_business(
        db, source, mode, WorkflowType.sales_report, "sales", "sales"
    )
