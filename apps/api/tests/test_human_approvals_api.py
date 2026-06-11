import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.workflow_event import WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from tests.test_sales_analyst_api import FakeSession


def make_run(status: WorkflowStatus = WorkflowStatus.waiting_for_human) -> WorkflowRun:
    return WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        run_mode=RunMode.multi_agent,
        status=status,
        retry_count=0,
        created_at=datetime.now(UTC),
    )


def make_approval(
    run_id: uuid.UUID,
    status: ApprovalStatus = ApprovalStatus.pending,
) -> HumanApproval:
    return HumanApproval(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        reviewer_score=0.78,
        issues_json=[
            {
                "claim": "Enterprise churn doubled",
                "problem": "Source only says churn increased",
                "severity": "high",
            }
        ],
        status=status,
        created_at=datetime.now(UTC),
    )


def override_db(db: FakeSession) -> None:
    app.dependency_overrides[get_db] = lambda: db


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_list_and_get_human_approvals():
    db = FakeSession()
    run = make_run()
    approval = make_approval(run.id)
    db.runs.append(run)
    db.approvals.append(approval)
    override_db(db)
    client = TestClient(app)

    listed = client.get("/human-approvals")
    detail = client.get(f"/human-approvals/{approval.id}")

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == str(approval.id)
    assert detail.status_code == 200
    assert detail.json()["workflow_run_id"] == str(run.id)
    clear_overrides()


def test_missing_human_approval_returns_404():
    db = FakeSession()
    override_db(db)
    client = TestClient(app)

    response = client.get(f"/human-approvals/{uuid.uuid4()}")

    assert response.status_code == 404
    clear_overrides()


