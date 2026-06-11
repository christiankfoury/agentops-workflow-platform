from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.customer_feedback_classifier import run_customer_feedback_classifier
from src.services.customer_feedback_insight import run_customer_feedback_insight
from src.services.customer_feedback_reviewer import run_customer_feedback_reviewer
from src.services.customer_feedback_writer import run_customer_feedback_writer
from src.services.evaluation_metrics import calculate_sales_evaluation_scores
from src.services.human_approvals import approve_human_approval
from src.services.incident_reviewer import run_incident_reviewer
from src.services.incident_root_cause import run_incident_root_cause
from src.services.incident_timeline import run_incident_timeline
from src.services.incident_writer import run_incident_writer
from src.services.llm_client import StructuredResponse, TextResponse
from src.services.sales_analyst import run_sales_analyst
from src.services.sales_baseline import run_sales_baseline
from src.services.sales_reviewer import run_sales_reviewer
from src.services.sales_writer import run_sales_writer


class EvaluationRunnerError(Exception):
    pass


class LLMClientLike(Protocol):
    def generate_structured(
        self,
        messages: list[dict],
        schema: dict,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        pass

    def generate_text(
        self,
        messages: list[dict],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> TextResponse:
        pass


def run_sales_evaluation_case(
    db: Session,
    evaluation_case: EvaluationCase,
    run_mode: RunMode,
    llm_client: LLMClientLike,
) -> EvaluationResult:
    if evaluation_case.workflow_type not in {
        WorkflowType.sales_report,
        WorkflowType.customer_feedback,
        WorkflowType.incident_log,
    }:
        raise EvaluationRunnerError(
            "Evaluation runner only supports sales report, customer feedback, "
            "and incident log cases"
        )

    result = EvaluationResult(
        evaluation_case_id=evaluation_case.id,
        run_mode=run_mode,
        status=EvaluationRunStatus.pending,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    try:
        uploaded_input = _create_uploaded_input(db, evaluation_case)
        run = _create_workflow_run(db, evaluation_case, uploaded_input, run_mode)
        if run_mode == RunMode.baseline:
            run_sales_baseline(db, run, llm_client)
            human_approval_required = False
            human_approved = None
        elif run_mode == RunMode.multi_agent:
            human_approval_required, human_approved = _run_multi_agent_case(
                db,
                run,
                llm_client,
            )
        else:
            raise EvaluationRunnerError(f"Unsupported run mode: {run_mode}")

        _complete_result(
            db,
            result,
            evaluation_case,
            run,
            human_approval_required=human_approval_required,
            human_approved=human_approved,
        )
    except Exception as e:
        result.status = EvaluationRunStatus.failed
        result.error_message = str(e)
        db.commit()
        db.refresh(result)

    return result


def run_sales_evaluation_suite(
    db: Session,
    cases: list[EvaluationCase],
    llm_client: LLMClientLike,
    run_modes: tuple[RunMode, ...] = (RunMode.baseline, RunMode.multi_agent),
) -> list[EvaluationResult]:
    results: list[EvaluationResult] = []
    for evaluation_case in cases:
        for run_mode in run_modes:
            results.append(run_sales_evaluation_case(db, evaluation_case, run_mode, llm_client))
    return results


def _create_uploaded_input(db: Session, evaluation_case: EvaluationCase) -> UploadedInput:
    uploaded_input = UploadedInput(
        title=f"Evaluation: {evaluation_case.title}",
        input_type=InputType(evaluation_case.workflow_type.value),
        raw_text=evaluation_case.input_text,
        notes="Created by evaluation runner.",
    )
    db.add(uploaded_input)
    db.commit()
    db.refresh(uploaded_input)
    return uploaded_input


def _create_workflow_run(
    db: Session,
    evaluation_case: EvaluationCase,
    uploaded_input: UploadedInput,
    run_mode: RunMode,
) -> WorkflowRun:
    run = WorkflowRun(
        workflow_type=evaluation_case.workflow_type,
        run_mode=run_mode,
        status=WorkflowStatus.created,
        input_id=uploaded_input.id,
        retry_count=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _run_multi_agent_case(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> tuple[bool, bool | None]:
    if run.workflow_type == WorkflowType.customer_feedback:
        return _run_customer_feedback_multi_agent_case(db, run, llm_client)
    if run.workflow_type == WorkflowType.incident_log:
        return _run_incident_multi_agent_case(db, run, llm_client)

    run_sales_analyst(db, run, llm_client)
    if run.status == WorkflowStatus.failed:
        return False, None

    while run.status == WorkflowStatus.reviewer_running:
        run_sales_reviewer(db, run, llm_client)
        if run.status == WorkflowStatus.retrying:
            run_sales_analyst(db, run, llm_client)
        if run.status == WorkflowStatus.failed:
            return False, None

    if run.status == WorkflowStatus.waiting_for_human:
        approval = _get_pending_approval(db, run.id)
        if approval is None:
            raise EvaluationRunnerError("Pending human approval not found")
        approve_human_approval(
            db,
            approval,
            human_feedback="Evaluation runner auto-approved for comparison.",
        )
        run_sales_writer(db, run, llm_client)
        return True, True

    if run.status == WorkflowStatus.writer_running:
        run_sales_writer(db, run, llm_client)
        return False, None

    return False, None


def _run_incident_multi_agent_case(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> tuple[bool, bool | None]:
    run_incident_timeline(db, run, llm_client)
    if run.status == WorkflowStatus.failed:
        return False, None

    run_incident_root_cause(db, run, llm_client)
    if run.status == WorkflowStatus.failed:
        return False, None

    run_incident_reviewer(db, run, llm_client)
    if run.status == WorkflowStatus.failed:
        return False, None

    if run.status == WorkflowStatus.waiting_for_human:
        approval = _get_pending_approval(db, run.id)
        if approval is None:
            raise EvaluationRunnerError("Pending human approval not found")
        approve_human_approval(
            db,
            approval,
            human_feedback="Evaluation runner auto-approved for comparison.",
        )
        run_incident_writer(db, run, llm_client)
        return True, True

    if run.status == WorkflowStatus.writer_running:
        run_incident_writer(db, run, llm_client)
        return False, None

    return False, None


def _run_customer_feedback_multi_agent_case(
    db: Session,
    run: WorkflowRun,
    llm_client: LLMClientLike,
) -> tuple[bool, bool | None]:
    run_customer_feedback_classifier(db, run, llm_client)
    if run.status == WorkflowStatus.failed:
        return False, None

    run_customer_feedback_insight(db, run, llm_client)
    if run.status == WorkflowStatus.failed:
        return False, None

    run_customer_feedback_reviewer(db, run, llm_client)
    if run.status == WorkflowStatus.failed:
        return False, None

    if run.status == WorkflowStatus.waiting_for_human:
        approval = _get_pending_approval(db, run.id)
        if approval is None:
            raise EvaluationRunnerError("Pending human approval not found")
        approve_human_approval(
            db,
            approval,
            human_feedback="Evaluation runner auto-approved for comparison.",
        )
        run_customer_feedback_writer(db, run, llm_client)
        return True, True

    if run.status == WorkflowStatus.writer_running:
        run_customer_feedback_writer(db, run, llm_client)
        return False, None

    return False, None


def _get_pending_approval(db: Session, run_id: uuid.UUID) -> HumanApproval | None:
    return (
        db.query(HumanApproval)
        .filter(
            HumanApproval.workflow_run_id == run_id,
            HumanApproval.status == ApprovalStatus.pending,
        )
        .first()
    )


def _complete_result(
    db: Session,
    result: EvaluationResult,
    evaluation_case: EvaluationCase,
    run: WorkflowRun,
    *,
    human_approval_required: bool,
    human_approved: bool | None,
) -> None:
    result.workflow_run_id = run.id
    result.status = (
        EvaluationRunStatus.completed
        if run.status == WorkflowStatus.completed
        else EvaluationRunStatus.failed
    )
    result.human_approval_required = human_approval_required
    result.human_approved = human_approved
    result.retry_count = run.retry_count
    result.cost = run.total_cost
    result.latency_ms = run.latency_ms
    result.prompt_version_summary_json = _prompt_version_summary(db, run)
    if result.status == EvaluationRunStatus.completed:
        scores = calculate_sales_evaluation_scores(evaluation_case, run.final_output)
        result.factual_accuracy = scores.factual_accuracy
        result.unsupported_claim_rate = scores.unsupported_claim_rate
        result.completeness_score = scores.completeness_score
    if result.status == EvaluationRunStatus.failed:
        result.error_message = f"Workflow ended with status {run.status.value}"
    db.commit()
    db.refresh(result)


def _prompt_version_summary(db: Session, run: WorkflowRun) -> dict[str, str | None]:
    steps = db.query(AgentStep).filter(AgentStep.workflow_run_id == run.id).all()
    summary: dict[str, str | None] = {}
    for step in sorted(steps, key=lambda item: item.step_order):
        summary[step.agent_type] = (
            str(step.prompt_version_id) if step.prompt_version_id is not None else None
        )
    return summary
