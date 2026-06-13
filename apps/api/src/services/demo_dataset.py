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
from src.services.evaluation_comparisons import CORRECTED_RUN_MARKER

DEMO_TITLE_PREFIX = "[Demo]"

REVIEWER_ISSUE_DEMO_CASE: dict[str, Any] = {
    "title": "[Demo] Reviewer issue correction path",
    "input_text": (
        "Q2 Renewal Risk Review\n"
        "Q2 revenue increased 8% quarter over quarter to $5.9M. Enterprise renewal "
        "pipeline coverage declined from 3.2x to 2.4x. APAC revenue grew 15%, while "
        "the Central region missed target by $260K. Mid-market churn rose from 6% to "
        "9% because onboarding tickets remained unresolved. Expansion revenue from "
        "existing customers improved 11%. Three healthcare renewal deals totaling "
        "$810K moved to legal review."
    ),
    "expected_facts_json": [
        "Q2 revenue increased 8% quarter over quarter to $5.9M",
        "Enterprise renewal pipeline coverage declined from 3.2x to 2.4x",
        "APAC revenue grew 15%",
        "Central region missed target by $260K",
        "Mid-market churn rose from 6% to 9%",
        "Expansion revenue improved 11%",
        "Three healthcare renewal deals totaling $810K moved to legal review",
    ],
    "expected_risks_json": [
        "Enterprise renewal pipeline coverage declined",
        "Central region missed target",
        "Mid-market churn increased because onboarding tickets remained unresolved",
        "Healthcare renewal deals moved to legal review",
    ],
    "expected_recommendations_json": [
        "Rebuild enterprise renewal pipeline coverage",
        "Resolve onboarding tickets to reduce mid-market churn",
        "Prioritize legal review for healthcare renewal deals",
    ],
    "expected_output_notes": (
        "Declining enterprise renewal pipeline coverage should be framed as a risk, "
        "not as an opportunity."
    ),
}

REMEDIATION_IMPACT_DEMO_CASE: dict[str, Any] = {
    "title": "[Demo] Remediation impact showcase",
    "input_text": (
        "Q1 Expansion Pipeline Review\n"
        "Q1 revenue increased 9% quarter over quarter to $6.2M. Enterprise pipeline "
        "coverage improved from 2.8x to 3.1x, but mid-market pipeline coverage "
        "declined from 2.4x to 1.9x. APAC revenue grew 16%, while EMEA missed target "
        "by $210K. Customer expansion revenue increased 14% after the account "
        "management team launched renewal playbooks. New-logo conversion declined "
        "from 22% to 18% because trial onboarding tickets took longer to resolve. "
        "Three financial services deals worth $920K advanced to procurement review."
    ),
    "expected_facts_json": [
        "Q1 revenue increased 9% quarter over quarter to $6.2M",
        "Enterprise pipeline coverage improved from 2.8x to 3.1x",
        "Mid-market pipeline coverage declined from 2.4x to 1.9x",
        "APAC revenue grew 16%",
        "EMEA missed target by $210K",
        "Customer expansion revenue increased 14%",
        "New-logo conversion declined from 22% to 18%",
        "Three financial services deals worth $920K advanced to procurement review",
    ],
    "expected_risks_json": [
        "Mid-market pipeline coverage declined",
        "EMEA missed target",
        "New-logo conversion declined because onboarding tickets took longer",
        "Financial services deals are still in procurement review",
    ],
    "expected_recommendations_json": [
        "Reduce trial onboarding ticket resolution time",
        "Monitor mid-market pipeline coverage",
        "Prioritize financial services procurement review",
    ],
    "expected_output_notes": (
        "Enterprise pipeline coverage improvement is a supported fact, but should not "
        "be labeled as an explicit opportunity unless the source says so."
    ),
}

REVIEWER_ISSUE = {
    "claim": "Enterprise renewal pipeline coverage is listed as an opportunity",
    "problem": (
        "The source says enterprise renewal pipeline coverage declined, so this "
        "should be framed as a risk."
    ),
    "severity": "medium",
}

