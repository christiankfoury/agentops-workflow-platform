import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.prompt_version import PromptVersion
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from tests.test_evaluation_runner import EvaluationFakeSession, EvaluationLLMClient
from tests.test_sales_analyst_api import FakeQuery, make_prompt
from tests.test_sales_reviewer_api import make_reviewer_prompt
from tests.test_sales_writer_api import make_writer_prompt


class PromotionFakeSession(EvaluationFakeSession):
    def __init__(self) -> None:
        super().__init__()
        self.evaluation_cases: list[EvaluationCase] = []

    def query(self, model: type) -> FakeQuery:
        if model is EvaluationCase:
            return FakeQuery(self.evaluation_cases)
        return super().query(model)

    def add(self, item: object) -> None:
        if isinstance(item, EvaluationCase) and item not in self.evaluation_cases:
            self.evaluation_cases.append(item)
            return
        super().add(item)

    def refresh(self, item: object) -> None:
        if isinstance(item, EvaluationCase):
            if item.id is None:
                item.id = uuid.uuid4()
            if item.created_at is None:
                item.created_at = datetime.now(UTC)
            return
        super().refresh(item)


def make_uploaded_input() -> UploadedInput:
    return UploadedInput(
        id=uuid.uuid4(),
        title="Q4 Sales Risk Review",
        input_type=InputType.sales_report,
        raw_text=(
            "Q4 revenue increased 6% quarter over quarter to $5.4M. "
            "Enterprise pipeline coverage declined from 3.4x to 2.5x."
        ),
        notes="Manual walkthrough test.",
        created_at=datetime.now(UTC),
    )


def make_source_run(
    input_id: uuid.UUID | None,
    *,
    run_mode: RunMode = RunMode.multi_agent,
    status: WorkflowStatus = WorkflowStatus.completed,
) -> WorkflowRun:
    return WorkflowRun(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        run_mode=run_mode,
        status=status,
        input_id=input_id,
        retry_count=0,
        total_cost=0.042,
        latency_ms=5300,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        final_output=(
            "Q4 revenue increased 6% quarter over quarter to $5.4M. "
            "Prioritize enterprise pipeline recovery."
        ),
    )


def make_source_step(run_id: uuid.UUID) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Sales Analyst Agent",
        agent_type="analyst",
        step_order=1,
        status=AgentStepStatus.completed,
        output_json={
            "key_findings": [
                "Q4 revenue increased 6% quarter over quarter to $5.4M.",
                "Enterprise pipeline coverage declined from 3.4x to 2.5x.",
            ],
            "risks": ["Pipeline decline could affect future sales."],
            "recommendations": ["Prioritize enterprise pipeline recovery."],
            "supporting_evidence": ["Q4 revenue increased to $5.4M."],
        },
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def make_reviewer_step(
    run_id: uuid.UUID,
    issues: list[dict[str, str]] | None = None,
) -> AgentStep:
    return AgentStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        agent_name="Reviewer Agent",
        agent_type="reviewer",
        step_order=2,
        status=AgentStepStatus.completed,
        output_json={
            "approved": True,
            "quality_score": 0.9,
            "retry_recommended": False,
            "issues": issues if issues is not None else [],
        },
        retry_count=0,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def make_evaluation_result(
    case_id: uuid.UUID,
    run: WorkflowRun,
) -> EvaluationResult:
    return EvaluationResult(
        id=uuid.uuid4(),
        evaluation_case_id=case_id,
        workflow_run_id=run.id,
        run_mode=run.run_mode,
        status=EvaluationRunStatus.completed,
        factual_accuracy=0.9,
        unsupported_claim_rate=0.1,
        completeness_score=0.8,
        cost=run.total_cost,
        latency_ms=run.latency_ms,
        created_at=datetime.now(UTC),
    )


def make_agent_prompt(agent_type: AgentType) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        agent_type=agent_type,
        name=f"{agent_type.value.title()} Agent",
        version=1,
        template=f"Run {agent_type.value}.",
        is_active=True,
        created_at=datetime.now(UTC),
    )


def make_db_with_run(
    run_mode: RunMode = RunMode.multi_agent,
) -> tuple[PromotionFakeSession, WorkflowRun]:
    db = PromotionFakeSession()
    uploaded_input = make_uploaded_input()
    run = make_source_run(uploaded_input.id, run_mode=run_mode)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
    if run_mode == RunMode.multi_agent:
        db.steps.append(make_source_step(run.id))
    db.prompts.extend(
        [
            make_prompt(),
            make_reviewer_prompt(),
            make_writer_prompt(),
            make_agent_prompt(AgentType.router),
        ]
    )
    return db, run


def client_for(db: PromotionFakeSession) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: EvaluationLLMClient()
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_compare_this_multi_agent_run_creates_only_baseline_counterpart():
    db, run = make_db_with_run(RunMode.multi_agent)
    original_run_ids = {item.id for item in db.runs}
    client = client_for(db)

    response = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")

    assert response.status_code == 200
    body = response.json()
    assert len(db.evaluation_cases) == 1
    assert len(db.evaluation_results) == 2
    assert body["multi_agent_run_id"] == str(run.id)
    assert body["baseline_run_id"] != str(run.id)
    new_runs = [item for item in db.runs if item.id not in original_run_ids]
    assert len(new_runs) == 1
    assert new_runs[0].run_mode == RunMode.baseline
    clear_overrides()


