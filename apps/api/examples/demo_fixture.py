"""Credential-free walkthrough fixture. See docs/demo-walkthrough.md; never production."""

import argparse
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config import settings
from src.database import engine
from src.models.human_approval import HumanApproval
from src.models.identity import Organization
from src.models.tenant import DEFAULT_ORGANIZATION_ID
from src.models.uploaded_input import UploadedInput
from src.models.workflow_definition import WorkflowVersion
from src.models.workflow_execution import WorkflowExecution
from src.models.workflow_run import RunMode, WorkflowRun
from src.schemas.tool import ToolContract, ToolCreate
from src.schemas.workflow_definition import DefinitionCreate
from src.schemas.workflow_graph import WorkflowGraph
from src.services import tool_catalog, workflow_definitions
from src.services.demo_dataset import seed_demo_dataset
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.llm_client import LLMUsage, StructuredResponse
from src.services.sales_template import start_sales
from src.worker import run_worker

ANALYSIS = {
    "key_findings": ["Revenue is $10 million."],
    "risks": ["Renewal pipeline coverage declined from 3.2x to 2.4x."],
    "opportunities": [],
    "recommendations": ["Review renewal coverage."],
    "supporting_evidence": ["Source reports $10 million and coverage of 3.2x then 2.4x."],
}
REVIEW = {
    "approved": True, "quality_score": 0.95, "issues": [], "retry_recommended": False,
}
STRING, BOOLEAN = {"type": "string"}, {"type": "boolean"}


def obj(**fields):
    return {"type": "object", "properties": fields, "required": list(fields)}


def literal(value):
    return {"op": "literal", "value": value}


def graph(tool_id):
    payload = obj(request=STRING)
    return {
        "entry_node": "route",
        "input_schema": obj(check=BOOLEAN),
        "nodes": [
            {
                "id": "route", "type": "condition",
                "config": {
                    "cases": [{"label": "review", "when": {
                        "op": "ref", "ref": {"source": "input", "path": ["check"]},
                    }}],
                    "default": "skip",
                },
            },
            {
                "id": "gate", "type": "approval",
                "config": {"deadline_seconds": 3600},
                "input_schema": obj(payload=payload, review=obj(
                    approved=BOOLEAN, quality_score={"type": "number"},
                    issues={"type": "array", "items": obj(
                        claim=STRING, problem=STRING, severity=STRING,
                    )}, retry_recommended=BOOLEAN,
                )),
                "output_schema": payload,
                "inputs": {
                    "payload": literal({"request": "Read the local demo fixture status."}),
                    "review": literal(REVIEW),
                },
            },
            {
                "id": "read_status", "type": "tool",
                "input_schema": obj(),
                "output_schema": obj(status={"type": "integer"}, body=obj(status=STRING)),
                "config": {"tool_id": str(tool_id), "version": 1},
                "retry": {
                    "max_attempts": 2, "initial_delay_seconds": 5,
                    "jitter_fraction": 0, "retryable_errors": ["tool_unavailable"],
                },
            },
            {"id": "skip", "type": "transform", "config": {"assign": {}}},
        ],
        "edges": [
            {"source": "route", "target": "gate", "label": "review"},
            {"source": "route", "target": "skip", "label": "skip"},
            {"source": "gate", "target": "read_status"},
        ],
    }


class SyntheticProvider:
    """Three declared responses only; no network/client fallback or paid usage."""

    def generate_structured(self, **kwargs):
        fields = set(kwargs["schema"]["properties"])
        if fields == set(ANALYSIS):
            output = ANALYSIS
        elif fields == set(REVIEW):
            output = REVIEW
        elif fields == {"final_output"}:
            data = json.loads(kwargs["messages"][0]["content"])["input"]
            approved = data["approved_analysis"]
            output = {"final_output": (
                "# Synthetic sales report\n\nRevenue is $10 million. Renewal pipeline "
                "coverage declined from 3.2x to 2.4x.\n\n## Approved recommendations\n\n"
                + "\n".join(f"- {item}" for item in approved["recommendations"])
            )}
        else:
            raise ValueError("Unexpected demo model schema; no provider fallback")
        return StructuredResponse(output, kwargs["model"], LLMUsage(0, 0))

    def close(self):
        pass


def guard():
    if (
        settings.environment != "development" or settings.identity_enabled
        or engine.url.host not in {"localhost", "127.0.0.1"}
        or not (engine.url.database or "").startswith("phase104_demo_")
        or bool(engine.url.query)
    ):
        raise ValueError(
            "Requires development, local identity and a loopback phase104_demo_* DB; "
            "URL query parameters are not allowed"
        )


