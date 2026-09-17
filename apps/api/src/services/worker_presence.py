"""Best-effort liveness telemetry, independent of job ownership/lease authority."""

import logging
from contextlib import contextmanager
from datetime import timedelta
from threading import Event, Thread

from sqlalchemy import delete, func, update
from sqlalchemy.dialects.postgresql import insert

from src.models.worker_presence import WorkerPresence

workers = WorkerPresence.__table__
log = logging.getLogger(__name__)


def beat(engine, identity, capacity, status="running"):
    with engine.begin() as conn:
        values = {
            "id": identity,
            "capacity": capacity,
            "status": status,
            "heartbeat_at": func.clock_timestamp(),
            "expires_at": func.clock_timestamp() + timedelta(seconds=40),
        }
        conn.execute(
            insert(workers)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[workers.c.id],
                set_={k: v for k, v in values.items() if k != "id"},
                where=workers.c.status != "stopped",
            )
        )
        # Only ephemeral presence is pruned. Job/attempt/event history is retained.
        conn.execute(
            delete(workers).where(
                workers.c.expires_at < func.clock_timestamp() - timedelta(days=1),
            )
        )


@contextmanager
def presence(engine, identity, capacity, worker_stop):
    done = Event()

    def refresh():
        try:
            beat(engine, identity, capacity, "draining" if worker_stop.is_set() else "running")
        except Exception:
            log.warning("Worker presence unavailable; durable job leases remain authoritative")

    def heartbeat():
        while not done.wait(10):
            refresh()

    refresh()
    thread = Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join(timeout=5)
        try:
            with engine.begin() as conn:
                conn.execute(
                    update(workers)
                    .where(workers.c.id == identity)
                    .values(
                        status="stopped",
                        expires_at=func.clock_timestamp(),
                    )
                )
        except Exception:
            log.warning("Worker stop presence unavailable; heartbeat will expire")
