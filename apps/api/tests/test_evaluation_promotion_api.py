import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.database import get_db
from src.dependencies import get_llm_client
from src.main import app
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.agent_type import AgentType
from src.models.evaluation_case import EvaluationCase
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


def make_source_run(input_id: uuid.UUID | None, **overrides: object) -> WorkflowRun:
    values = {
        "id": uuid.uuid4(),
        "workflow_type": WorkflowType.sales_report,
        "run_mode": RunMode.multi_agent,
        "status": WorkflowStatus.completed,
        "input_id": input_id,
        "retry_count": 0,
        "created_at": datetime.now(UTC),
        "completed_at": datetime.now(UTC),
        "final_output": "Manual executive summary.",
    }
    values.update(overrides)
    return WorkflowRun(**values)


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


def make_db_with_promotable_run() -> tuple[PromotionFakeSession, WorkflowRun]:
    db = PromotionFakeSession()
    uploaded_input = make_uploaded_input()
    run = make_source_run(uploaded_input.id)
    db.inputs.append(uploaded_input)
    db.runs.append(run)
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


def client_for(db: PromotionFakeSession) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: EvaluationLLMClient()
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_promotes_completed_sales_multi_agent_run_into_comparison():
    db, run = make_db_with_promotable_run()
    client = client_for(db)

    response = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")

    assert response.status_code == 200
    body = response.json()
    assert body["comparison_url"].startswith("/workflow-comparison?search=%5BPromoted%5D")
    assert len(db.evaluation_cases) == 1
    assert db.evaluation_cases[0].title == "[Promoted] Q4 Sales Risk Review"
    assert len(db.evaluation_results) == 2
    assert {result.run_mode for result in db.evaluation_results} == {
        RunMode.baseline,
        RunMode.multi_agent,
    }
    assert body["baseline_run_id"] != str(run.id)
    assert body["multi_agent_run_id"] != str(run.id)
    clear_overrides()


def test_rejects_ineligible_source_runs():
    uploaded_input = make_uploaded_input()
    cases = [
        make_source_run(uploaded_input.id, run_mode=RunMode.baseline),
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


def test_rejects_run_without_completed_structured_step():
    db, run = make_db_with_promotable_run()
    db.steps.clear()
    client = client_for(db)

    response = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")

    assert response.status_code == 422
    assert "completed analyst step" in response.json()["detail"]
    clear_overrides()


def test_reuses_existing_promoted_case_but_creates_fresh_result_pairs():
    db, run = make_db_with_promotable_run()
    existing_case = EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="[Promoted] Q4 Sales Risk Review",
        input_text=db.inputs[0].raw_text,
        expected_facts_json=["Q4 revenue increased 6%"],
        expected_risks_json=["Pipeline decline could affect future sales."],
        expected_recommendations_json=["Prioritize enterprise pipeline recovery."],
        created_at=datetime.now(UTC),
    )
    db.evaluation_cases.append(existing_case)
    client = client_for(db)

    first = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")
    second = client.post(f"/workflow-runs/{run.id}/evaluation-comparison")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(db.evaluation_cases) == 1
    assert len(db.evaluation_results) == 4
    assert first.json()["evaluation_case_id"] == str(existing_case.id)
    assert second.json()["evaluation_case_id"] == str(existing_case.id)
    assert first.json()["baseline_result_id"] != second.json()["baseline_result_id"]
    assert first.json()["multi_agent_result_id"] != second.json()["multi_agent_result_id"]
    clear_overrides()
