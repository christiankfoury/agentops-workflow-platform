from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_openapi_registers_workflow_evaluation_and_demo_routes():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    expected_paths = {
        "/workflow-runs",
        "/workflow-runs/{run_id}",
        "/workflow-runs/{run_id}/agent-steps",
        "/workflow-runs/{run_id}/events",
        "/workflow-runs/{run_id}/run-analyst",
        "/workflow-runs/{run_id}/run-reviewer",
        "/workflow-runs/{run_id}/run-writer",
        "/workflow-runs/{run_id}/evaluation-comparison",
        "/human-approvals",
        "/human-approvals/{approval_id}/approve",
        "/uploaded-inputs",
        "/uploaded-inputs/upload",
        "/uploaded-inputs/detect-workflow",
        "/evaluation-results/summary",
        "/evaluation-results/comparisons",
        "/evaluation-results/export/markdown",
        "/agent-performance",
        "/demo/sales-report",
        "/demo/customer-feedback",
        "/demo/incident-log",
        "/demo/full-evaluation",
    }

    assert expected_paths.issubset(paths.keys())


def test_openapi_exposes_workflow_run_create_schema_defaults():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    workflow_create = response.json()["components"]["schemas"]["WorkflowRunCreate"]

    assert workflow_create["properties"]["run_mode"]["default"] == "multi_agent"
    assert workflow_create["required"] == ["workflow_type"]
