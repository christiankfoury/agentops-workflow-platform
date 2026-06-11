import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.models.human_approval import ApprovalStatus


class HumanApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_run_id: uuid.UUID
    reviewer_score: float | None
    issues_json: list[Any] | None
    status: ApprovalStatus
    human_feedback: str | None
    edited_analysis_json: dict[str, Any] | None
    approved_by_user_id: uuid.UUID | None
    created_at: datetime
    resolved_at: datetime | None


class HumanApprovalAction(BaseModel):
    human_feedback: str | None = None
    approved_by_user_id: uuid.UUID | None = None


class HumanApprovalEdit(BaseModel):
    human_feedback: str | None = None
    edited_analysis_json: dict[str, Any] | None = None


class ReviewerIssueSummaryRead(BaseModel):
    label: str
    severity: str | None
    count: int


class HumanEditSummaryRead(BaseModel):
    field: str
    count: int
    examples: list[str]


class HumanApprovalTrendPointRead(BaseModel):
    date: str
    total: int
    approved: int
    retry_requested: int
    rejected: int


class HumanFeedbackSummaryRead(BaseModel):
    total_approvals: int
    resolved_approvals: int
    approvals_with_feedback: int
    approvals_with_edits: int
    approval_rate: float
    retry_request_rate: float
    rejection_rate: float
    common_reviewer_issues: list[ReviewerIssueSummaryRead]
    common_human_edits: list[HumanEditSummaryRead]
    approval_trend: list[HumanApprovalTrendPointRead]
