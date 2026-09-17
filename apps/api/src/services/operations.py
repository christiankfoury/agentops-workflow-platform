"""Payload-free persisted operations. HTTP callers must supply a verified tenant."""

from datetime import timedelta

from sqlalchemy import Float, and_, cast, exists, func, or_, select

from src.models.durable_job import DurableJob
from src.models.execution_recovery import ExecutionRecovery
from src.models.workflow_execution import ExecutionEvent, StepAttempt, StepRun, WorkflowExecution
from src.services.worker_presence import workers

jobs, runs, steps, attempts, events, recoveries = (
    model.__table__
    for model in (
        DurableJob,
        WorkflowExecution,
        StepRun,
        StepAttempt,
        ExecutionEvent,
        ExecutionRecovery,
    )
)
DEAD = ("retry_exhausted", "recovery_exhausted")
FILTERS = (
    "all",
    "queued",
    "running",
    "failed",
    "completed",
    "cancelled",
    "retrying",
    "dead_letter",
    "stale",
)


def scope(table, organization_id):
    # None is reserved for the infrastructure CLI. It is never accepted by HTTP.
    return table.c.organization_id == organization_id if organization_id is not None else True


def job_filter(kind, now):
    if kind == "all":
        return True
    if kind == "stale":
        return and_(jobs.c.status == "running", jobs.c.lease_expires_at <= now)
    if kind == "dead_letter":
        return and_(jobs.c.status == "failed", jobs.c.error_code.in_(DEAD))
    if kind == "retrying":
        return and_(
            jobs.c.status == "queued",
            or_(
                jobs.c.recovery_count > 0,
                exists(
                    select(steps.c.id).where(
                        steps.c.organization_id == jobs.c.organization_id,
                        steps.c.execution_id == jobs.c.execution_id,
                        steps.c.status == "retrying",
                        or_(
                            jobs.c.node_id.is_(None),
                            and_(
                                steps.c.node_id == jobs.c.node_id,
                                steps.c.iteration == jobs.c.iteration,
                            ),
                        ),
                    ),
                ),
            ),
        )
    if kind not in FILTERS:
        raise ValueError("Unknown operations filter")
    return jobs.c.status == kind


def snapshot(conn, organization_id):
    now = conn.scalar(select(func.current_timestamp()))

    def count(table, *conditions):
        return conn.scalar(
            select(func.count())
            .select_from(table)
            .where(
                scope(table, organization_id),
                *conditions,
            )
        )

    def statuses(table):
        return dict(
            conn.execute(
                select(table.c.status, func.count())
                .where(
                    scope(table, organization_id),
                )
                .group_by(table.c.status)
            ).all()
        )

    job_counts = statuses(jobs)
    for key in ("retrying", "dead_letter", "stale"):
        job_counts[key] = count(jobs, job_filter(key, now))
    claim_where = (
        scope(events, organization_id),
        events.c.entity_type == "durable_jobs",
        events.c.from_status == "queued",
        events.c.to_status == "running",
    )
    wait = cast(events.c.details["queue_wait_seconds"].astext, Float)
    queue_wait = conn.execute(
        select(
            func.count(wait), func.coalesce(func.sum(wait), 0), func.coalesce(func.max(wait), 0)
        ).where(*claim_where)
    ).one()
    oldest = conn.scalar(
        select(func.min(jobs.c.due_at)).where(
            scope(jobs, organization_id),
            jobs.c.status == "queued",
            jobs.c.due_at <= now,
        )
    )
    observed_workers = (
        True
        if organization_id is None
        else exists(
            select(jobs.c.id).where(
                jobs.c.organization_id == organization_id,
                jobs.c.worker_id == workers.c.id,
            )
        )
    )
    worker_counts = dict(
        conn.execute(
            select(workers.c.status, func.count())
            .where(
                observed_workers,
                workers.c.expires_at > now,
            )
            .group_by(workers.c.status)
        ).all()
    )
    return {
        "observed_at": now.isoformat(),
        "window_seconds": 900,
        "jobs": job_counts,
        "runs": statuses(runs),
        "attempts": statuses(attempts),
        "waiting_steps": count(steps, steps.c.status == "waiting"),
        "claims": count(events, *claim_where[1:]),
        "lease_recoveries": count(
            events,
            events.c.entity_type == "durable_jobs",
            events.c.details["reason"].astext == "lease_expired",
        ),
        "abandoned_attempts": count(attempts, attempts.c.error_code == "worker_abandoned"),
        "linked_recoveries": count(recoveries),
        "queue_wait": {
            "samples": queue_wait[0],
            "sum_seconds": queue_wait[1],
            "max_seconds": queue_wait[2],
        },
        "oldest_ready_seconds": max(0, (now - oldest).total_seconds()) if oldest else 0,
        "completed_in_window": count(
            runs, runs.c.status == "completed", runs.c.completed_at >= now - timedelta(seconds=900)
        ),
        "workers": worker_counts,
        "worker_scope": "fleet" if organization_id is None else "associated_with_tenant_jobs",
    }


def job_page(conn, organization_id, kind="all", offset=0, limit=25):
    if organization_id is None:
        raise ValueError("Job history requires a tenant")
    now = conn.scalar(select(func.current_timestamp()))
    columns = (
        "id",
        "execution_id",
        "status",
        "node_id",
        "iteration",
        "created_at",
        "due_at",
        "claimed_at",
        "completed_at",
        "lease_expires_at",
        "heartbeat_at",
        "recovery_count",
    )
    rows = conn.execute(
        select(*(jobs.c[key] for key in columns))
        .where(
            scope(jobs, organization_id),
            job_filter(kind, now),
        )
        .order_by(jobs.c.created_at.desc(), jobs.c.id.desc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = rows.mappings()
    rows = [dict(row) for row in rows]
    return {
        "items": rows[:limit],
        "offset": offset,
        "next_offset": offset + limit if len(rows) > limit else None,
    }


def prometheus(data):
    """Fixed metric names/status allowlists; no resource, tenant or hostname labels."""
    lines = []

    def emit(name, value, label=""):
        lines.append(f"agentops_{name}{label} {float(value):.9g}")

    for group in ("jobs", "runs", "attempts", "workers"):
        for state in (
            "pending",
            "queued",
            "running",
            "waiting",
            "retrying",
            "completed",
            "failed",
            "cancelled",
            "dead_letter",
            "stale",
            "draining",
        ):
            if state in data[group]:
                emit(group, data[group][state], f'{{status="{state}"}}')
    for key in (
        "waiting_steps",
        "claims",
        "lease_recoveries",
        "abandoned_attempts",
        "linked_recoveries",
        "oldest_ready_seconds",
        "completed_in_window",
    ):
        emit(key, data[key])
    for key, value in data["queue_wait"].items():
        emit(f"queue_wait_{key}", value)
    emit("throughput_per_second", data["completed_in_window"] / data["window_seconds"])
    return "\n".join(lines) + "\n"
