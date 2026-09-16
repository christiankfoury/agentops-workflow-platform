import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.evaluation_case import EvaluationCase
from src.models.evaluation_result import EvaluationResult
from src.models.human_approval import HumanApproval
from src.models.identity import Membership
from src.models.workflow_definition import WorkflowDefinition
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowType
from src.schemas.human_approval import HumanApprovalAction
from src.services.business_approvals import adapt
from src.services.demo_dataset import seed_demo_dataset
from src.services.durable_evaluations import AUTO_FEEDBACK, enqueue
from src.services.evaluation_promotion import promote_workflow_run_to_evaluation_comparison
from src.services.execution_registry import DEFAULT_REGISTRY
from src.services.identity import Principal
from src.services.prompt_versions import seed_default_prompt_versions
from src.services.tenancy import bind_tenant
from src.worker import run_worker
from tests.test_durable_evaluations import FixtureProvider, case
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_tenant_isolation import tenants as tenants
from tests.test_workflow_transactions_postgres import database as database


def test_revoked_initiator_blocks_automatic_approval_and_allows_manual_recovery(
    database, tenants, monkeypatch
):
    owner = tenants[0]
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        member = db.scalar(select(Membership).where(Membership.organization_id == owner["org"]))
        actor = member.user_id
        db.info["principal"] = Principal("admin", actor, owner["org"])
        seed_default_prompt_versions(db)
        result = enqueue(db, case(db, WorkflowType.sales_report), RunMode.multi_agent)
        identity, run_id = result.id, result.workflow_run_id
        member.role = "viewer"
        db.commit()
    provider = FixtureProvider(WorkflowType.sales_report)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        result = db.get(EvaluationResult, identity)
        assert result.status == "pending" and result.approval_blocked
        assert db.get(WorkflowRun, run_id).status == "waiting_for_human"
        approval = db.scalar(
            select(HumanApproval).where(
                HumanApproval.workflow_run_id == run_id, HumanApproval.status == "pending"
            )
        )
        assert approval.human_feedback != AUTO_FEEDBACK
        member = db.scalar(select(Membership).where(Membership.organization_id == owner["org"]))
        member.role = "admin"
        db.commit()
        db.info["principal"] = Principal("admin", actor, owner["org"])
        adapt(
            db,
            approval,
            "approve",
            HumanApprovalAction(
                expected_payload_hash=approval.expected_payload_hash,
                human_feedback="Individually reviewed after role restoration",
            ),
        )
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        bind_tenant(db, owner["org"])
        assert db.get(EvaluationResult, identity).status == "completed"
        result = db.get(EvaluationResult, identity)
        result.requested_by_user_id = uuid.uuid4()
        with pytest.raises(ValueError, match="immutable"):
            db.commit()


@pytest.mark.parametrize("source_mode", list(RunMode))
def test_promotion_queues_one_counterpart_and_retains_same_input(
    database, monkeypatch, source_mode
):
    provider = FixtureProvider(WorkflowType.customer_feedback)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    with Session(database) as db:
        seed_default_prompt_versions(db)
        result = enqueue(db, case(db, WorkflowType.customer_feedback), source_mode)
        run_id = result.workflow_run_id
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowRun, run_id)
        first = promote_workflow_run_to_evaluation_comparison(db, run, object())
        second = promote_workflow_run_to_evaluation_comparison(db, run, object())
        assert first == second and first.comparison_url.startswith("/workflow-runs/")
        baseline = db.get(WorkflowRun, first.baseline_run_id)
        multi = db.get(WorkflowRun, first.multi_agent_run_id)
        assert baseline.input_id == multi.input_id == run.input_id
        assert len(db.scalars(select(WorkflowRun)).all()) == 2
        case_id = first.evaluation_case_id
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        item = db.get(EvaluationCase, case_id)
        assert item.expected_facts_json and item.expected_recommendations_json
        results = db.scalars(
            select(EvaluationResult).where(EvaluationResult.evaluation_case_id == case_id)
        ).all()
        assert len(results) == 2 and all(result.status == "completed" for result in results)


