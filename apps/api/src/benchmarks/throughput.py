"""Real queue execution with bounded producer batches and explicit fixture approvals."""

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, process_time
from uuid import UUID

from sqlalchemy import select

from src.benchmarks.evidence import archive, latencies, peak_rss_bytes, reconcile, snapshot
from src.benchmarks.fixtures import Sink, fixture_settings, prepare, run_input, session, workload
from src.models.execution_approval import ExecutionApproval
from src.models.workflow_execution import TERMINAL, WorkflowExecution
from src.schemas.execution_approval import ApprovalDecision
from src.schemas.execution_start import ExecutionStartRequest
from src.services.approval_runtime import decide_approval
from src.services.execution_starts import start_execution
from src.worker import run_worker


def approve_pending(engine, principal):
    with session(engine, principal) as db:
        pending = db.execute(
            select(ExecutionApproval.id, ExecutionApproval.payload_hash)
            .where(
                ExecutionApproval.status == "pending",
            )
            .order_by(ExecutionApproval.created_at, ExecutionApproval.id)
            .limit(100)
        ).all()
    for identity, payload_hash in pending:
        with session(engine, principal) as db:
            decide_approval(
                db,
                identity,
                ApprovalDecision(
                    action="approve",
                    expected_payload_hash=payload_hash,
                    human_feedback="Synthetic loopback benchmark fixture; no real external action.",
                ),
            )


def execute_stage(
    engine, output, *, count, capacity, seed, offset=0, batch_size=100, timeout=14400
):
    accepted, duplicates, errors = [], 0, []
    stop, sink = Event(), Sink()
    with fixture_settings(sink):
        principal, definitions, tool_id = prepare(engine)
        items = workload(count, seed, offset)
        started, cpu_started = monotonic(), process_time()
        with ThreadPoolExecutor(max_workers=1) as pool:
            worker = pool.submit(
                run_worker, engine, capacity=capacity, poll_seconds=0.02, stop=stop
            )
            try:
                for begin in range(0, count, batch_size):
                    batch = []
                    for item in items[begin : begin + batch_size]:
                        body = ExecutionStartRequest(
                            **definitions[item["kind"]],
                            input=run_input(item, tool_id),
                            idempotency_key=f"benchmark-{seed}-{item['index']}",
                        )
                        with session(engine, principal) as db:
                            identity = start_execution(db, body).id
                        accepted.append(
                            {
                                **item,
                                "id": str(identity),
                                "version_id": str(body.version_id),
                                "start_key": body.idempotency_key,
                                "input_bytes": len(json.dumps(body.input).encode()),
                            }
                        )
                        batch.append(identity)
                        if item["index"] % 10 == 0:
                            with session(engine, principal) as db:
                                if start_execution(db, body).id != identity:
                                    raise RuntimeError("Duplicate start created another identity")
                            duplicates += 1
                    while True:
                        if worker.done():
                            worker.result()
                            raise RuntimeError("Worker stopped before drain")
                        if monotonic() - started > timeout:
                            raise TimeoutError("Benchmark stage deadline exceeded")
                        approve_pending(engine, principal)
                        with session(engine, principal) as db:
                            states = db.execute(
                                select(
                                    WorkflowExecution.id,
                                    WorkflowExecution.status,
                                ).where(WorkflowExecution.id.in_(batch))
                            ).all()
                        if len(states) == len(batch) and all(
                            status in TERMINAL for _, status in states
                        ):
                            break
                        stop.wait(0.1)
                    print(
                        json.dumps(
                            {
                                "capacity": capacity,
                                "accepted": len(accepted),
                                "target": count,
                                "seconds": round(monotonic() - started, 2),
                            }
                        ),
                        flush=True,
                    )
            except Exception as error:
                errors.append(type(error).__name__)
            finally:
                stop.set()
            try:
                worker_failures = worker.result()
            except Exception as error:
                errors.append(type(error).__name__)
                worker_failures = 1
        elapsed, cpu = monotonic() - started, process_time() - cpu_started
        memory = peak_rss_bytes()
        data = snapshot(engine)
        with sink.lock:
            sink_effects, sink_calls, conflicts = (
                dict(sink.effects),
                list(sink.calls),
                sink.conflicts,
            )
    checked = reconcile(accepted, data, sink_effects, conflicts)
    if errors or worker_failures or len(accepted) != count:
        checked["passed"] = False
    prefix = f"capacity-{capacity}"
    files = [
        archive(output / f"{prefix}-{name}.jsonl.gz", rows)
        for name, rows in {
            "accepted": accepted,
            **{
                key: data[key] for key in ("starts", "runs", "jobs", "steps", "attempts", "effects")
            },
            "sink-calls": sink_calls,
            "sink-effects": [
                {"key": key, "body": body} for key, body in sorted(sink_effects.items())
            ],
            "claim-waits": [{"seconds": value} for value in data["claim_waits"]],
        }.items()
    ]
    return {
        "capacity": capacity,
        "requested": count,
        "seed": seed,
        "offset": offset,
        "batch_size": batch_size,
        "poll_seconds": 0.02,
        "timeout_seconds": timeout,
        "duration_seconds": elapsed,
        "cpu_seconds": cpu,
        "process_lifetime_peak_rss_bytes": memory,
        "schema_bytes_after_drain": data["schema_bytes"],
        "postgresql": data["postgresql"],
        "expected_failures": 0,
        "completed_per_second": checked["statuses"].get("completed", 0) / elapsed,
        "duplicate_start_requests": duplicates,
        "duplicate_starts_prevented": duplicates,
        "start_requests": len(accepted) + duplicates,
        "worker_exceptions": worker_failures,
        "controller_errors": errors,
        "reconciliation": checked,
        "latencies": latencies(data),
        "workload_counts": dict(Counter(row["kind"] for row in accepted)),
        "max_input_bytes": max((row["input_bytes"] for row in accepted), default=0),
        "step_retries": sum(row["number"] > 1 for row in data["attempts"]),
        "lease_recoveries": sum(row["recovery_count"] for row in data["jobs"]),
        "tool_retries": sum(max(0, row["attempts"] - 1) for row in data["effects"]),
        "sink_requests": len(sink_calls),
        "sink_duplicate_requests": len(sink_calls) - len(sink_effects),
        "files": files,
        "accepted_id_count": len({UUID(row["id"]) for row in accepted}),
    }
