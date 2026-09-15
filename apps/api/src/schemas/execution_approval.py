import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from src.schemas.workflow_graph import WorkflowGraph


class ReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str
    problem: str
    severity: Literal["low", "medium", "high", "critical"]


class ApprovalReview(BaseModel):
    # Preserve additional structured reviewer rationale/checks used by feedback workflows.
    model_config = ConfigDict(extra="allow")
    approved: bool
    quality_score: float = Field(ge=0, le=1)
    issues: list[ReviewIssue] = Field(max_length=100)
    retry_recommended: bool


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["approve", "edit", "reject", "request_retry"]
    expected_payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    human_feedback: str | None = Field(default=None, max_length=4000)
    edited_payload: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def edit_contract(self):
        if (self.action == "edit") != (self.edited_payload is not None):
            raise ValueError("Only edit decisions require an edited_payload")
        WorkflowGraph.payload_bounds(self.model_dump(mode="json"))
        return self


class ApprovalDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    replacement_id: uuid.UUID | None


class ExecutionApprovalRead(ApprovalDecisionRead):
    execution_id: uuid.UUID
    step_run_id: uuid.UUID
    version_id: uuid.UUID
    node_id: str
    iteration: int
    revision: int
    payload_hash: str
    payload_json: dict
    review_json: dict
    expires_at: datetime | None
    created_at: datetime
    resolved_at: datetime | None
    decided_by_user_id: uuid.UUID | None
    human_feedback: str | None
