"""Real independent-session lifecycle checks; set WORKFLOW_TEST_DATABASE_URL."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from src.database import Base
from src.models.agent_step import AgentStep, AgentStepStatus
from src.models.cost_event import CostEvent
from src.models.human_approval import ApprovalStatus, HumanApproval
from src.models.identity import Organization
from src.models.tenant import DEFAULT_ORGANIZATION_ID
from src.models.uploaded_input import InputType, UploadedInput
from src.models.workflow_event import WorkflowEvent, WorkflowEventType
from src.models.workflow_run import RunMode, WorkflowRun, WorkflowStatus, WorkflowType
from src.services.human_approvals import (
    approve_human_approval,
    edit_human_approval,
    reject_human_approval,
)
from src.services.llm_client import LLMUsage, TextResponse
from src.services.sales_baseline import run_sales_baseline
from src.services.workflow_recovery import cancel_workflow_run
from src.services.workflow_state import (
    InvalidTransitionError,
    initialize_run,
    transition,
    transition_step,
)
from src.services.workflow_transactions import StaleWorkflowError, workflow_transaction


@pytest.fixture
def database():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required for real PostgreSQL tests")
    engine = create_engine(url, connect_args={"options": "-c statement_timeout=10000"})
    # A unique schema owns all test data; never alter application tables.
    schema = "phase66_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(scoped)
    with Session(scoped) as db:
        db.add(Organization(id=DEFAULT_ORGANIZATION_ID, name="Legacy local organization"))
        db.commit()
    try:
        yield scoped
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def make_run(db, status=WorkflowStatus.created, workflow_type=WorkflowType.sales_report):
    source = UploadedInput(
        input_type=InputType(workflow_type.value), title="Lifecycle fixture", raw_text="Revenue 10"
    )
    db.add(source)
    db.flush()
    run = WorkflowRun(
        workflow_type=workflow_type, run_mode=RunMode.baseline,
        status=status, input_id=source.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def test_atomic_transition_rolls_back_event_timestamp_and_related_result(database, monkeypatch):
    emitted = []
    monkeypatch.setattr(
        "src.services.workflow_state.emit_workflow_summary_telemetry", emitted.append,
    )
    with Session(database) as db:
        run = make_run(db, WorkflowStatus.running)
        run_id = run.id
        with pytest.raises(RuntimeError, match="injected"):
            with workflow_transaction(db, run):
                run.final_output = "must disappear"
                transition(run, WorkflowStatus.completed, db)
                raise RuntimeError("injected persistence failure")
        db.expire_all()
        run = db.get(WorkflowRun, run_id)
        assert run.status == WorkflowStatus.running
        assert run.final_output is None and run.completed_at is None
        assert run.state_revision == 0
        assert db.scalars(select(WorkflowEvent)).all() == []
        assert emitted == []


def test_start_event_failure_rolls_back_the_new_run(database, monkeypatch):
    def fail_event(*args, **kwargs):
        raise RuntimeError("event storage failed")

    monkeypatch.setattr("src.services.workflow_state.log_workflow_event", fail_event)
    with Session(database) as db:
        run = WorkflowRun(workflow_type=WorkflowType.sales_report, run_mode=RunMode.baseline)
        with pytest.raises(RuntimeError, match="event storage failed"):
            initialize_run(db, run)
    with Session(database) as db:
        assert db.scalars(select(WorkflowRun)).all() == []
        assert db.scalars(select(WorkflowEvent)).all() == []


def test_start_persists_one_run_and_initial_event(database):
    with Session(database) as db:
        run = initialize_run(db, WorkflowRun(
            workflow_type=WorkflowType.sales_report, run_mode=RunMode.baseline,
        ))
        assert run.status == WorkflowStatus.created and run.state_revision == 1
        event = db.scalars(select(WorkflowEvent)).one()
        assert event.workflow_run_id == run.id
        assert event.event_type == WorkflowEventType.workflow_started


def test_revision_fences_stale_writes_even_when_status_is_unchanged(database):
    with Session(database) as first, Session(database) as second:
        run = make_run(first, WorkflowStatus.running)
        stale = second.get(WorkflowRun, run.id)
        with workflow_transaction(first, run):
            run.quality_score = 0.9
        with pytest.raises(StaleWorkflowError):
            with workflow_transaction(second, stale):
                stale.quality_score = 0.1
        second.expire_all()
        assert second.get(WorkflowRun, run.id).quality_score == 0.9


@pytest.mark.parametrize("terminal", [WorkflowStatus.completed, WorkflowStatus.failed,
                                     WorkflowStatus.cancelled])
def test_terminal_runs_cannot_reopen(database, terminal):
    with Session(database) as db:
        run = make_run(db, WorkflowStatus.running)
        transition(run, terminal, db)
        timestamp = run.completed_at
        with pytest.raises(InvalidTransitionError):
            transition(run, WorkflowStatus.running, db)
        assert run.status == terminal and run.completed_at == timestamp


@pytest.mark.parametrize("workflow_type", list(WorkflowType))
@pytest.mark.parametrize("fail", [False, True])
def test_provider_result_after_cancel_cannot_write_completion(database, workflow_type, fail):
    with Session(database) as db:
        run = make_run(db, workflow_type=workflow_type)
        run_id = run.id

        class Provider:
            def generate_text(self, **kwargs):
                # This independent connection also proves provider I/O holds no run lock.
                with Session(database) as other:
                    cancel_workflow_run(other, other.get(WorkflowRun, run_id))
                if fail:
                    raise RuntimeError("late provider failure")
                return TextResponse("late output", "fixture", LLMUsage(1, 1))

        with pytest.raises(StaleWorkflowError):
            run_sales_baseline(db, run, Provider())
        db.expire_all()
        assert db.get(WorkflowRun, run_id).status == WorkflowStatus.cancelled
        assert db.get(WorkflowRun, run_id).final_output is None
        step = db.scalars(select(AgentStep)).one()
        assert step.status == AgentStepStatus.failed and step.output_json is None
        assert db.scalars(select(CostEvent)).all() == []
        event_types = [e.event_type for e in db.scalars(select(WorkflowEvent))]
        assert WorkflowEventType.workflow_cancelled in event_types
        assert WorkflowEventType.agent_completed not in event_types
        assert WorkflowEventType.workflow_completed not in event_types


@pytest.mark.parametrize("workflow_type", list(WorkflowType))
def test_real_baseline_commits_output_cost_events_and_terminal_state(database, workflow_type):
    class Provider:
        def generate_text(self, **kwargs):
            return TextResponse("accepted output", "fixture", LLMUsage(1, 2))

    with Session(database) as db:
        run = make_run(db, workflow_type=workflow_type)
        step = run_sales_baseline(db, run, Provider())
        assert step.status == AgentStepStatus.completed
        assert run.status == WorkflowStatus.completed
        assert run.final_output == "accepted output" and run.total_tokens == 3
        assert run.state_revision == 2
        assert len(db.scalars(select(CostEvent)).all()) == 1


def test_competing_cancellation_and_completion_have_one_terminal_winner(database):
    with Session(database) as db:
        run_id = make_run(db, WorkflowStatus.running).id
    barrier = Barrier(2)

    def compete(target):
        with Session(database) as db:
            run = db.get(WorkflowRun, run_id)
            barrier.wait(timeout=5)
            try:
                transition(run, target, db)
                return "accepted"
            except StaleWorkflowError:
                return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(compete, [WorkflowStatus.completed, WorkflowStatus.cancelled]))
    assert sorted(outcomes) == ["accepted", "stale"]
    with Session(database) as db:
        assert db.get(WorkflowRun, run_id).state_revision == 1
        assert len(db.scalars(select(WorkflowEvent)).all()) == 1


def test_conflicting_approval_decision_cannot_overwrite_first_decision(database):
    with Session(database) as first, Session(database) as second:
        run = make_run(first, WorkflowStatus.waiting_for_human)
        approval = HumanApproval(workflow_run_id=run.id, status=ApprovalStatus.pending)
        first.add(approval)
        first.commit()
        approval_id = approval.id
        stale_run = second.get(WorkflowRun, run.id)
        stale_approval = second.get(HumanApproval, approval_id)
        approve_human_approval(first, approval)
        with pytest.raises(StaleWorkflowError):
            reject_human_approval(second, stale_approval)
        second.expire_all()
        assert stale_run.status == WorkflowStatus.writer_running
        assert stale_approval.status == ApprovalStatus.approved
        events = second.scalars(select(WorkflowEvent)).all()
        assert sum(e.event_type == WorkflowEventType.human_approved for e in events) == 1
        assert all(e.event_type != WorkflowEventType.human_rejected for e in events)


def test_step_terminal_transition_rejected():
    step = AgentStep(status=AgentStepStatus.failed)
    with pytest.raises(ValueError):
        transition_step(step, AgentStepStatus.completed)


def test_approval_refreshes_feedback_committed_before_run_lock(database):
    with Session(database) as first, Session(database) as second:
        run = make_run(first, WorkflowStatus.waiting_for_human)
        approval = HumanApproval(workflow_run_id=run.id, status=ApprovalStatus.pending)
        first.add(approval)
        first.commit()
        stale_approval = second.get(HumanApproval, approval.id)
        assert stale_approval.human_feedback is None
        edit_human_approval(first, approval, human_feedback="Keep this correction")
        # The deciding request had loaded the approval before the concurrent edit,
        # but has not loaded the run yet. Lock then refresh must preserve the edit.
        approve_human_approval(second, stale_approval)
        first.expire_all()
        assert approval.human_feedback == "Keep this correction"
        assert approval.status == ApprovalStatus.approved
