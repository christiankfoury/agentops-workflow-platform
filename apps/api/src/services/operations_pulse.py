"""Small permission-scoped change tokens; never return workflow payloads."""

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import func, select

from src.models.human_approval import HumanApproval
from src.models.workflow_execution import TERMINAL, WorkflowExecution
from src.models.workflow_run import WorkflowRun

KINDS = ("execution", "run", "approval", "executions", "runs", "approvals", "operations")


def pulse(db, kind, identity=None):
    terminal, waiting = False, False
    if kind in {"execution", "run"}:
        model = WorkflowExecution if kind == "execution" else WorkflowRun
        row = db.execute(
            select(model.status, model.state_revision).where(
                model.id == identity,
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(404, "Run unavailable")
        data = list(row)
        terminal, waiting = row.status in TERMINAL, row.status in {"waiting", "waiting_for_human"}
    elif kind == "approval":
        row = db.execute(
            select(
                HumanApproval.status,
                WorkflowRun.status.label("run_status"),
                WorkflowRun.state_revision,
            )
            .join(
                WorkflowRun,
                HumanApproval.workflow_run_id == WorkflowRun.id,
            )
            .where(HumanApproval.id == identity)
        ).one_or_none()
        if row is None:
            raise HTTPException(404, "Approval unavailable")
        data = list(row)
        terminal = row.status != "pending" or row.run_status in TERMINAL
        waiting = True
    elif kind in {"executions", "runs", "approvals"}:
        model = {"executions": WorkflowExecution, "runs": WorkflowRun, "approvals": HumanApproval}[
            kind
        ]
        revision = (
            func.max(model.resolved_at) if kind == "approvals" else func.sum(model.state_revision)
        )
        data = [
            list(row)
            for row in db.execute(
                select(
                    model.status,
                    func.count(),
                    func.max(model.created_at),
                    revision,
                )
                .group_by(model.status)
                .order_by(model.status)
            )
        ]
        waiting = True
    elif kind == "operations":
        # Ages and heartbeat expiry change even without a workflow transition.
        data = [int(db.scalar(select(func.extract("epoch", func.clock_timestamp())))) // 15]
        waiting = True
    else:
        raise HTTPException(422, "Unknown live view")
    return {
        "token": hashlib.sha256(json.dumps(data, default=str).encode()).hexdigest(),
        "terminal": terminal,
        "interval_ms": 15000 if waiting else 5000,
    }
