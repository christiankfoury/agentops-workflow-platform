import uuid
from datetime import UTC, datetime
from typing import Any

from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.uploaded_input import UploadedInput
from src.models.workflow_run import RunMode, WorkflowType
from src.services.evaluation_runner import run_sales_evaluation_case
from src.services.llm_client import LLMUsage, StructuredResponse, TextResponse
from tests.test_sales_analyst_api import FakeQuery, FakeSession, make_prompt
from tests.test_sales_reviewer_api import make_reviewer_prompt
from tests.test_sales_writer_api import make_writer_prompt


class EvaluationFakeSession(FakeSession):
    def __init__(self) -> None:
        super().__init__()
        self.evaluation_results: list[EvaluationResult] = []

    def query(self, model: type) -> FakeQuery:
        if model is EvaluationResult:
            return FakeQuery(self.evaluation_results)
        return super().query(model)

    def add(self, item: object) -> None:
        if isinstance(item, EvaluationResult) and item not in self.evaluation_results:
            self.evaluation_results.append(item)
            return
        if isinstance(item, UploadedInput) and item not in self.inputs:
            self.inputs.append(item)
            return
        super().add(item)

    def refresh(self, item: object) -> None:
        if isinstance(item, EvaluationResult):
            if item.id is None:
                item.id = uuid.uuid4()
            if item.created_at is None:
                item.created_at = datetime.now(UTC)
            return
        super().refresh(item)


class EvaluationLLMClient:
    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        if "approved" in schema["required"]:
            return StructuredResponse(
                data={
                    "approved": True,
                    "quality_score": 0.91,
                    "issues": [],
                    "retry_recommended": False,
                },
                model="gpt-eval-reviewer",
                usage=LLMUsage(input_tokens=80, output_tokens=20),
            )
        return StructuredResponse(
            data={
                "key_findings": ["Revenue increased 12%"],
                "risks": ["Enterprise churn increased"],
                "opportunities": ["North America growth"],
                "recommendations": ["Prioritize enterprise retention"],
                "supporting_evidence": ["Revenue increased from $4.2M to $4.7M"],
            },
            model="gpt-eval-analyst",
            usage=LLMUsage(input_tokens=100, output_tokens=50),
        )

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> TextResponse:
        return TextResponse(
            content="Executive Summary\nRevenue increased 12%.",
            model="gpt-eval-writer",
            usage=LLMUsage(input_tokens=120, output_tokens=60),
        )


def make_case() -> EvaluationCase:
    return EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.sales_report,
        title="Q1 regional growth and churn",
        input_text="Revenue increased 12%. Enterprise churn increased.",
        expected_facts_json=["Revenue increased 12%"],
        expected_risks_json=["Enterprise churn increased"],
        expected_recommendations_json=["Prioritize enterprise retention"],
        created_at=datetime.now(UTC),
    )


def test_run_sales_evaluation_case_stores_baseline_result():
    db = EvaluationFakeSession()
    evaluation_case = make_case()

    result = run_sales_evaluation_case(
        db,
        evaluation_case,
        RunMode.baseline,
        EvaluationLLMClient(),
    )

    assert result.status == EvaluationRunStatus.completed
    assert result.run_mode == RunMode.baseline
    assert result.workflow_run_id == db.runs[0].id
    assert result.human_approval_required is False
    assert result.human_approved is None
    assert result.retry_count == 0
    assert result.cost == db.runs[0].total_cost
    assert result.latency_ms == db.runs[0].latency_ms
    assert result.factual_accuracy == 1.0
    assert result.unsupported_claim_rate == 0.0
    assert result.completeness_score == 0.3333
    assert db.runs[0].final_output == "Executive Summary\nRevenue increased 12%."


def test_run_sales_evaluation_case_stores_multi_agent_result_after_auto_approval():
    db = EvaluationFakeSession()
    db.prompts.extend([make_prompt(), make_reviewer_prompt(), make_writer_prompt()])
    evaluation_case = make_case()

    result = run_sales_evaluation_case(
        db,
        evaluation_case,
        RunMode.multi_agent,
        EvaluationLLMClient(),
    )

    assert result.status == EvaluationRunStatus.completed
    assert result.run_mode == RunMode.multi_agent
    assert result.workflow_run_id == db.runs[0].id
    assert result.human_approval_required is True
    assert result.human_approved is True
    assert result.retry_count == 0
    assert result.factual_accuracy == 1.0
    assert result.unsupported_claim_rate == 0.0
    assert result.completeness_score == 0.3333
    assert db.approvals[0].human_feedback == "Evaluation runner auto-approved for comparison."
    assert [step.agent_type for step in db.steps] == ["analyst", "reviewer", "writer"]
    assert db.runs[0].final_output == "Executive Summary\nRevenue increased 12%."