def test_compare_this_baseline_run_creates_only_multi_agent_counterpart():
    db, run = make_db_with_run(RunMode.baseline)
    original_run_ids = {item.id for item in db.runs}
    client = client_for(db)

    response = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")

    assert response.status_code == 200
    body = response.json()
    assert len(db.evaluation_cases) == 1
    assert len(db.evaluation_results) == 2
    assert body["baseline_run_id"] == str(run.id)
    assert body["multi_agent_run_id"] != str(run.id)
    new_runs = [item for item in db.runs if item.id not in original_run_ids]
    assert len(new_runs) == 1
    assert new_runs[0].run_mode == RunMode.multi_agent
    clear_overrides()


def test_compare_this_run_is_idempotent_after_pair_exists():
    db, run = make_db_with_run(RunMode.multi_agent)
    client = client_for(db)

    first = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")
    runs_after_first = len(db.runs)
    results_after_first = len(db.evaluation_results)
    second = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(db.evaluation_cases) == 1
    assert len(db.runs) == runs_after_first
    assert len(db.evaluation_results) == results_after_first
    assert first.json()["baseline_result_id"] == second.json()["baseline_result_id"]
    assert first.json()["multi_agent_result_id"] == second.json()["multi_agent_result_id"]
    clear_overrides()


def test_rejects_ineligible_source_runs():
    uploaded_input = make_uploaded_input()
    cases = [
        make_source_run(uploaded_input.id, status=WorkflowStatus.writer_running),
        make_source_run(None),
    ]

    for run in cases:
        db = PromotionFakeSession()
        db.inputs.append(uploaded_input)
        db.runs.append(run)
        db.steps.append(make_source_step(run.id))
        client = client_for(db)

        response = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")

        assert response.status_code == 422
        clear_overrides()


def test_rejects_multi_agent_run_without_completed_structured_step():
    db, run = make_db_with_run(RunMode.multi_agent)
    db.steps.clear()
    client = client_for(db)

    response = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")

    assert response.status_code == 422
    assert "completed analyst step" in response.json()["detail"]
    clear_overrides()


def test_create_corrected_run_reuses_baseline_and_adds_multi_agent_result():
    db, source_run = make_db_with_run(RunMode.multi_agent)
    baseline_run = make_source_run(db.inputs[0].id, run_mode=RunMode.baseline)
    case = EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="[Promoted] Q4 Sales Risk Review",
        input_text=db.inputs[0].raw_text,
        expected_facts_json=["Q4 revenue increased 6% quarter over quarter to $5.4M."],
        expected_risks_json=["Pipeline decline could affect future sales."],
        expected_recommendations_json=["Prioritize enterprise pipeline recovery."],
        expected_output_notes="Promoted from a completed workflow run.",
        created_at=datetime.now(UTC),
    )
    db.evaluation_cases.append(case)
    db.runs.append(baseline_run)
    baseline_result = make_evaluation_result(case.id, baseline_run)
    source_result = make_evaluation_result(case.id, source_run)
    db.evaluation_results.extend([baseline_result, source_result])
    db.steps.append(
        make_reviewer_step(
            source_run.id,
            [
                {
                    "claim": "Enterprise coverage is an opportunity.",
                    "problem": "Source lists it as a fact, not an explicit opportunity.",
                    "severity": "low",
                }
            ],
        )
    )
    original_run_ids = {item.id for item in db.runs}
    client = client_for(db)

    response = client.post(f"/evaluation-results/comparisons/{case.id}/corrected-run")

    assert response.status_code == 200
    body = response.json()
    assert body["baseline_result_id"] == str(baseline_result.id)
    assert body["source_multi_agent_run_id"] == str(source_run.id)
    assert body["corrected_multi_agent_run_id"] != str(source_run.id)
    assert len([item for item in db.runs if item.id not in original_run_ids]) == 1
    assert len(db.evaluation_results) == 3
    assert db.evaluation_results[-1].run_mode == RunMode.multi_agent
    assert "Enterprise coverage is an opportunity." in (db.inputs[-1].notes or "")
    assert case.expected_output_notes == "Promoted from a completed workflow run."
    clear_overrides()


def test_create_corrected_run_rejects_clean_comparison():
    db, source_run = make_db_with_run(RunMode.multi_agent)
    baseline_run = make_source_run(db.inputs[0].id, run_mode=RunMode.baseline)
    case = EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="[Promoted] Q4 Sales Risk Review",
        input_text=db.inputs[0].raw_text,
        expected_facts_json=["Q4 revenue increased 6% quarter over quarter to $5.4M."],
        expected_risks_json=["Pipeline decline could affect future sales."],
        expected_recommendations_json=["Prioritize enterprise pipeline recovery."],
        created_at=datetime.now(UTC),
    )
    db.evaluation_cases.append(case)
    db.runs.append(baseline_run)
    db.evaluation_results.extend(
        [
            make_evaluation_result(case.id, baseline_run),
            make_evaluation_result(case.id, source_run),
        ]
    )
    db.steps.append(make_reviewer_step(source_run.id, []))
    client = client_for(db)

    response = client.post(f"/evaluation-results/comparisons/{case.id}/corrected-run")

    assert response.status_code == 422
    assert "no reviewer issues" in response.json()["detail"]
    clear_overrides()
