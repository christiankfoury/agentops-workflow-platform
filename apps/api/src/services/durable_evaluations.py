"""Queued evaluations and explicit, revocable administrator approval delegation."""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models.agent_step import AgentStep
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.execution_approval import ExecutionApproval
from src.models.human_approval import HumanApproval
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_execution import WorkflowExecution
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowType
from src.schemas.execution_approval import ApprovalDecision
from src.services import business_templates
from src.services.approval_runtime import decide_approval
from src.services.audit import record_audit
from src.services.evaluation_metrics import calculate_sales_evaluation_scores
from src.services.evaluation_templates import select_template
from src.services.identity import Principal
from src.services.permissions import authorize
from src.services.tenancy import bind_tenant

AUTO_FEEDBACK = "Evaluation runner auto-approved for comparison; no individual human review."


def enabled(db, workflow_type):
    return (
        isinstance(db, Session)
        and {
            WorkflowType.sales_report: settings.sales_template_enabled,
            WorkflowType.customer_feedback: settings.feedback_template_enabled,
            WorkflowType.incident_log: settings.incident_template_enabled,
        }[workflow_type]
    )


def installer(workflow_type):
    from src.services import feedback_template, incident_template, sales_template

    return {
        WorkflowType.sales_report: sales_template.install,
        WorkflowType.customer_feedback: feedback_template.install,
        WorkflowType.incident_log: incident_template.install,
    }[workflow_type]


def enqueue(
    db, case, mode, *, guidance=None, source=None, derive_expected=False, definition_id=None
):
    authorize(db, "evaluation.run")
    if definition_id is None:
        installer(case.workflow_type)(db)
        definition_id = select_template(db, case.workflow_type, mode)
    # Installation may commit; recheck immediately before acceptance.
    principal = authorize(db, "evaluation.run", lock=True)
    try:
        if source is None:
            title = f"Evaluation: {case.title}"
            notes = "Created by evaluation runner." + (f"\n\n{guidance}" if guidance else "")
            source = db.scalar(
                select(UploadedInput)
                .where(
                    UploadedInput.title == title,
                    UploadedInput.raw_text == case.input_text,
                    UploadedInput.input_type == case.workflow_type,
                    UploadedInput.notes == notes,
                )
                .order_by(UploadedInput.created_at, UploadedInput.id)
                .limit(1)
            )
            if source is None:
                source = UploadedInput(
                    title=title,
                    input_type=InputType(case.workflow_type.value),
                    raw_text=case.input_text,
                    notes=notes,
                )
                db.add(source)
                db.flush()
        run = business_templates.start_business(
            db,
            source,
            mode,
            case.workflow_type,
            case.workflow_type.value,
            "evaluation",
            commit=False,
            definition_id=definition_id,
        )
        result = EvaluationResult(
            id=uuid.uuid4(),
            evaluation_case_id=case.id,
            workflow_run_id=run.id,
            run_mode=mode,
            status=EvaluationRunStatus.pending,
            requested_by_user_id=principal.user_id,
            automatic_approval=mode == RunMode.multi_agent,
            derive_expected=derive_expected,
            judge_notes=(
                "Queued durable evaluation. Administrator-authorized automatic approval."
                if mode == RunMode.multi_agent
                else "Queued durable baseline evaluation."
            ),
        )
        db.add(result)
        record_audit(
            db,
            principal,
            "evaluation.enqueue",
            "evaluation_result",
            result.id,
            automatic_approval=result.automatic_approval,
            workflow_run_id=str(run.id),
        )
        db.commit()
        return result
    except BaseException:
        db.rollback()
        raise


