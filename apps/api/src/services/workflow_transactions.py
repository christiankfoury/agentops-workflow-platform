"""Short, run-serialized units of work. Never hold these across provider I/O."""

from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.workflow_run import WorkflowRun


class StaleWorkflowError(Exception):
    """Another transaction changed this run after the caller read it."""


def after_workflow_commit(db: Session, callback) -> None:
    """External telemetry follows a successful database commit, never a flush."""
    if isinstance(db, Session) and db.info.get("workflow_transaction"):
        db.info.setdefault("workflow_after_commit", []).append(callback)
    else:
        callback()


def commit_workflow(db: Session) -> None:
    """Helpers flush inside an owned transaction; only its owner commits."""
    if isinstance(db, Session) and db.info.get("workflow_transaction"):
        db.flush()
    else:
        db.commit()


@contextmanager
def workflow_transaction(db: Session, run: WorkflowRun, *, expected_revision=None):
    # Existing unit-test doubles exercise domain behavior without SQL semantics.
    if not isinstance(db, Session):
        yield
        return
    active = db.info.get("workflow_transaction")
    if active is not None:
        if active != run.id:
            raise ValueError("A workflow transaction may own only one run")
        yield
        return
    expected = run.state_revision if expected_revision is None else expected_revision
    expire_on_commit = db.expire_on_commit
    try:
        with db.no_autoflush:
            current = db.execute(
                select(WorkflowRun.state_revision, WorkflowRun.status)
                .where(WorkflowRun.id == run.id)
                .with_for_update()
            ).one_or_none()
        if current is None or current.state_revision != expected:
            raise StaleWorkflowError("Workflow changed; reload before retrying this operation")
        if current.status != run.status:
            raise StaleWorkflowError("Workflow status changed")
        db.info["workflow_transaction"] = run.id
        # Preserve the exact revision and provider inputs observed under the lock.
        # Lazy reload after commit could otherwise adopt a competing revision.
        db.expire_on_commit = False
        yield
        run.state_revision = expected + 1
        db.commit()
        callbacks = db.info.pop("workflow_after_commit", [])
        for callback in callbacks:
            callback()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.expire_on_commit = expire_on_commit
        db.info.pop("workflow_transaction", None)
        db.info.pop("workflow_after_commit", None)
