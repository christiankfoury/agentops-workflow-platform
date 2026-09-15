from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from src.database import get_db
from src.main import app
from src.models.agent_setting import AgentSetting
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.identity import Membership, Organization, User
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.cost_tracking import record_agent_cost, update_workflow_cost_totals
from src.services.demo_dataset import seed_demo_dataset
from src.services.tenancy import TenantAccessError, bind_tenant
from tests.test_identity import ISSUER, signed_token
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_workflow_transactions_postgres import database as database


@pytest.fixture
def tenants(database, auth_config):
    owners = []
    for subject in ["alice", "bob"]:
        with Session(database) as db:
            org = Organization(name=subject)
            user = User(issuer=ISSUER, subject=subject, display_name=subject)
            db.add_all([org, user])
            db.flush()
            db.add(Membership(user_id=user.id, organization_id=org.id, role="admin"))
            bind_tenant(db, org.id)
            source = UploadedInput(
                title=f"private-{subject}",
                raw_text=f"secret-{subject}",
                input_type=InputType.sales_report,
            )
            prompt = PromptVersion(
                agent_type=AgentType.analyst,
                name="Shared name",
                version=1,
                template=f"secret-{subject}",
                is_active=True,
            )
            db.add_all([source, prompt])
            db.flush()
            run = WorkflowRun(
                workflow_type=WorkflowType.sales_report,
                run_mode=RunMode.baseline,
                status=WorkflowStatus.completed,
                input_id=source.id,
                final_output=f"secret-{subject}",
                completed_at=datetime.now(UTC),
            )
            case = EvaluationCase(
                workflow_type=WorkflowType.sales_report,
                title=f"private-{subject}",
                input_text=f"secret-{subject}",
                expected_facts_json=[subject],
                expected_risks_json=[],
                expected_recommendations_json=[],
            )
            db.add_all([run, case])
            db.flush()
            step = AgentStep(
                workflow_run_id=run.id,
                agent_name="Analyst",
                agent_type="analyst",
                step_order=1,
                status=AgentStepStatus.completed,
                output_json={"private": f"secret-{subject}"},
                model="fixture",
                tokens_input=1,
                tokens_output=2,
                total_tokens=3,
                latency_ms=10,
                prompt_version_id=prompt.id,
            )
            approval = HumanApproval(
                workflow_run_id=run.id,
                status=ApprovalStatus.pending,
                human_feedback=f"secret-{subject}",
            )
            result = EvaluationResult(
                evaluation_case_id=case.id,
                workflow_run_id=run.id,
                run_mode=RunMode.baseline,
                status=EvaluationRunStatus.completed,
                factual_accuracy=0.9,
                completeness_score=1,
                unsupported_claim_rate=0,
                cost=1,
                latency_ms=10,
            )
            db.add_all([step, approval, result])
            db.flush()
            db.add(
                WorkflowEvent(
                    workflow_run_id=run.id,
                    agent_step_id=step.id,
                    event_type=WorkflowEventType.agent_completed,
                    message=f"secret-{subject}",
                )
            )
            record_agent_cost(db, step)
            update_workflow_cost_totals(db, run)
            db.commit()
            owners.append(
                {
                    "org": org.id,
                    "run": run.id,
                    "input": source.id,
                    "prompt": prompt.id,
                    "approval": approval.id,
                    "case": case.id,
                }
            )
    return owners


@pytest.fixture
def tenant_client(database, tenants, signing_key):
    def session():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            client.headers.update(
                {
                    "authorization": "Bearer " + signed_token(signing_key),
                    "x-organization-id": str(tenants[0]["org"]),
                }
            )
            yield client
    finally:
        app.dependency_overrides.clear()


def test_all_resource_lists_exports_and_aggregates_are_scoped(tenant_client, tenants):
    client = tenant_client
    for path in [
        "/workflow-runs",
        "/human-approvals",
        "/prompt-versions",
        "/evaluation-results",
        "/evaluation-results/summary",
        "/evaluation-results/comparisons",
        "/evaluation-results/export/json",
        "/evaluation-results/export/csv",
        "/evaluation-results/export/markdown",
        "/agent-performance",
        "/human-approvals/feedback-summary",
        "/agent-settings",
    ]:
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)
        assert "secret-bob" not in response.text and "private-bob" not in response.text
        for foreign_id in tenants[1].values():
            assert str(foreign_id) not in response.text
    assert len(client.get("/workflow-runs").json()) == 1
    assert client.get("/evaluation-results/summary").json()[0]["run_count"] == 1