def sync(db, run):
    """Update evaluation projections in the execution's own checkpoint transaction."""
    results = db.scalars(
        select(EvaluationResult).where(EvaluationResult.workflow_run_id == run.id)
    ).all()
    if not results:
        return
    cases = {}
    if run.status in {"completed", "failed", "cancelled"}:
        # Lock cases before modifying result rows. This prevents a baseline
        # completion from holding its result while waiting on a deriving peer.
        cases = {
            item.id: item
            for item in db.scalars(
                select(EvaluationCase)
                .where(EvaluationCase.id.in_({result.evaluation_case_id for result in results}))
                .order_by(EvaluationCase.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        }
    approvals = db.scalars(
        select(HumanApproval).where(HumanApproval.workflow_run_id == run.id)
    ).all()
    steps = db.scalars(
        select(AgentStep).where(AgentStep.workflow_run_id == run.id).order_by(AgentStep.step_order)
    ).all()
    for result in results:
        if result.status != EvaluationRunStatus.pending:
            continue
        result.human_approval_required = bool(approvals)
        result.human_approved = (
            any(item.status == "approved" for item in approvals) if approvals else None
        )
        result.retry_count, result.cost, result.latency_ms = (
            run.retry_count,
            run.total_cost,
            run.latency_ms,
        )
        result.prompt_version_summary_json = {
            step.agent_type: str(step.prompt_version_id) if step.prompt_version_id else None
            for step in steps
        }
        router = next(
            (step for step in steps if step.agent_type == "router" and step.status == "completed"),
            None,
        )
        if router:
            result.router_detected_workflow_type = WorkflowType(router.output_json["workflow_type"])
            result.router_confidence = router.output_json["confidence"]
            result.router_correct = result.router_detected_workflow_type == run.workflow_type
        if run.status not in {"completed", "failed", "cancelled"}:
            continue
        if run.status != "completed":
            result.status = EvaluationRunStatus.failed
            result.error_message = f"Workflow ended with status {run.status.value}"
            continue
        case = cases[result.evaluation_case_id]
        if result.derive_expected:
            from src.services.evaluation_promotion import (
                STRUCTURED_AGENT_BY_WORKFLOW,
                EvaluationPromotionError,
                _derive_expected_items,
            )

            approved = next(
                (
                    item
                    for item in reversed(approvals)
                    if item.status == "approved" and item.edited_analysis_json
                ),
                None,
            )
            structured = next(
                (
                    step
                    for step in reversed(steps)
                    if step.agent_type == STRUCTURED_AGENT_BY_WORKFLOW[run.workflow_type]
                    and step.status == "completed"
                ),
                None,
            )
            try:
                items = _derive_expected_items(
                    run.workflow_type,
                    approved.edited_analysis_json
                    if approved
                    else (structured.output_json if structured else {}),
                )
            except EvaluationPromotionError:
                result.status = EvaluationRunStatus.failed
                result.error_message = (
                    "Cannot derive expected items from completed structured output"
                )
                continue
            for key, column in [
                ("facts", "expected_facts_json"),
                ("risks", "expected_risks_json"),
                ("recommendations", "expected_recommendations_json"),
                ("themes", "expected_themes_json"),
                ("timeline", "expected_timeline_json"),
            ]:
                setattr(case, column, items.get(key))
            # A promoted baseline was scored before its expected structured items existed.
            for baseline in db.scalars(
                select(EvaluationResult).where(
                    EvaluationResult.evaluation_case_id == case.id,
                    EvaluationResult.run_mode == RunMode.baseline,
                )
            ):
                baseline_run = db.get(WorkflowRun, baseline.workflow_run_id)
                if baseline_run and baseline_run.status == "completed":
                    score(baseline, case, baseline_run)
        score(result, case, run)


def score(result, case, run):
    values = calculate_sales_evaluation_scores(case, run.final_output)
    result.status = EvaluationRunStatus.completed
    result.factual_accuracy = values.factual_accuracy
    result.unsupported_claim_rate = values.unsupported_claim_rate
    result.completeness_score = values.completeness_score
    result.judge_notes = values.deterministic_notes + (
        " Evaluation has an administrator-authorized automatic-approval policy;"
        " see approval history."
        if result.automatic_approval
        else ""
    )
    result.error_message = None


def advance_approvals(engine):
    """Trusted worker scan; each actual decision rechecks the original admin membership."""
    results, runs, approvals = (
        EvaluationResult.__table__,
        WorkflowExecution.__table__,
        ExecutionApproval.__table__,
    )
    with engine.connect() as connection:
        candidates = connection.execute(
            select(results.c.id, results.c.organization_id, approvals.c.id.label("approval_id"))
            .select_from(
                results.join(runs, runs.c.legacy_run_id == results.c.workflow_run_id).join(
                    approvals, approvals.c.execution_id == runs.c.id
                )
            )
            .where(
                results.c.status == "pending",
                results.c.automatic_approval.is_(True),
                results.c.approval_blocked.is_(False),
                approvals.c.status == "pending",
            )
            .limit(50)
        ).all()
    for candidate in candidates:
        with Session(engine) as db:
            bind_tenant(db, candidate.organization_id)
            result = db.get(EvaluationResult, candidate.id)
            if result is None or result.status != "pending" or not result.automatic_approval:
                continue
            if settings.identity_enabled and result.requested_by_user_id is None:
                result.approval_blocked = True
                result.judge_notes = (
                    "Automatic approval unavailable; an authorized human must review."
                )
                db.commit()
                continue
            db.info["principal"] = Principal(
                role="admin",
                user_id=result.requested_by_user_id,
                organization_id=candidate.organization_id,
            )
            try:
                authorize(db, "evaluation.run", lock=True)
                approval = db.get(ExecutionApproval, candidate.approval_id)
                if approval is not None and approval.status == "pending":
                    decide_approval(
                        db,
                        approval.id,
                        ApprovalDecision(
                            action="approve",
                            expected_payload_hash=approval.payload_hash,
                            human_feedback=AUTO_FEEDBACK,
                        ),
                    )
            except HTTPException as error:
                db.rollback()
                if error.status_code not in {403, 404, 409}:
                    raise
                if error.status_code == 403:
                    result = db.get(EvaluationResult, candidate.id)
                    result.approval_blocked = True
                    result.judge_notes = (
                        "Automatic approval is no longer authorized; "
                        "an authorized human must review."
                    )
                    db.commit()
