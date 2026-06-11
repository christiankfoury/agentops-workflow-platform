from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.agent_step import AgentStep
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowType
from src.schemas.evaluation import (
    EvaluationComparisonRead,
    EvaluationMetricsSummaryRead,
    EvaluationResultRead,
)
from src.services.evaluation_comparisons import build_evaluation_comparisons
from src.services.evaluation_metrics import summarize_evaluation_results

router = APIRouter()


@router.get("", response_model=list[EvaluationResultRead])
def list_evaluation_results(db: Session = Depends(get_db)) -> list[EvaluationResult]:
    return db.query(EvaluationResult).order_by(EvaluationResult.created_at.desc()).all()


@router.get("/summary", response_model=list[EvaluationMetricsSummaryRead])
def get_evaluation_summary(db: Session = Depends(get_db)) -> list[EvaluationMetricsSummaryRead]:
    results = db.query(EvaluationResult).all()
    cases = db.query(EvaluationCase).all()
    case_workflows = {case.id: case.workflow_type for case in cases}
    summaries: list[EvaluationMetricsSummaryRead] = []
    for workflow_type in (
        WorkflowType.sales_report,
        WorkflowType.customer_feedback,
        WorkflowType.incident_log,
    ):
        workflow_results = [
            result
            for result in results
            if case_workflows.get(result.evaluation_case_id) == workflow_type
        ]
        for run_mode in (RunMode.baseline, RunMode.multi_agent):
            mode_results = [result for result in workflow_results if result.run_mode == run_mode]
            metrics = summarize_evaluation_results(mode_results)
            summaries.append(
                EvaluationMetricsSummaryRead(
                    workflow_type=workflow_type,
                    run_mode=run_mode,
                    run_count=metrics.run_count,
                    factual_accuracy=metrics.factual_accuracy,
                    unsupported_claim_rate=metrics.unsupported_claim_rate,
                    completeness_score=metrics.completeness_score,
                    router_accuracy=metrics.router_accuracy,
                    average_router_confidence=metrics.average_router_confidence,
                    human_approval_rate=metrics.human_approval_rate,
                    average_cost=metrics.average_cost,
                    average_latency_ms=metrics.average_latency_ms,
                    average_retries=metrics.average_retries,
                )
            )
    return summaries


@router.get("/comparisons", response_model=list[EvaluationComparisonRead])
def get_evaluation_comparisons(
    db: Session = Depends(get_db),
) -> list[EvaluationComparisonRead]:
    cases = db.query(EvaluationCase).all()
    results = db.query(EvaluationResult).all()
    runs = db.query(WorkflowRun).all()
    steps = db.query(AgentStep).all()
    return build_evaluation_comparisons(cases, results, runs, steps)