def test_approve_human_approval_marks_approved_and_advances_workflow():
    db = FakeSession()
    run = make_run()
    approval = make_approval(run.id)
    user_id = uuid.uuid4()
    db.runs.append(run)
    db.approvals.append(approval)
    override_db(db)
    client = TestClient(app)

    response = client.post(
        f"/human-approvals/{approval.id}/approve",
        json={"human_feedback": "Looks good.", "approved_by_user_id": str(user_id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ApprovalStatus.approved
    assert body["human_feedback"] == "Looks good."
    assert body["approved_by_user_id"] == str(user_id)
    assert body["resolved_at"] is not None
    assert run.status == WorkflowStatus.writer_running
    clear_overrides()


def test_request_retry_marks_retry_requested_and_moves_workflow_to_retrying():
    db = FakeSession()
    run = make_run()
    approval = make_approval(run.id)
    db.runs.append(run)
    db.approvals.append(approval)
    override_db(db)
    client = TestClient(app)

    response = client.post(
        f"/human-approvals/{approval.id}/request-retry",
        json={"human_feedback": "Revise unsupported churn claim."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ApprovalStatus.retry_requested
    assert body["human_feedback"] == "Revise unsupported churn claim."
    assert body["resolved_at"] is not None
    assert run.status == WorkflowStatus.retrying
    clear_overrides()


def test_reject_human_approval_marks_rejected_and_cancels_workflow():
    db = FakeSession()
    run = make_run()
    approval = make_approval(run.id)
    db.runs.append(run)
    db.approvals.append(approval)
    override_db(db)
    client = TestClient(app)

    response = client.post(
        f"/human-approvals/{approval.id}/reject",
        json={"human_feedback": "Not acceptable."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ApprovalStatus.rejected
    assert body["human_feedback"] == "Not acceptable."
    assert body["resolved_at"] is not None
    assert run.status == WorkflowStatus.cancelled
    clear_overrides()


def test_edit_human_approval_saves_feedback_and_edited_analysis_without_resolving():
    db = FakeSession()
    run = make_run()
    approval = make_approval(run.id)
    db.runs.append(run)
    db.approvals.append(approval)
    override_db(db)
    client = TestClient(app)

    response = client.post(
        f"/human-approvals/{approval.id}/edit",
        json={
            "human_feedback": "Tightened recommendation.",
            "edited_analysis_json": {"recommendations": ["Focus enterprise retention."]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ApprovalStatus.pending
    assert body["human_feedback"] == "Tightened recommendation."
    assert body["edited_analysis_json"] == {
        "recommendations": ["Focus enterprise retention."]
    }
    assert body["resolved_at"] is None
    assert run.status == WorkflowStatus.waiting_for_human
    assert db.workflow_events[-1].event_type == WorkflowEventType.human_edited_analysis
    assert db.workflow_events[-1].metadata_json["edited_fields"] == ["recommendations"]
    clear_overrides()


def test_human_feedback_summary_tracks_issues_edits_and_decisions():
    db = FakeSession()
    run = make_run()
    approved = make_approval(run.id, status=ApprovalStatus.approved)
    approved.human_feedback = "Tightened claims and recommendation."
    approved.edited_analysis_json = {
        "key_findings": ["Revenue increased 12%."],
        "recommendations": ["Prioritize enterprise retention."],
    }
    approved.resolved_at = datetime(2026, 6, 10, tzinfo=UTC)
    retry = make_approval(run.id, status=ApprovalStatus.retry_requested)
    retry.human_feedback = "Retry with exact source language."
    retry.edited_analysis_json = {"risks": ["Churn claim needs support."]}
    retry.resolved_at = datetime(2026, 6, 11, tzinfo=UTC)
    rejected = make_approval(run.id, status=ApprovalStatus.rejected)
    rejected.issues_json = [
        {
            "claim": "Pipeline doubled",
            "problem": "Pipeline only increased modestly",
            "severity": "medium",
        }
    ]
    rejected.resolved_at = datetime(2026, 6, 11, tzinfo=UTC)
    db.runs.append(run)
    db.approvals.extend([approved, retry, rejected])
    override_db(db)
    client = TestClient(app)

    response = client.get("/human-approvals/feedback-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_approvals"] == 3
    assert body["resolved_approvals"] == 3
    assert body["approvals_with_feedback"] == 2
    assert body["approvals_with_edits"] == 2
    assert body["approval_rate"] == 1 / 3
    assert body["retry_request_rate"] == 1 / 3
    assert body["rejection_rate"] == 1 / 3
    assert body["common_reviewer_issues"][0] == {
        "label": "Source only says churn increased",
        "severity": "high",
        "count": 2,
    }
    edit_fields = {edit["field"]: edit for edit in body["common_human_edits"]}
    assert edit_fields["recommendations"]["count"] == 1
    assert edit_fields["risks"]["examples"] == ["Churn claim needs support."]
    assert body["approval_trend"] == [
        {
            "date": "2026-06-10",
            "total": 1,
            "approved": 1,
            "retry_requested": 0,
            "rejected": 0,
        },
        {
            "date": "2026-06-11",
            "total": 2,
            "approved": 0,
            "retry_requested": 1,
            "rejected": 1,
        },
    ]
    clear_overrides()


def test_edit_human_approval_rejects_when_workflow_is_not_waiting_for_human():
    db = FakeSession()
    run = make_run(status=WorkflowStatus.writer_running)
    approval = make_approval(run.id)
    db.runs.append(run)
    db.approvals.append(approval)
    override_db(db)
    client = TestClient(app)

    response = client.post(
        f"/human-approvals/{approval.id}/edit",
        json={"human_feedback": "Late edit."},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Workflow run is not waiting for human approval"
    clear_overrides()


def test_resolved_human_approval_rejects_followup_action():
    db = FakeSession()
    run = make_run(status=WorkflowStatus.writer_running)
    approval = make_approval(run.id, status=ApprovalStatus.approved)
    approval.resolved_at = datetime.now(UTC)
    db.runs.append(run)
    db.approvals.append(approval)
    override_db(db)
    client = TestClient(app)

    response = client.post(f"/human-approvals/{approval.id}/request-retry")

    assert response.status_code == 422
    assert response.json()["detail"] == "Human approval is already resolved"
    clear_overrides()
