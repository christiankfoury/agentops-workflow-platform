"""Prove SIGTERM drains an actually claimed checkpoint in the owned local stack."""

import argparse
import hashlib
import json
import subprocess
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from queue import Queue
from threading import Thread

from verify import (
    COMPOSE,
    ROOT,
    command,
    completed,
    compose,
    graph,
    login,
    publish,
    request,
    start,
    wait,
)

LOCK = """
from sqlalchemy import text
from src.database import engine
with engine.begin() as conn:
    conn.execute(text("SET LOCAL idle_in_transaction_session_timeout='45s'"))
    conn.execute(text("SET LOCAL lock_timeout='5s'"))
    conn.execute(text('LOCK TABLE step_attempts IN SHARE MODE'))
    print('held', flush=True)
    input()
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".local/production/active-drain.json")
    output = ROOT / parser.parse_args().output
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RuntimeError("Refusing to overwrite drain evidence")
    evidence = {"started_at": datetime.now(UTC).isoformat(), "passed": False}
    evidence["script_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    locker = stop = None
    try:
        with closing(login()) as client:
            definition = publish(client, graph(False))
            worker = compose("ps", "-q", "worker").strip()
            wait(
                lambda: (
                    json.loads(command("docker", "inspect", worker))[0]["State"]["Health"]["Status"]
                    == "healthy"
                )
            )
            locker = subprocess.Popen(
                [*COMPOSE, "run", "--rm", "--no-deps", "-T", "migrate", "python", "-u", "-c", LOCK],
                cwd=ROOT,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Server-side expiry releases the lock even if this client fails.
            messages = Queue()
            Thread(
                target=lambda: messages.put(locker.stdout.readline().strip()), daemon=True
            ).start()
            assert messages.get(timeout=30) == "held"
            identity = start(client, definition, {"value": 99})
            evidence["accepted_id"] = identity
            claimed = wait(
                lambda: [
                    j
                    for j in request(client, "GET", f"/workflow-executions/{identity}/jobs")
                    if j["status"] == "running"
                ],
                seconds=10,
            )
            evidence["claimed_before_signal"] = claimed
            stop = subprocess.Popen(
                [*COMPOSE, "stop", "worker"],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            wait(
                lambda: request(client, "GET", "/operations")["workers"].get("draining", 0) > 0,
                seconds=20,
            )
            evidence["draining_heartbeat_observed"] = True
            assert stop.poll() is None, "Worker exited before releasing the active checkpoint"
            assert json.loads(command("docker", "inspect", worker))[0]["State"]["Running"]
            locker.communicate("release\n", timeout=15)
            assert locker.returncode == 0
            stop.communicate(timeout=65)
            assert stop.returncode == 0
            state = json.loads(command("docker", "inspect", worker))[0]["State"]
            evidence["stopped_state"] = state
            assert state["ExitCode"] == 0 and not state["Running"] and not state["OOMKilled"]
            jobs = request(client, "GET", f"/workflow-executions/{identity}/jobs")
            original = next(j for j in jobs if j["id"] == claimed[0]["id"])
            assert original["status"] == "completed" and original["recovery_count"] == 0
            evidence["jobs_after_drain"] = jobs
            compose("start", "worker")
            evidence["run"] = wait(lambda: completed(client, identity))
            assert evidence["run"]["output_json"] == {"value": 99}
            evidence["jobs"] = request(client, "GET", f"/workflow-executions/{identity}/jobs")
            assert all(j["status"] == "completed" for j in evidence["jobs"])
            evidence["passed"] = True
    finally:
        if locker and locker.poll() is None:
            locker.communicate("release\n", timeout=25)
        if stop and stop.poll() is None:
            stop.communicate(timeout=65)
        compose("start", "worker")
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("Active checkpoint drained under SIGTERM; original job completed without recovery")


if __name__ == "__main__":
    main()
