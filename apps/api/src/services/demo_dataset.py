import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.evaluation_cases import seed_default_evaluation_cases

DEMO_TITLE_PREFIX = "[Demo]"


@dataclass(frozen=True)
class DemoDatasetSummary:
    evaluation_cases: int
    uploaded_inputs: int
    workflow_runs: int
    evaluation_results: int
    agent_steps: int


def seed_demo_dataset(
    db: Session,
    workflow_types: set[WorkflowType] | None = None,
) -> DemoDatasetSummary:
    cases = seed_default_evaluation_cases(db)
    selected_cases = [
        case for case in cases if workflow_types is None or case.workflow_type in workflow_types
    ]
    created_at_base = datetime.now(UTC) - timedelta(days=len(cases))

    uploaded_inputs = 0
    workflow_runs = 0
    evaluation_results = 0
    agent_steps = 0

    for index, case in enumerate(selected_cases):
        input_record = _upsert_uploaded_input(db, case, created_at_base + timedelta(days=index))
        uploaded_inputs += 1

        baseline_run = _upsert_workflow_run(
            db,
            case=case,
            input_record=input_record,
            run_mode=RunMode.baseline,
            final_output=_build_baseline_output(case),
            quality_score=0.68,
            cost=0.035,
            total_tokens=820,
            latency_ms=4200,
            retry_count=0,
            created_at=created_at_base + timedelta(days=index, minutes=5),
        )
        multi_agent_run = _upsert_workflow_run(
            db,
            case=case,
            input_record=input_record,
            run_mode=RunMode.multi_agent,
            final_output=_build_multi_agent_output(case),
            quality_score=0.91,
            cost=0.128,
            total_tokens=2460,
            latency_ms=18400,
            retry_count=1 if index % 4 == 0 else 0,
            created_at=created_at_base + timedelta(days=index, minutes=15),
        )
        _flush_pending_parents(db)
        workflow_runs += 2

        _upsert_evaluation_result(
            db,
            case=case,
            run=baseline_run,
            factual_accuracy=0.70,
            unsupported_claim_rate=0.22,
            completeness_score=0.64,
            human_approval_required=False,
            human_approved=None,
            judge_notes=(
                "Demo baseline: captures the broad story but misses several expected "
                "facts and includes a higher unsupported-claim rate."
            ),
            created_at=baseline_run.created_at,
        )
        _upsert_evaluation_result(
            db,
            case=case,
            run=multi_agent_run,
            factual_accuracy=0.92,
            unsupported_claim_rate=0.05,
            completeness_score=0.88,
            human_approval_required=multi_agent_run.retry_count > 0,
            human_approved=True if multi_agent_run.retry_count > 0 else None,
            judge_notes=(
                "Demo multi-agent result: reviewer and writer preserve expected facts, "
                "call out known risks, and avoid unsupported numeric claims."
            ),
            created_at=multi_agent_run.created_at,
        )
        evaluation_results += 2

        agent_steps += _upsert_agent_steps(db, case, multi_agent_run)

    db.commit()
    return DemoDatasetSummary(
        evaluation_cases=len(selected_cases),
        uploaded_inputs=uploaded_inputs,
        workflow_runs=workflow_runs,
        evaluation_results=evaluation_results,
        agent_steps=agent_steps,
    )


def _upsert_uploaded_input(
    db: Session, case: EvaluationCase, created_at: datetime
) -> UploadedInput:
    title = f"{DEMO_TITLE_PREFIX} {case.title}"
    input_record = db.query(UploadedInput).filter(UploadedInput.title == title).first()
    if input_record is None:
        input_record = UploadedInput(id=uuid.uuid4(), title=title)
        db.add(input_record)

    input_record.input_type = InputType(case.workflow_type.value)
    input_record.raw_text = case.input_text
    input_record.notes = (
        "Seeded demo input with gold-standard expected facts, risks, and recommendations."
    )
    input_record.file_name = None
    input_record.file_type = "demo"
    input_record.file_size = len(case.input_text.encode("utf-8"))
    input_record.created_at = created_at
    return input_record


def _flush_pending_parents(db: Session) -> None:
    flush = getattr(db, "flush", None)
    if callable(flush):
        flush()


def _upsert_workflow_run(
    db: Session,
    *,
    case: EvaluationCase,
    input_record: UploadedInput,
    run_mode: RunMode,
    final_output: str,
    quality_score: float,
    cost: float,
    total_tokens: int,
    latency_ms: int,
    retry_count: int,
    created_at: datetime,
) -> WorkflowRun:
    run = (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.input_id == input_record.id,
            WorkflowRun.run_mode == run_mode,
        )
        .first()
    )
    if run is None:
        run = WorkflowRun(id=uuid.uuid4(), input_id=input_record.id, run_mode=run_mode)
        db.add(run)

    run.workflow_type = case.workflow_type
    run.status = WorkflowStatus.completed
    run.final_output = final_output
    run.quality_score = quality_score
    run.total_cost = cost
    run.total_tokens = total_tokens
    run.latency_ms = latency_ms
    run.retry_count = retry_count
    run.created_at = created_at
    run.completed_at = created_at + timedelta(milliseconds=latency_ms)
    return run


