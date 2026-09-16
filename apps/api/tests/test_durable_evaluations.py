from copy import deepcopy

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.agent_step import AgentStep
from src.models.cost_event import CostEvent
from src.models.durable_job import DurableJob
from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult
from src.models.human_approval import HumanApproval
from src.models.uploaded_input import UploadedInput
from src.models.workflow_execution import WorkflowExecution
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowType
from src.services.durable_evaluations import AUTO_FEEDBACK, enqueue
from src.services.evaluation_comparisons import build_evaluation_comparisons
from src.services.evaluation_metrics import calculate_sales_evaluation_scores
from src.services.evaluation_runner import run_sales_evaluation_case
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.llm_client import LLMUsage, StructuredResponse
from src.services.prompt_versions import seed_default_prompt_versions
from src.services.workflow_recovery import cancel_workflow_run
from src.worker import run_worker
from tests.test_customer_feedback_reviewer_writer_api import (
    CLASSIFIER_OUTPUT,
    PRODUCT_INSIGHT_OUTPUT,
    REVIEWER_OUTPUT,
)
from tests.test_incident_reviewer_writer_api import ROOT_CAUSE_OUTPUT, TIMELINE_OUTPUT
from tests.test_quality_revisions import review
from tests.test_sales_template import ANALYSIS
from tests.test_workflow_transactions_postgres import database as database

REPORT = "Revenue 10. Improve mobile checkout. Add connection pool alerts."


class FixtureProvider:
    def __init__(self, workflow_type):
        self.workflow_type, self.calls = workflow_type, []

    def close(self):
        pass

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        properties = kwargs["schema"]["properties"]
        if "workflow_type" in properties:
            output = {
                "workflow_type": self.workflow_type,
                "confidence": 0.95,
                "reasoning_summary": "Fixture classification",
            }
        elif "final_output" in properties:
            output = {"final_output": REPORT}
        elif "key_findings" in properties:
            output = ANALYSIS
        elif "themes" in properties:
            output = CLASSIFIER_OUTPUT
        elif "top_insights" in properties:
            output = PRODUCT_INSIGHT_OUTPUT
        elif "timeline" in properties:
            output = TIMELINE_OUTPUT
        elif "suspected_root_cause" in properties:
            output = ROOT_CAUSE_OUTPUT
        elif "approval_rationale" in properties:
            output = REVIEWER_OUTPUT
        else:
            assert "approved" in properties
            output = review(approved=True, retry=False, score=0.95)
        return StructuredResponse(deepcopy(output), kwargs["model"], LLMUsage(10, 5))


def case(db, workflow_type):
    item = EvaluationCase(
        workflow_type=workflow_type,
        title=f"Fixture {workflow_type}",
        input_text=REPORT,
        expected_facts_json=["Revenue 10"],
        expected_risks_json=[],
        expected_recommendations_json=["Add connection pool alerts"],
    )
    db.add(item)
    db.commit()
    return item


