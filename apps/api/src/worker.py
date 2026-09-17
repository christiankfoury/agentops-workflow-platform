"""Run with `uv run python -m src.worker`; signals stop claims and drain active work."""

import argparse
import logging
import os
import signal
import socket
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

from src.config import settings
from src.database import engine
from src.production import validate_configuration
from src.services.approval_runtime import expire_approval_waits
from src.services.delay_runtime import wake_due_delays
from src.services.durable_queue import claim_jobs, has_queued_jobs, process_claim
from src.services.execution_deadlines import enforce_deadlines
from src.services.worker_leases import recover_expired
from src.services.worker_presence import presence
from src.services.workflow_transactions import StaleWorkflowError

log = logging.getLogger(__name__)


def run_worker(database, *, capacity=1, poll_seconds=1, stop=None, max_jobs=None, drain=False):
    if type(capacity) is not int or not 1 <= capacity <= 32 or poll_seconds <= 0:
        raise ValueError("Worker capacity/poll interval are invalid")
    if max_jobs is not None and max_jobs < 1:
        raise ValueError("max_jobs must be positive")
    stop = stop or Event()
    identity = os.environ.get("WORKER_INSTANCE_ID") or f"{socket.gethostname()[:64]}:{uuid4().hex}"
    dispatched = 0
    failures = 0
    active = set()
    with (
        presence(database, identity, capacity, stop),
        ThreadPoolExecutor(max_workers=capacity) as pool,
    ):
        while True:
            for future in list(active):
                if future.done():
                    active.remove(future)
                    try:
                        future.result()
                    except StaleWorkflowError:
                        log.info("Checkpoint ownership changed; late result discarded")
                    except Exception as error:
                        failures += 1
                        log.error("Worker checkpoint interrupted: %s", type(error).__name__)
            enforce_deadlines(database)
            wake_due_delays(database)
            expire_approval_waits(database)
            if stop.is_set() or (max_jobs is not None and dispatched >= max_jobs):
                if not active:
                    break
                stop.wait(poll_seconds) if not stop.is_set() else Event().wait(poll_seconds)
                continue
            from src.services.durable_evaluations import advance_approvals

            advance_approvals(database)
            from src.services.schedules import fire_due_schedules

            fire_due_schedules(database)
            available = capacity - len(active)
            recover_expired(database)
            from src.services.tool_effects import recover_effects

            recover_effects(database)
            if max_jobs is not None:
                available = min(available, max_jobs - dispatched)
            claimed = claim_jobs(database, identity, available) if available else []
            for claim in claimed:
                active.add(pool.submit(process_claim, database, claim))
            dispatched += len(claimed)
            if drain and not active and not claimed and not has_queued_jobs(database):
                break
            stop.wait(poll_seconds)
    return failures


def main():
    validate_configuration()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-jobs", type=int)
    parser.add_argument("--drain", action="store_true", help="Exit when the queue is empty")
    args = parser.parse_args()
    stop = Event()
    for name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(name, lambda *_: stop.set())
    logging.basicConfig(level=logging.INFO)
    return (
        1
        if run_worker(
            engine,
            capacity=settings.worker_concurrency,
            poll_seconds=settings.worker_poll_seconds,
            stop=stop,
            max_jobs=args.max_jobs,
            drain=args.drain,
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