def require_single_organization(db):
    # Organization is not tenant-filtered. The example worker must never claim
    # another tenant's jobs with its synthetic model implementation.
    if db.scalar(select(Organization.id).where(
        Organization.id != DEFAULT_ORGANIZATION_ID,
    ).limit(1)) is not None:
        raise ValueError("Demo fixture requires a single local organization")


def drain(manifest):
    guard()
    if manifest["database"] != engine.url.database:
        raise ValueError("Manifest/database mismatch")
    with Session(engine) as db:
        require_single_organization(db)
        active = db.scalars(select(WorkflowExecution).where(
            WorkflowExecution.status.not_in(["completed", "failed", "cancelled"]),
        )).all()
        for run in active:
            if (
                str(run.id) != manifest["sales_execution_id"]
                and str(db.get(WorkflowVersion, run.version_id).definition_id)
                != manifest["definition_id"]
            ):
                raise ValueError("Unrelated active work; refusing to run a synthetic provider")
    previous = DEFAULT_REGISTRY.llm_factory
    try:
        DEFAULT_REGISTRY.llm_factory = lambda _: SyntheticProvider()
        return run_worker(engine, capacity=1, drain=True, poll_seconds=0.05)
    finally:
        DEFAULT_REGISTRY.llm_factory = previous


def seed(path):
    guard()
    if path.exists():
        raise ValueError("Manifest exists; use a new disposable database and manifest")
    with Session(engine) as db:
        require_single_organization(db)
        if db.scalar(select(func.count()).select_from(WorkflowRun)) or db.scalar(
            select(func.count()).select_from(WorkflowExecution)
        ):
            raise ValueError("Database already contains runs; use a fresh migrated database")
        summary = seed_demo_dataset(db)
        tool = tool_catalog.create(db, ToolCreate(
            name="[Demo fixture] Local status read",
            contract=ToolContract(
                adapter="http", input_schema=obj(),
                output_schema=obj(status={"type": "integer"}, body=obj(status=STRING)),
                options={"destination": "demo", "method": "GET", "path": "/health"},
                retry={"max_attempts": 2, "initial_delay_seconds": 5,
                       "jitter_fraction": 0, "retryable_errors": ["tool_unavailable"]},
            ),
        ))
        definition = workflow_definitions.create_definition(db, DefinitionCreate(
            name="[Demo fixture] Reviewed status check",
            description="Local condition, approval and read-only HTTP retry fixture.",
            graph=WorkflowGraph.model_validate(graph(tool.definition_id)).model_dump(mode="json"),
        ))
        source = UploadedInput(
            title="[Demo fixture] Synthetic sales approval", input_type="sales_report",
            raw_text=("Revenue is $10 million. "
                      "Renewal pipeline coverage declined from 3.2x to 2.4x."),
        )
        db.add(source)
        db.commit()
        sales = start_sales(db, source, RunMode.multi_agent)
        manifest = {
            "database": engine.url.database, "definition_id": str(definition.id),
            "sales_run_id": str(sales.id), "sales_execution_id": str(sales.execution_id),
            "seeded_comparison_counts": asdict(summary),
            "label": "Synthetic model/assigned evaluation values; local HTTP/runtime execution",
        }
    if drain(manifest) != 0:
        raise RuntimeError("Fixture worker failed")
    with Session(engine) as db:
        approval = db.scalar(select(HumanApproval).where(
            HumanApproval.workflow_run_id == sales.id, HumanApproval.status == "pending",
        ))
        if approval is None:
            raise RuntimeError("Expected pending sales approval")
        manifest["sales_approval_id"] = str(approval.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def serve():
    class Handler(BaseHTTPRequestHandler):
        failed_once = False

        def do_GET(self):
            if self.path != "/health":
                self.send_error(404)
                return
            status = 200 if Handler.failed_once else 503
            Handler.failed_once = True
            payload = b'{"status":"ok"}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_):
            pass

    print("Loopback fixture :8144; first /health GET returns 503, subsequent GETs 200", flush=True)
    with HTTPServer(("127.0.0.1", 8144), Handler) as server:
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "drain", "serve"])
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if args.action == "serve":
        serve()
    elif args.manifest is None:
        parser.error("seed/drain require --manifest")
    elif args.action == "seed":
        seed(args.manifest)
    else:
        raise SystemExit(drain(json.loads(args.manifest.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