def _upsert_evaluation_result(
    db: Session,
    *,
    case: EvaluationCase,
    run: WorkflowRun,
    factual_accuracy: float,
    unsupported_claim_rate: float,
    completeness_score: float,
    human_approval_required: bool,
    human_approved: bool | None,
    judge_notes: str,
    created_at: datetime,
) -> EvaluationResult:
    result = (
        db.query(EvaluationResult)
        .filter(
            EvaluationResult.workflow_run_id == run.id,
            EvaluationResult.run_mode == run.run_mode,
        )
        .first()
    )
    if result is None:
        result = EvaluationResult(
            id=uuid.uuid4(),
            evaluation_case_id=case.id,
            run_mode=run.run_mode,
        )
        db.add(result)

    result.workflow_run_id = run.id
    result.status = EvaluationRunStatus.completed
    result.prompt_version_summary_json = _prompt_version_summary()
    result.factual_accuracy = factual_accuracy
    result.unsupported_claim_rate = unsupported_claim_rate
    result.completeness_score = completeness_score
    result.router_detected_workflow_type = case.workflow_type
    result.router_confidence = 0.94
    result.router_correct = True
    result.human_approval_required = human_approval_required
    result.human_approved = human_approved
    result.retry_count = run.retry_count
    result.cost = run.total_cost
    result.latency_ms = run.latency_ms
    result.judge_notes = judge_notes
    result.error_message = None
    result.created_at = created_at
    return result


def _upsert_agent_steps(db: Session, case: EvaluationCase, run: WorkflowRun) -> int:
    step_specs = [
        (
            1,
            "Demo Analyst Agent",
            "analyst",
            {
                "findings": case.expected_facts_json[:4],
                "risks": case.expected_risks_json,
                "recommendations": case.expected_recommendations_json[:2],
            },
            0.041,
            6200,
        ),
        (
            2,
            "Demo Reviewer Agent",
            "reviewer",
            {
                "approved": True,
                "quality_score": 0.91,
                "issues": [],
                "unsupported_claim_checks": case.expected_risks_json,
            },
            0.033,
            4800,
        ),
        (
            3,
            "Demo Writer Agent",
            "writer",
            {
                "final_output": run.final_output,
                "included_expected_items": _expected_item_summary(case),
            },
            0.054,
            7400,
        ),
    ]

    for step_order, agent_name, agent_type, output_json, cost, latency_ms in step_specs:
        step = (
            db.query(AgentStep)
            .filter(
                AgentStep.workflow_run_id == run.id,
                AgentStep.step_order == step_order,
            )
            .first()
        )
        if step is None:
            step = AgentStep(
                id=uuid.uuid4(),
                workflow_run_id=run.id,
                step_order=step_order,
            )
            db.add(step)

        step.agent_name = agent_name
        step.agent_type = agent_type
        step.status = AgentStepStatus.completed
        step.input_json = {
            "workflow_type": case.workflow_type.value,
            "evaluation_case_title": case.title,
        }
        step.output_json = output_json
        step.model = "demo-deterministic"
        step.tokens_input = 700 + step_order * 120
        step.tokens_output = 420 + step_order * 80
        step.total_tokens = step.tokens_input + step.tokens_output
        step.cost = cost
        step.latency_ms = latency_ms
        step.retry_count = run.retry_count if agent_type == "analyst" else 0
        step.error_message = None
        step.created_at = run.created_at + timedelta(seconds=step_order * 3)
        step.completed_at = step.created_at + timedelta(milliseconds=latency_ms)

    return len(step_specs)


def _build_baseline_output(case: EvaluationCase) -> str:
    facts = case.expected_facts_json[:2]
    recommendations = case.expected_recommendations_json[:1]
    lines = [
        f"Baseline summary for {case.title}.",
        "Key points:",
        *[f"- {fact}." for fact in facts],
        "Recommended action:",
        *[f"- {recommendation}." for recommendation in recommendations],
        (
            "Note: this single-agent draft is intentionally less complete for demo "
            "comparison purposes."
        ),
    ]
    return "\n".join(lines)


def _build_multi_agent_output(case: EvaluationCase) -> str:
    lines = [
        f"Reviewed multi-agent report for {case.title}.",
        "Supported facts:",
        *[f"- {fact}." for fact in case.expected_facts_json[:5]],
        "Risks to manage:",
        *[f"- {risk}." for risk in case.expected_risks_json],
        "Recommended actions:",
        *[f"- {recommendation}." for recommendation in case.expected_recommendations_json],
    ]
    if case.expected_themes_json:
        lines.extend(
            [
                "Expected feedback themes:",
                *[f"- {theme}." for theme in case.expected_themes_json],
            ]
        )
    if case.expected_timeline_json:
        lines.extend(
            [
                "Expected incident timeline:",
                *[
                    f"- {item['time']}: {item['event']}."
                    for item in case.expected_timeline_json[:4]
                ],
            ]
        )
    if case.expected_output_notes:
        lines.extend(["Guardrail note:", f"- {case.expected_output_notes}"])
    return "\n".join(lines)


def _expected_item_summary(case: EvaluationCase) -> dict[str, Any]:
    return {
        "facts": len(case.expected_facts_json),
        "risks": len(case.expected_risks_json),
        "recommendations": len(case.expected_recommendations_json),
        "themes": len(case.expected_themes_json or []),
        "timeline_events": len(case.expected_timeline_json or []),
    }


def _prompt_version_summary() -> dict[str, str]:
    return {
        "analyst": "demo-analyst-v1",
        "reviewer": "demo-reviewer-v1",
        "writer": "demo-writer-v1",
    }
