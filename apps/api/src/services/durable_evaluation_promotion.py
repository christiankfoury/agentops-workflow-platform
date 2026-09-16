"""Comparison creation queues one counterpart against the same immutable source."""

import uuid

from sqlalchemy import select

from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult
from src.models.human_approval import HumanApproval
from src.models.identity import Organization
from src.models.workflow_run import RunMode
from src.services.durable_evaluations import enqueue, installer
from src.services.evaluation_templates import select_template
from src.services.permissions import authorize
from src.services.tenancy import tenant_id


def promote(db, run, source):
    from src.services import evaluation_promotion as legacy

    mode = RunMode.baseline if run.run_mode == RunMode.multi_agent else RunMode.multi_agent
    installer(run.workflow_type)(db)
    definition_id = select_template(db, run.workflow_type, mode)
    # One short metadata transaction serializes case creation and duplicate promotion.
    # There is no executor I/O or intermediate commit while this lock is held.
    authorize(db, "evaluation.run")
    db.scalar(select(Organization).where(Organization.id == tenant_id(db)).with_for_update())
    authorize(db, "evaluation.run", lock=True)
    title = f"[Promoted] {source.title}"
    provenance = f"Promoted from uploaded input {source.id}."
    case = db.scalar(
        select(EvaluationCase)
        .where(
            EvaluationCase.workflow_type == run.workflow_type,
            EvaluationCase.title == title,
            EvaluationCase.input_text == source.raw_text,
            EvaluationCase.expected_output_notes == provenance,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if case is None:
        case = EvaluationCase(
            id=uuid.uuid4(),
            workflow_type=run.workflow_type,
            title=title,
            input_text=source.raw_text,
            expected_facts_json=[],
            expected_risks_json=[],
            expected_recommendations_json=[],
            expected_output_notes=provenance,
        )
        db.add(case)
        db.flush()
    if run.run_mode == RunMode.multi_agent:
        approvals = db.scalars(
            select(HumanApproval)
            .where(
                HumanApproval.workflow_run_id == run.id,
                HumanApproval.status == "approved",
            )
            .order_by(HumanApproval.resolved_at.desc())
        ).all()
        edited = next(
            (
                item.edited_analysis_json
                for item in approvals
                if item.edited_analysis_json is not None
            ),
            None,
        )
        output = (
            edited
            if edited is not None
            else legacy._get_latest_completed_structured_step(db, run).output_json
        )
        items = legacy._derive_expected_items(run.workflow_type, output or {})
        for key, column in [
            ("facts", "expected_facts_json"),
            ("risks", "expected_risks_json"),
            ("recommendations", "expected_recommendations_json"),
            ("themes", "expected_themes_json"),
            ("timeline", "expected_timeline_json"),
        ]:
            setattr(case, column, items.get(key))
    original = db.scalar(
        select(EvaluationResult)
        .where(
            EvaluationResult.evaluation_case_id == case.id,
            EvaluationResult.workflow_run_id == run.id,
        )
        .limit(1)
    )
    if original is None:
        original = EvaluationResult(
            id=uuid.uuid4(),
            evaluation_case_id=case.id,
            workflow_run_id=run.id,
            run_mode=run.run_mode,
            status="completed",
        )
        db.add(original)
    legacy._score_existing_run_result(db, original, case, run)
    counterpart = db.scalar(
        select(EvaluationResult)
        .where(
            EvaluationResult.evaluation_case_id == case.id,
            EvaluationResult.run_mode == mode,
            EvaluationResult.status.in_(["pending", "completed"]),
        )
        .order_by(EvaluationResult.created_at.desc())
        .limit(1)
    )
    if counterpart is None:
        counterpart = enqueue(
            db,
            case,
            mode,
            source=source,
            definition_id=definition_id,
            derive_expected=mode == RunMode.multi_agent and not case.expected_facts_json,
        )
    else:
        if counterpart.status == "completed":
            from src.models.workflow_run import WorkflowRun

            legacy._score_existing_run_result(
                db, counterpart, case, db.get(WorkflowRun, counterpart.workflow_run_id)
            )
        db.commit()
    baseline, multi = (
        (counterpart, original) if mode == RunMode.baseline else (original, counterpart)
    )
    result = legacy._promotion_result(case, baseline, multi)
    if counterpart.status == "pending":
        return legacy.EvaluationPromotionResult(
            **{**result.__dict__, "comparison_url": f"/workflow-runs/{counterpart.workflow_run_id}"}
        )
    return result
