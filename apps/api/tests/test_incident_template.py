import json
from copy import deepcopy

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep
from src.models.uploaded_input import UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun
from src.schemas.human_approval import HumanApprovalAction, HumanApprovalEdit
from src.services import human_approvals
from src.services.business_approvals import adapt
from src.services.incident_reviewer import run_incident_reviewer
from src.services.incident_root_cause import run_incident_root_cause
from src.services.incident_template import install, start_incident
from src.services.incident_timeline import run_incident_timeline
from src.services.incident_writer import run_incident_writer
from src.services.llm_client import LLMUsage, TextResponse
from src.services.prompt_versions import seed_default_prompt_versions
from src.services.sales_baseline import run_sales_baseline
from src.services.workflow_recovery import cancel_workflow_run
from src.services.workflow_state import initialize_run
from tests.test_feedback_template import pending
from tests.test_incident_reviewer_writer_api import ROOT_CAUSE_OUTPUT, TIMELINE_OUTPUT
from tests.test_llm_execution import Provider
from tests.test_quality_revisions import review
from tests.test_sales_template import drain
from tests.test_workflow_transactions_postgres import database as database

REPORT = "Incident report. Connection pool saturation is likely; the original cause is unknown."
TIMELINE = {**TIMELINE_OUTPUT, "ambiguous_events": ["Alert received without a timestamp"]}
REVIEW = review(approved=True, retry=False, score=0.95)


class LegacyProvider(Provider):
    def generate_text(self, **kwargs):
        self.calls.append(kwargs)
        return TextResponse(REPORT, "gpt-4.1-mini", LLMUsage(10, 5))


def start(database, mode=RunMode.multi_agent):
    with Session(database) as db:
        seed_default_prompt_versions(db)
        install(db)
        source = UploadedInput(
            title="Incident fixture",
            input_type="incident_log",
            raw_text="10:15 AM - Database connection pool saturated\n"
            "Alert received without timestamp",
        )
        db.add(source)
        db.commit()
        current = start_incident(db, source, mode)
        legacy = initialize_run(
            db, WorkflowRun(workflow_type="incident_log", run_mode=mode, input_id=source.id)
        )
        return current.id, legacy.id


@pytest.mark.parametrize("action", ["approve", "edit", "reject", "cancel", "baseline"])
def test_incident_old_new_parity_preserves_ambiguity_and_edits(database, monkeypatch, action):
    current, legacy = start(
        database, RunMode.baseline if action == "baseline" else RunMode.multi_agent
    )
    provider = LegacyProvider([TIMELINE, ROOT_CAUSE_OUTPUT, REVIEW])
    changed = {**ROOT_CAUSE_OUTPUT, "unknowns": ["Human verified evidence limitation"]}
    with Session(database) as db:
        old = db.get(WorkflowRun, legacy)
        if action == "baseline":
            run_sales_baseline(db, old, provider)
        else:
            for agent in [run_incident_timeline, run_incident_root_cause, run_incident_reviewer]:
                assert agent(db, old, provider).status == "completed"
            approval = pending(db, legacy)
            if action == "edit":
                human_approvals.edit_human_approval(db, approval, "Preserve unknowns", changed)
            if action == "reject":
                human_approvals.reject_human_approval(db, approval)
            elif action == "cancel":
                cancel_workflow_run(db, old)
            else:
                human_approvals.approve_human_approval(db, approval)
                run_incident_writer(db, old, provider)
    if action == "baseline":
        drain(database, monkeypatch, [{"final_output": REPORT}])
    else:
        drain(database, monkeypatch, [TIMELINE, ROOT_CAUSE_OUTPUT, REVIEW])
        with Session(database) as db:
            approval = pending(db, current)
            if action == "edit":
                approval = adapt(
                    db,
                    approval,
                    "edit",
                    HumanApprovalEdit(
                        expected_payload_hash=approval.expected_payload_hash,
                        edited_analysis_json=changed,
                        human_feedback="Preserve unknowns",
                    ),
                )
            if action == "cancel":
                cancel_workflow_run(db, db.get(WorkflowRun, current))
            else:
                adapt(
                    db,
                    approval,
                    "reject" if action == "reject" else "approve",
                    HumanApprovalAction(expected_payload_hash=approval.expected_payload_hash),
                )
        if action not in {"cancel", "reject"}:
            writer = drain(database, monkeypatch, [{"final_output": REPORT}])
            inputs = json.loads(writer.calls[0]["messages"][0]["content"])["input"]
            assert inputs["timeline"] == TIMELINE
            assert inputs["approved_root_cause"] == (
                changed if action == "edit" else ROOT_CAUSE_OUTPUT
            )
    with Session(database) as db:
        old, new = db.get(WorkflowRun, legacy), db.get(WorkflowRun, current)
        assert (
            old.status
            == new.status
            == ("cancelled" if action in {"reject", "cancel"} else "completed")
        )
        assert old.final_output == new.final_output and old.total_tokens == new.total_tokens

        def outputs(identity):
            return [
                step.output_json
                for step in db.scalars(
                    select(AgentStep)
                    .where(AgentStep.workflow_run_id == identity)
                    .order_by(AgentStep.step_order)
                )
            ]

        assert outputs(legacy) == outputs(current)


