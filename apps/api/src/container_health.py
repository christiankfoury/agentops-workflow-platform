"""Readiness for this container's worker, never another replica's heartbeat."""

from pathlib import Path

from sqlalchemy import func, select

from src.database import engine
from src.models.worker_presence import WorkerPresence


def ready(identity_file=Path("/tmp/worker-identity")):
    identity = identity_file.read_text(encoding="utf-8").strip()
    with engine.connect() as conn:
        return (
            conn.scalar(
                select(WorkerPresence.id)
                .where(
                    WorkerPresence.id == identity,
                    WorkerPresence.status == "running",
                    WorkerPresence.expires_at > func.clock_timestamp(),
                )
                .limit(1)
            )
            is not None
        )


if __name__ == "__main__":
    try:
        raise SystemExit(0 if ready() else 1)
    except Exception:
        raise SystemExit(1) from None