def test_demo_installation_and_reseed_preserve_durable_owned_run(database, monkeypatch):
    from src.models.uploaded_input import UploadedInput
    from src.services.sales_template import start_sales

    with Session(database) as db:
        seed_demo_dataset(db, {WorkflowType.sales_report})
        source = db.scalar(select(UploadedInput).order_by(UploadedInput.id))
        current = start_sales(db, source, RunMode.baseline)
        identity = current.id
        # Move the durable run ahead of historical rows in ordinary unordered reads.
        assert current.execution_id
        seed_demo_dataset(db, {WorkflowType.sales_report})
        db.refresh(current)
        assert current.status == "created" and current.final_output is None
        assert len(db.scalars(select(WorkflowDefinition)).all()) == 2
    provider = FixtureProvider(WorkflowType.sales_report)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        run = db.get(WorkflowRun, identity)
        before = run.final_output, run.total_tokens, run.total_cost
        seed_demo_dataset(db, {WorkflowType.sales_report})
        db.refresh(run)
        assert (run.final_output, run.total_tokens, run.total_cost) == before


def test_concurrent_promotion_keeps_one_case_and_counterpart(database, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    provider = FixtureProvider(WorkflowType.sales_report)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    with Session(database) as db:
        result = enqueue(db, case(db, WorkflowType.sales_report), RunMode.baseline)
        run_id = result.workflow_run_id
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    barrier = Barrier(2)

    def promote():
        with Session(database) as db:
            run = db.get(WorkflowRun, run_id)
            barrier.wait(timeout=10)
            return promote_workflow_run_to_evaluation_comparison(db, run, object())

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: promote(), range(2)))
    assert first == second
    with Session(database) as db:
        assert len(db.scalars(select(WorkflowRun)).all()) == 2
        assert len(db.scalars(select(EvaluationCase)).all()) == 2


def test_duplicate_worker_approval_resumes_once_after_restart(database, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from src.services.durable_evaluations import advance_approvals

    provider = FixtureProvider(WorkflowType.sales_report)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    with Session(database) as db:
        result = enqueue(db, case(db, WorkflowType.sales_report), RunMode.multi_agent)
        identity = result.id
    # No router is installed, so analyst/reviewer/approval are the first three jobs.
    assert run_worker(database, max_jobs=3, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.scalar(select(HumanApproval)).status == "pending"
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: advance_approvals(database), range(2)))
    assert run_worker(database, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        assert db.get(EvaluationResult, identity).status == "completed"
        assert len(db.scalars(select(HumanApproval)).all()) == 1
        assert len(provider.calls) == 3


def test_promotion_does_not_mix_distinct_uploads_with_identical_titles_and_text(
    database, monkeypatch
):
    from src.models.uploaded_input import UploadedInput
    from src.services.sales_template import install, start_sales

    provider = FixtureProvider(WorkflowType.sales_report)
    monkeypatch.setattr(DEFAULT_REGISTRY, "llm_factory", lambda _: provider)
    with Session(database) as db:
        install(db)
        run_ids = []
        for notes in ["North region", "South region"]:
            source = UploadedInput(
                input_type="sales_report", title="Sales", raw_text="Revenue 10", notes=notes
            )
            db.add(source)
            db.commit()
            run_ids.append(start_sales(db, source, RunMode.baseline).id)
    assert run_worker(database, capacity=2, drain=True, poll_seconds=0.01) == 0
    with Session(database) as db:
        pairs = [
            promote_workflow_run_to_evaluation_comparison(db, db.get(WorkflowRun, identity), None)
            for identity in run_ids
        ]
        assert pairs[0].evaluation_case_id != pairs[1].evaluation_case_id
        for pair in pairs:
            assert (
                db.get(WorkflowRun, pair.baseline_run_id).input_id
                == db.get(WorkflowRun, pair.multi_agent_run_id).input_id
            )