def test_foreign_details_nested_reads_and_mutations_are_hidden(tenant_client, tenants):
    other = tenants[1]
    for path in [
        f"/workflow-runs/{other['run']}",
        f"/workflow-runs/{other['run']}/agent-steps",
        f"/workflow-runs/{other['run']}/events",
        f"/uploaded-inputs/{other['input']}",
        f"/prompt-versions/{other['prompt']}",
        f"/human-approvals/{other['approval']}",
    ]:
        assert tenant_client.get(path).status_code == 404
    for path in [
        f"/workflow-runs/{other['run']}/cancel",
        f"/prompt-versions/{other['prompt']}/activate",
        f"/human-approvals/{other['approval']}/approve",
    ]:
        assert tenant_client.post(path).status_code == 404
    assert (
        tenant_client.get(
            "/workflow-runs",
            headers={
                "x-organization-id": str(other["org"]),
            },
        ).status_code
        == 403
    )


def test_api_rejects_cross_tenant_references_and_owner_forgery(tenant_client, tenants):
    other = tenants[1]
    assert (
        tenant_client.post(
            "/workflow-runs",
            json={
                "workflow_type": "sales_report",
                "input_id": str(other["input"]),
            },
        ).status_code
        == 422
    )
    response = tenant_client.post(
        "/uploaded-inputs",
        json={
            "title": "forged",
            "input_type": "sales_report",
            "raw_text": "test",
            "organization_id": str(other["org"]),
        },
    )
    assert response.status_code == 403
    response = tenant_client.put(
        "/agent-settings/analyst",
        json={
            "model": "gpt-4.1-mini",
            "max_tokens": 100,
            "max_retries": 0,
            "active_prompt_version_id": str(other["prompt"]),
        },
    )
    assert response.status_code == 404


def test_alias_aggregate_reads_and_session_get_are_scoped(database, tenants):
    for own, other in [tenants, list(reversed(tenants))]:
        with Session(database) as db:
            bind_tenant(db, own["org"])
            assert db.get(WorkflowRun, other["run"]) is None
            alias = aliased(WorkflowRun)
            assert db.scalars(select(alias)).one().id == own["run"]
            assert db.scalar(select(func.count(WorkflowRun.id))) == 1
            assert db.scalar(select(func.sum(WorkflowRun.total_tokens))) == 3
            with pytest.raises(TenantAccessError):
                bind_tenant(db, other["org"])


def test_orm_and_database_reject_cross_tenant_links(database, tenants):
    own, other = tenants
    with Session(database) as db:
        bind_tenant(db, own["org"])
        run = db.get(WorkflowRun, own["run"])
        run.input_id = other["input"]
        with pytest.raises(TenantAccessError):
            db.commit()
        db.rollback()
        with pytest.raises(TenantAccessError):
            db.execute(update(WorkflowRun).values(final_output="bulk bypass"))
    # A direct SQL client bypasses ORM checks but must still satisfy composite FKs.
    with pytest.raises(IntegrityError):
        with database.begin() as conn:
            conn.execute(
                WorkflowRun.__table__.update()
                .where(
                    WorkflowRun.id == own["run"],
                )
                .values(input_id=other["input"])
            )


def test_demo_seeds_are_independent_tenant_copies(database, tenants):
    seen = []
    for own in tenants:
        with Session(database) as db:
            bind_tenant(db, own["org"])
            first = seed_demo_dataset(db, workflow_types=[WorkflowType.sales_report])
            again = seed_demo_dataset(db, workflow_types=[WorkflowType.sales_report])
            assert first.workflow_runs == again.workflow_runs
            seen.append(set(db.scalars(select(WorkflowRun.id))))
    assert seen[0].isdisjoint(seen[1])


def test_prompt_activation_and_settings_are_independent(tenant_client, tenants, database):
    response = tenant_client.post(
        "/prompt-versions",
        json={
            "agent_type": "analyst",
            "name": "Shared name",
            "version": 2,
            "template": "new alice prompt",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    assert (
        tenant_client.get(f"/prompt-versions/{tenants[0]['prompt']}").json()["is_active"] is False
    )
    for owner in tenants:
        with Session(database) as db:
            bind_tenant(db, owner["org"])
            db.add(
                AgentSetting(
                    agent_type=AgentType.analyst,
                    model="gpt-4.1-mini",
                    max_tokens=100,
                    max_retries=0,
                )
            )
            db.commit()
    with Session(database) as db:
        bind_tenant(db, tenants[1]["org"])
        assert db.get(PromptVersion, tenants[1]["prompt"]).is_active is True


def test_identity_queries_fail_without_scope_and_ownership_is_immutable(database, tenants):
    with Session(database) as db:
        with pytest.raises(TenantAccessError):
            db.scalars(select(WorkflowRun)).all()
    with Session(database) as db:
        bind_tenant(db, tenants[0]["org"])
        run = db.get(WorkflowRun, tenants[0]["run"])
        run.organization_id = tenants[1]["org"]
        with pytest.raises(TenantAccessError):
            db.commit()