REMEDIATION_PREVIOUS_ISSUE = {
    "claim": "Enterprise segment pipeline coverage is listed as an opportunity",
    "problem": (
        "The source report does not explicitly list enterprise pipeline coverage "
        "improvement as an opportunity, only as a fact."
    ),
    "severity": "low",
}


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

    if workflow_types is None or WorkflowType.sales_report in workflow_types:
        showcase_summary = _seed_showcase_demo_records(
            db,
            created_at_base + timedelta(days=len(selected_cases), hours=1),
        )
        uploaded_inputs += showcase_summary.uploaded_inputs
        workflow_runs += showcase_summary.workflow_runs
        evaluation_results += showcase_summary.evaluation_results
        agent_steps += showcase_summary.agent_steps
        selected_cases.extend(showcase_summary.cases)

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
    title = (
        case.title
        if case.title.startswith(DEMO_TITLE_PREFIX)
        else f"{DEMO_TITLE_PREFIX} {case.title}"
    )
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


@dataclass(frozen=True)
class _ShowcaseSummary:
    cases: list[EvaluationCase]
    uploaded_inputs: int
    workflow_runs: int
    evaluation_results: int
    agent_steps: int


def _seed_showcase_demo_records(db: Session, created_at_base: datetime) -> _ShowcaseSummary:
    action_case = _upsert_showcase_case(db, REVIEWER_ISSUE_DEMO_CASE, created_at_base)
    impact_case = _upsert_showcase_case(
        db,
        REMEDIATION_IMPACT_DEMO_CASE,
        created_at_base + timedelta(minutes=30),
    )

    action_counts = _seed_action_ready_showcase(
        db,
        action_case,
        created_at_base + timedelta(minutes=5),
    )
    impact_counts = _seed_impact_ready_showcase(
        db,
        impact_case,
        created_at_base + timedelta(minutes=35),
    )
    return _ShowcaseSummary(
        cases=[action_case, impact_case],
        uploaded_inputs=action_counts.uploaded_inputs + impact_counts.uploaded_inputs,
        workflow_runs=action_counts.workflow_runs + impact_counts.workflow_runs,
        evaluation_results=(
            action_counts.evaluation_results + impact_counts.evaluation_results
        ),
        agent_steps=action_counts.agent_steps + impact_counts.agent_steps,
    )


def _upsert_showcase_case(
    db: Session,
    default: dict[str, Any],
    created_at: datetime,
) -> EvaluationCase:
    case = (
        db.query(EvaluationCase)
        .filter(
            EvaluationCase.workflow_type == WorkflowType.sales_report,
            EvaluationCase.title == default["title"],
        )
        .first()
    )
    if case is None:
        case = EvaluationCase(
            id=uuid.uuid4(),
            workflow_type=WorkflowType.sales_report,
            title=default["title"],
            created_at=created_at,
        )
        db.add(case)

    case.input_text = default["input_text"]
    case.expected_facts_json = default["expected_facts_json"]
    case.expected_risks_json = default["expected_risks_json"]
    case.expected_recommendations_json = default["expected_recommendations_json"]
    case.expected_themes_json = None
    case.expected_timeline_json = None
    case.expected_output_notes = default["expected_output_notes"]
    return case