def test_incident_revision_uses_new_timeline_and_rejects_invalid_human_edit(database, monkeypatch):
    current, _ = start(database)
    changed = deepcopy(TIMELINE)
    changed["ambiguous_events"] = ["A new unresolved timestamp"]
    provider = drain(
        database,
        monkeypatch,
        [TIMELINE, ROOT_CAUSE_OUTPUT, review(), changed, ROOT_CAUSE_OUTPUT, REVIEW],
    )
    assert json.loads(provider.calls[4]["messages"][0]["content"])["input"]["timeline"] == changed
    with Session(database) as db:
        assert db.get(WorkflowRun, current).retry_count == 1
        approval = pending(db, current)
        bad = deepcopy(ROOT_CAUSE_OUTPUT)
        bad["impact"][0]["severity"] = "invented"
        with pytest.raises(HTTPException) as error:
            adapt(
                db,
                approval,
                "edit",
                HumanApprovalEdit(
                    expected_payload_hash=approval.expected_payload_hash, edited_analysis_json=bad
                ),
            )
        assert error.value.status_code == 422
        assert pending(db, current).id == approval.id


def test_incident_api_normalization_queue_and_legacy_deprecation(database, monkeypatch):
    from fastapi.testclient import TestClient
    from pydantic import SecretStr

    from src.config import settings
    from src.database import get_db
    from src.dependencies import get_llm_client
    from src.main import app

    def connection():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = connection
    app.dependency_overrides[get_llm_client] = lambda: object()
    monkeypatch.setattr(settings, "openai_api_key", SecretStr(""))
    try:
        with TestClient(app) as client:
            source = client.post(
                "/uploaded-inputs",
                json={
                    "title": "Incident API",
                    "input_type": "incident_log",
                    "raw_text": (
                        "10:15 AM - Database connection pool saturated\nAlert without a timestamp"
                    ),
                },
            )
            assert source.status_code == 201, source.text
            assert "Parsed incident events:" in source.json()["raw_text"]
            assert "Ambiguous incident log lines:" in source.json()["raw_text"]
            assert (
                client.post("/workflow-definitions/templates/incident/install").status_code == 200
            )
            started = client.post(
                "/workflow-runs",
                json={
                    "workflow_type": "incident_log",
                    "run_mode": "baseline",
                    "input_id": source.json()["id"],
                },
            )
            assert started.status_code == 201, started.text
            identity = started.json()["id"]
            assert client.post(f"/workflow-runs/{identity}/run-baseline").status_code == 409
            provider = drain(database, monkeypatch, [{"final_output": REPORT}])
            assert (
                json.loads(provider.calls[0]["messages"][0]["content"])["input"]["source"][
                    "raw_text"
                ]
                == source.json()["raw_text"]
            )
            comparison = client.post(f"/workflow-runs/{identity}/evaluation-comparison")
            assert comparison.status_code == 200, comparison.text
            assert comparison.json()["comparison_url"].startswith("/workflow-runs/")
            assert client.get("/openapi.json").json()["paths"][
                "/workflow-runs/{run_id}/run-baseline"
            ]["post"]["deprecated"]
            monkeypatch.setattr(settings, "incident_template_enabled", False)
            old = client.post(
                "/workflow-runs",
                json={"workflow_type": "incident_log", "input_id": source.json()["id"]},
            )
            assert old.status_code == 201 and old.json()["execution_id"] is None
    finally:
        app.dependency_overrides.clear()
