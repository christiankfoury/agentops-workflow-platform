import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.models.workflow_run import RunMode, WorkflowStatus, WorkflowType


class WorkflowRunCreate(BaseModel):
    workflow_type: WorkflowType
    run_mode: RunMode = RunMode.multi_agent
    input_id: uuid.UUID | None = None


class WorkflowRunTransition(BaseModel):
    status: WorkflowStatus


class WorkflowRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    workflow_type: WorkflowType
    run_mode: RunMode
    status: WorkflowStatus
    input_id: uuid.UUID | None
    final_output: str | None
    quality_score: float | None
    total_cost: float | None
    total_tokens: int | None
    latency_ms: int | None
    retry_count: int
    created_at: datetime
    completed_at: datetime | None


class WorkflowRunEvaluationComparisonRead(BaseModel):
    evaluation_case_id: uuid.UUID
    baseline_result_id: uuid.UUID
    multi_agent_result_id: uuid.UUID
    baseline_run_id: uuid.UUID
    multi_agent_run_id: uuid.UUID
    comparison_url: str