def _seed_action_ready_showcase(
    db: Session,
    case: EvaluationCase,
    created_at: datetime,
) -> DemoDatasetSummary:
    input_record = _upsert_uploaded_input(db, case, created_at)
    baseline_run = _upsert_workflow_run(
        db,
        case=case,
        input_record=input_record,
        run_mode=RunMode.baseline,
        final_output=(
            "In Q2, revenue grew 8% to $5.9M. APAC revenue grew 15%, while Central "
            "missed target by $260K. Mid-market churn rose to 9% because onboarding "
            "tickets remained unresolved. Three healthcare renewal deals worth $810K "
            "moved to legal review."
        ),
        quality_score=0.84,
        cost=0.00031,
        total_tokens=830,
        latency_ms=2100,
        retry_count=0,
        created_at=created_at + timedelta(minutes=1),
    )
    multi_agent_run = _upsert_workflow_run(
        db,
        case=case,
        input_record=input_record,
        run_mode=RunMode.multi_agent,
        final_output=(
            "Executive Summary\n\n"
            "Q2 revenue increased 8% quarter over quarter to $5.9M. APAC grew 15%, "
            "and expansion revenue improved 11%. Enterprise renewal pipeline coverage "
            "declined from 3.2x to 2.4x, but the draft incorrectly lists that pipeline "
            "movement as an opportunity. Central missed target by $260K, mid-market "
            "churn rose from 6% to 9% because onboarding tickets remained unresolved, "
            "and three healthcare renewal deals totaling $810K moved to legal review."
        ),
        quality_score=0.82,
        cost=0.00172,
        total_tokens=1970,
        latency_ms=11800,
        retry_count=0,
        created_at=created_at + timedelta(minutes=3),
    )
    _flush_pending_parents(db)

    _upsert_evaluation_result(
        db,
        case=case,
        run=baseline_run,
        factual_accuracy=0.88,
        unsupported_claim_rate=0.04,
        completeness_score=0.82,
        human_approval_required=False,
        human_approved=None,
        judge_notes="Demo baseline for reviewer issue correction path.",
        created_at=baseline_run.created_at,
    )
    _upsert_evaluation_result(
        db,
        case=case,
        run=multi_agent_run,
        factual_accuracy=0.86,
        unsupported_claim_rate=0.18,
        completeness_score=0.90,
        human_approval_required=True,
        human_approved=None,
        judge_notes=(
            "Demo multi-agent result intentionally includes one reviewer issue so "
            "the correction action is available."
        ),
        created_at=multi_agent_run.created_at,
    )
    steps = _upsert_agent_steps(db, case, multi_agent_run, reviewer_issues=[REVIEWER_ISSUE])
    return DemoDatasetSummary(
        evaluation_cases=1,
        uploaded_inputs=1,
        workflow_runs=2,
        evaluation_results=2,
        agent_steps=steps,
    )


