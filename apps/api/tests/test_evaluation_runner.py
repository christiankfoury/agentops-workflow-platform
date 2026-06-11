import uuid
from datetime import UTC, datetime
from typing import Any

from src.models.agent_type import AgentType
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult, EvaluationRunStatus
from src.models.prompt_version import PromptVersion
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
        if "themes" in schema["required"]:
            return StructuredResponse(
                data={
                    "themes": [
                        {
                            "name": "performance",
                            "count": 1,
                            "sentiment": "negative",
                            "examples": [
                                {"text": "The mobile app is slow.", "source": "review-1"}
                            ],
                        }
                    ],
                    "sentiment_patterns": [
                        {
                            "sentiment": "negative",
                            "count": 1,
                            "summary": "Performance feedback is negative.",
                        }
                    ],
                    "feature_requests": [
                        {
                            "request": "Bulk export",
                            "count": 1,
                            "supporting_examples": [
                                {"text": "Please add bulk export.", "source": "ticket-9"}
                            ],
                        }
                    ],
                    "bug_reports": [],
                },
                model="gpt-eval-classifier",
                usage=LLMUsage(input_tokens=100, output_tokens=60),
            )
        if "top_insights" in schema["required"]:
            return StructuredResponse(
                data={
                    "top_insights": ["Mobile performance is a top customer pain point"],
                    "customer_pain_points": ["Mobile app is slow"],
                    "feature_requests": [
                        {
                            "request": "Bulk export",
                            "count": 1,
                            "supporting_examples": [
                                {"text": "Please add bulk export.", "source": "ticket-9"}
                            ],
                        }
                    ],
                    "risks": ["Mobile performance may hurt retention"],
                    "recommendations": [
                        {
                            "recommendation": "Prioritize mobile performance",
                            "rationale": "Performance feedback is negative.",
                            "supporting_examples": [
                                {"text": "The mobile app is slow.", "source": "review-1"}
                            ],
                        }
                    ],
                    "supporting_examples": [
                        {"text": "The mobile app is slow.", "source": "review-1"},
                        {"text": "Please add bulk export.", "source": "ticket-9"},
                    ],
                },
                model="gpt-eval-insight",
                usage=LLMUsage(input_tokens=120, output_tokens=70),
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
        content = messages[0]["content"]
        if "customer feedback" in content.lower():
            return TextResponse(
                content=(
                    "Product Insights Report\n"
                    "Mobile performance is a top customer pain point. "
                    "Prioritize mobile performance and add bulk export."
                ),
                model="gpt-eval-writer",
                usage=LLMUsage(input_tokens=120, output_tokens=60),
            )
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


def make_customer_feedback_case() -> EvaluationCase:
    return EvaluationCase(
        id=uuid.uuid4(),
        workflow_type=WorkflowType.customer_feedback,
        title="Mobile performance and export requests",
        input_text="The mobile app is slow. Please add bulk export.",
        expected_facts_json=["Mobile performance is a top customer pain point"],
        expected_risks_json=["Mobile performance may hurt retention"],
        expected_recommendations_json=[
            "Prioritize mobile performance",
            "Add bulk export",
        ],
        expected_themes_json=["performance", "feature_requests"],
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
    assert result.prompt_version_summary_json == {"baseline": None}
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
    assert result.prompt_version_summary_json == {
        "analyst": str(db.prompts[0].id),
        "reviewer": str(db.prompts[1].id),
        "writer": str(db.prompts[2].id),
    }
    assert db.approvals[0].human_feedback == "Evaluation runner auto-approved for comparison."
    assert [step.agent_type for step in db.steps] == ["analyst", "reviewer", "writer"]
    assert db.runs[0].final_output == "Executive Summary\nRevenue increased 12%."


def test_run_customer_feedback_evaluation_case_stores_baseline_result():
    db = EvaluationFakeSession()
    evaluation_case = make_customer_feedback_case()

    result = run_sales_evaluation_case(
        db,
        evaluation_case,
        RunMode.baseline,
        EvaluationLLMClient(),
    )

    assert result.status == EvaluationRunStatus.completed
    assert result.run_mode == RunMode.baseline
    assert db.inputs[0].input_type.value == WorkflowType.customer_feedback.value
    assert db.runs[0].workflow_type == WorkflowType.customer_feedback
    assert db.runs[0].final_output.startswith("Product Insights Report")


def test_run_customer_feedback_evaluation_case_stores_multi_agent_result():
    db = EvaluationFakeSession()
    db.prompts.extend(
        [
            make_agent_prompt(AgentType.classifier),
            make_agent_prompt(AgentType.insight),
            make_reviewer_prompt(),
            make_writer_prompt(),
        ]
    )
    evaluation_case = make_customer_feedback_case()

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
    assert result.completeness_score == 0.75
    assert result.prompt_version_summary_json == {
        "classifier": str(db.prompts[0].id),
        "insight": str(db.prompts[1].id),
        "reviewer": str(db.prompts[2].id),
        "writer": str(db.prompts[3].id),
    }
    assert db.approvals[0].human_feedback == "Evaluation runner auto-approved for comparison."
    assert [step.agent_type for step in db.steps] == [
        "classifier",
        "insight",
        "reviewer",
        "writer",
    ]
    assert db.runs[0].final_output.startswith("Product Insights Report")
