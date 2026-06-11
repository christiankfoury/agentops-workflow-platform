import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.models.evaluation_result import EvaluationRunStatus
from src.models.workflow_run import RunMode, WorkflowType


class EvaluationCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_type: WorkflowType
    title: str
    input_text: str
    expected_facts_json: list[str]
    expected_risks_json: list[str]
    expected_recommendations_json: list[str]
    expected_themes_json: list[str] | None
    expected_timeline_json: list[dict[str, Any]] | None
    expected_output_notes: str | None
    created_at: datetime


class EvaluationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evaluation_case_id: uuid.UUID
    workflow_run_id: uuid.UUID | None
    run_mode: RunMode
    status: EvaluationRunStatus
    prompt_version_summary_json: dict[str, Any] | None
    factual_accuracy: float | None
    unsupported_claim_rate: float | None
    completeness_score: float | None
    router_detected_workflow_type: WorkflowType | None
    router_confidence: float | None
    router_correct: bool | None
    human_approval_required: bool | None
    human_approved: bool | None
    retry_count: int | None
    cost: float | None
    latency_ms: int | None
    judge_notes: str | None
    error_message: str | None
    created_at: datetime


class EvaluationMetricsSummaryRead(BaseModel):
    workflow_type: WorkflowType
    run_mode: RunMode
    run_count: int
    factual_accuracy: float
    unsupported_claim_rate: float
    completeness_score: float
    router_accuracy: float
    average_router_confidence: float
    human_approval_rate: float
    average_cost: float
    average_latency_ms: float
    average_retries: float


class EvaluationComparisonRunRead(BaseModel):
    workflow_run_id: uuid.UUID
    final_output: str | None
    factual_accuracy: float | None
    unsupported_claim_rate: float | None
    completeness_score: float | None
    cost: float
    latency_ms: int


class EvaluationComparisonRead(BaseModel):
    evaluation_case_id: uuid.UUID
    workflow_type: WorkflowType
    title: str
    input_preview: str
    baseline: EvaluationComparisonRunRead
    multi_agent: EvaluationComparisonRunRead
    reviewer_issues: list[dict[str, Any]]
    cost_difference: float
    latency_difference_ms: int