def _seed_impact_ready_showcase(
    db: Session,
    case: EvaluationCase,
    created_at: datetime,
) -> DemoDatasetSummary:
    source_input = _upsert_uploaded_input(db, case, created_at)
    corrected_input = _upsert_showcase_uploaded_input(
        db,
        case=case,
        title=f"{case.title} corrected",
        notes=(
            f"{CORRECTED_RUN_MARKER} Seeded demo correction uses the previous "
            "reviewer issue as guidance."
        ),
        created_at=created_at + timedelta(minutes=6),
    )

    baseline_run = _upsert_workflow_run(
        db,
        case=case,
        input_record=source_input,
        run_mode=RunMode.baseline,
        final_output=(
            "In Q1, total revenue grew 9% to $6.2M. Enterprise pipeline coverage "
            "strengthened from 2.8x to 3.1x, while mid-market pipeline coverage "
            "decreased from 2.4x to 1.9x. APAC grew 16%, EMEA missed target by "
            "$210K, and three financial services deals worth $920K advanced to "
            "procurement review."
        ),
        quality_score=0.88,
        cost=0.00034,
        total_tokens=840,
        latency_ms=2420,
        retry_count=0,
        created_at=created_at + timedelta(minutes=1),
    )
    previous_multi_agent_run = _upsert_workflow_run(
        db,
        case=case,
        input_record=source_input,
        run_mode=RunMode.multi_agent,
        final_output=(
            "Executive Summary\n\n"
            "Q1 revenue increased 9% to $6.2M. Enterprise pipeline coverage improved "
            "from 2.8x to 3.1x and is listed as an opportunity. APAC grew 16%, EMEA "
            "missed target by $210K, mid-market coverage declined to 1.9x, and "
            "new-logo conversion declined because onboarding tickets took longer."
        ),
        quality_score=0.90,
        cost=0.00205,
        total_tokens=2210,
        latency_ms=10230,
        retry_count=0,
        created_at=created_at + timedelta(minutes=3),
    )
    corrected_multi_agent_run = _upsert_workflow_run(
        db,
        case=case,
        input_record=corrected_input,
        run_mode=RunMode.multi_agent,
        final_output=(
            "Executive Summary\n\n"
            "Q1 revenue increased 9% quarter over quarter, reaching $6.2M. Enterprise "
            "pipeline coverage improved from 2.8x to 3.1x as a supported fact, while "
            "mid-market pipeline coverage declined from 2.4x to 1.9x. APAC revenue "
            "grew 16%, EMEA missed target by $210K, customer expansion revenue rose "
            "14%, and three financial services deals worth $920K are in procurement "
            "review. The corrected output avoids labeling enterprise coverage as an "
            "explicit opportunity."
        ),
        quality_score=0.93,
        cost=0.00198,
        total_tokens=2160,
        latency_ms=7930,
        retry_count=0,
        created_at=created_at + timedelta(minutes=8),
    )
    _flush_pending_parents(db)

    _upsert_evaluation_result(
        db,
        case=case,
        run=baseline_run,
        factual_accuracy=0.94,
        unsupported_claim_rate=0.00,
        completeness_score=0.91,
        human_approval_required=False,
        human_approved=None,
        judge_notes="Seeded baseline for remediation impact demo.",
        created_at=baseline_run.created_at,
    )
    _upsert_evaluation_result(
        db,
        case=case,
        run=previous_multi_agent_run,
        factual_accuracy=1.00,
        unsupported_claim_rate=0.00,
        completeness_score=1.00,
        human_approval_required=True,
        human_approved=None,
        judge_notes="Previous multi-agent run intentionally has one reviewer issue.",
        created_at=previous_multi_agent_run.created_at,
    )
    _upsert_evaluation_result(
        db,
        case=case,
        run=corrected_multi_agent_run,
        factual_accuracy=0.94,
        unsupported_claim_rate=0.33,
        completeness_score=0.96,
        human_approval_required=False,
        human_approved=True,
        judge_notes=(
            "Corrected run removes reviewer issues but demonstrates mixed benchmark "
            "impact for unsupported-claim scoring."
        ),
        created_at=corrected_multi_agent_run.created_at,
    )
    previous_steps = _upsert_agent_steps(
        db,
        case,
        previous_multi_agent_run,
        reviewer_issues=[REMEDIATION_PREVIOUS_ISSUE],
    )
    corrected_steps = _upsert_agent_steps(db, case, corrected_multi_agent_run)
    return DemoDatasetSummary(
        evaluation_cases=1,
        uploaded_inputs=2,
        workflow_runs=3,
        evaluation_results=3,
        agent_steps=previous_steps + corrected_steps,
    )


def _upsert_showcase_uploaded_input(
    db: Session,
    *,
    case: EvaluationCase,
    title: str,
    notes: str,
    created_at: datetime,
) -> UploadedInput:
    input_record = db.query(UploadedInput).filter(UploadedInput.title == title).first()
    if input_record is None:
        input_record = UploadedInput(id=uuid.uuid4(), title=title)
        db.add(input_record)

    input_record.input_type = InputType(case.workflow_type.value)
    input_record.raw_text = case.input_text
    input_record.notes = notes
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


def _upsert_agent_steps(
    db: Session,
    case: EvaluationCase,
    run: WorkflowRun,
    reviewer_issues: list[dict[str, Any]] | None = None,
) -> int:
    issues = reviewer_issues or []
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
                "approved": not issues,
                "quality_score": 0.91 if not issues else 0.78,
                "issues": issues,
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
