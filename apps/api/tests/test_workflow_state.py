from datetime import UTC

import pytest

from src.models.workflow_run import WorkflowRun, WorkflowStatus
from src.services.workflow_state import InvalidTransitionError, transition


class FakeSession:
    def commit(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass


def test_valid_transition_updates_status():
    run = WorkflowRun(status=WorkflowStatus.created)

    transition(run, WorkflowStatus.running, FakeSession())

    assert run.status == WorkflowStatus.running
    assert run.completed_at is None


def test_terminal_transition_sets_completed_at():
    run = WorkflowRun(status=WorkflowStatus.writer_running)

    transition(run, WorkflowStatus.completed, FakeSession())

    assert run.status == WorkflowStatus.completed
    assert run.completed_at is not None
    assert run.completed_at.tzinfo == UTC


def test_running_can_complete_for_baseline_workflow():
    run = WorkflowRun(status=WorkflowStatus.running)

    transition(run, WorkflowStatus.completed, FakeSession())

    assert run.status == WorkflowStatus.completed
    assert run.completed_at is not None


def test_invalid_transition_is_rejected():
    run = WorkflowRun(status=WorkflowStatus.created)

    with pytest.raises(InvalidTransitionError):
        transition(run, WorkflowStatus.completed, FakeSession())


@pytest.mark.parametrize(
    "terminal_status",
    [WorkflowStatus.completed, WorkflowStatus.failed, WorkflowStatus.cancelled],
)
def test_terminal_states_reject_followup_transitions(terminal_status):
    run = WorkflowRun(status=terminal_status)

    with pytest.raises(InvalidTransitionError):
        transition(run, WorkflowStatus.running, FakeSession())