@pytest.mark.parametrize("workflow_type", list(WorkflowType))
def test_queued_evaluation_parity_scoring_router_costs_and_comparisons(
    database, monkeypatch, workflow_type
):
    with Session(database) as db:
        seed_default_prompt_versions(db)
        item = case(db, workflow_type)
        baseline = run_sales_evaluation_case(db, item, RunMode.baseline, object())
        multi = run_sales_evaluation_case(db, item, RunMode.multi_agent, object())
        assert baseline.status == multi.status == "pending"
        identities = [baseline.id, multi.id]
        runs = [db.get(WorkflowRun, result.workflow_run_id) for result in [baseline, multi]]
        assert runs[0].input_id == runs[1].input_id
        assert all(run.execution_id for run in runs)
        assert len(db.scalars(select(DurableJob)).all()) == 2
        assert not db.scalars(select(AgentStep)).all()
    provider = FixtureProvider(workflow_type)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        results = [db.get(EvaluationResult, identity) for identity in identities]
        assert all(result.status == "completed" and result.router_correct for result in results)
        assert results[1].human_approved and results[1].human_approval_required
        approval = db.scalar(select(HumanApproval))
        assert approval.human_feedback == AUTO_FEEDBACK
        assert not results[0].human_approval_required
        cases, runs, steps = (
            db.scalars(select(EvaluationCase)).all(),
            db.scalars(select(WorkflowRun)).all(),
            db.scalars(select(AgentStep)).all(),
        )
        comparisons = build_evaluation_comparisons(
            cases, results, runs, steps, db.scalars(select(UploadedInput)).all()
        )
        assert len(comparisons) == 1
        expected = calculate_sales_evaluation_scores(cases[0], REPORT)
        assert (
            results[0].factual_accuracy == results[1].factual_accuracy == expected.factual_accuracy
        )
        assert (
            results[0].completeness_score
            == results[1].completeness_score
            == expected.completeness_score
        )
        assert sum(run.total_tokens for run in runs) == len(provider.calls) * 15
        assert sum(event.total_cost for event in db.scalars(select(CostEvent))) == pytest.approx(
            sum(run.total_cost for run in runs)
        )
        assert len(db.scalars(select(WorkflowExecution)).all()) == 2


def test_cancelled_evaluation_is_failed_without_provider_work(database):
    with Session(database) as db:
        result = enqueue(db, case(db, WorkflowType.incident_log), RunMode.multi_agent)
        cancel_workflow_run(db, db.get(WorkflowRun, result.workflow_run_id))
        db.refresh(result)
        assert result.status == "failed" and "cancelled" in result.error_message
        assert not db.scalars(select(HumanApproval)).all()


def test_evaluation_acceptance_rolls_back_result_run_and_queue(database, monkeypatch):
    from src.services import durable_evaluations

    with Session(database) as db:
        item = case(db, WorkflowType.sales_report)

        def fail(*args, **kwargs):
            raise RuntimeError("Injected evaluation audit failure")

        monkeypatch.setattr(durable_evaluations, "record_audit", fail)
        with pytest.raises(RuntimeError, match="Injected"):
            enqueue(db, item, RunMode.baseline)
        for model in [EvaluationResult, WorkflowRun, WorkflowExecution, DurableJob, UploadedInput]:
            assert db.scalars(select(model)).all() == []


def test_corrected_comparison_queues_guidance_without_provider_io(database, monkeypatch):
    from src.services.evaluation_remediation import create_corrected_evaluation_comparison_run

    provider = FixtureProvider(WorkflowType.sales_report)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    with Session(database) as db:
        item = case(db, WorkflowType.sales_report)
        case_id = item.id
        enqueue(db, item, RunMode.baseline)
        original = enqueue(db, item, RunMode.multi_agent)
        original_run_id = original.workflow_run_id
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        review_step = db.scalar(
            select(AgentStep).where(
                AgentStep.workflow_run_id == original_run_id, AgentStep.agent_type == "reviewer"
            )
        )
        review_step.output_json = {
            **review_step.output_json,
            "issues": [{"severity": "low", "claim": "Revenue", "problem": "Verify source"}],
        }
        db.commit()
        before = len(provider.calls)
        corrected = create_corrected_evaluation_comparison_run(db, case_id, None)
        assert len(provider.calls) == before
        result = db.get(EvaluationResult, corrected.corrected_result_id)
        assert result.status == "pending"
        run = db.get(WorkflowRun, corrected.corrected_multi_agent_run_id)
        source = db.get(UploadedInput, run.input_id)
        assert source.raw_text == db.get(EvaluationCase, case_id).input_text
        assert "not source facts" in source.notes and "Verify source" in source.notes
        assert corrected.comparison_url == f"/workflow-runs/{run.id}"
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(EvaluationResult, corrected.corrected_result_id).status == "completed"
