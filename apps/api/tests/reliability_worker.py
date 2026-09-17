"""Disposable subprocess fixture; stdin requests the same stop event used by SIGTERM."""

import sys
from pathlib import Path
from threading import Event, Thread
from time import sleep

from src.database import engine
from src.services import durable_queue as queue
from src.services.execution_registry import ExecutorRegistry
from src.worker import run_worker


def main():
    boundary, root = sys.argv[1], Path(sys.argv[2])
    ready, release = root / "ready", root / "release"
    registry = ExecutorRegistry()

    def held(value):
        ready.write_text("ready")
        while not release.exists():
            sleep(0.02)
        return value

    if boundary in {"rolling", "replacement"}:
        stop = Event()

        def request_stop():
            sys.stdin.readline()
            stop.set()
            (root / "stop-requested").write_text("draining")

        Thread(target=request_stop, daemon=True).start()
        # The worker invokes the ordinary queue function with this deterministic registry.
        import src.worker as worker

        if boundary == "rolling":
            registry.handlers[("builtin.identity", 1)] = held
            worker.process_claim = lambda db, claim: queue.process_claim(db, claim, registry)
        else:
            ready.write_text("ready")
        return run_worker(engine, poll_seconds=0.02, stop=stop)
    claim = queue.claim_jobs(engine, "fault-boundary")[0]
    if boundary == "during":
        registry.handlers[("builtin.identity", 1)] = held
        queue.process_claim(engine, claim, registry)
    elif boundary == "after":
        queue.process_claim(engine, claim)
    ready.write_text("ready")
    while True:
        sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
