import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.models.human_approval import ApprovalStatus, HumanApproval
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
