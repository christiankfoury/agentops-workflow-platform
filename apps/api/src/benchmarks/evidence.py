"""Portable evidence, resource observations and strict end-state reconciliation."""

import ctypes
import gzip
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select, text

from src.models.durable_job import DurableJob
from src.models.execution_start import ExecutionStart
from src.models.tool import ToolExecution
from src.models.workflow_execution import ExecutionEvent, StepAttempt, StepRun, WorkflowExecution

API = Path(__file__).resolve().parents[2]
ROOT = API.parents[1]


def json_text(value):
    return json.dumps(value, default=str, sort_keys=True, ensure_ascii=False, allow_nan=False)


def save(path, value):
    Path(path).write_text(json_text(value) + "\n", encoding="utf-8")


def archive(path, records):
    data = "".join(json_text(row) + "\n" for row in records).encode()
    encoded = gzip.compress(data, mtime=0)
    Path(path).write_bytes(encoded)
    return {
        "file": Path(path).name,
        "records": len(records),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "uncompressed_bytes": len(data),
    }


def environment():
    sources = sorted(
        [
            *API.joinpath("src").rglob("*.py"),
            *API.joinpath("alembic").rglob("*.py"),
            API / "uv.lock",
        ]
    )
    return {
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip(),
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
                path.read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
            for path in sources
        },
        "platform": platform.platform(),
        "python": sys.version,
        "logical_cpus": os.cpu_count(),
        "measurement_scope": "One Python process: producer, worker threads, approver and sink; "
        "external PostgreSQL. No HTTP/OIDC ingress or human decision latency.",
    }


def peak_rss_bytes():
    if os.name == "nt":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "peak",
                    "working",
                    "peak_pool",
                    "pool",
                    "peak_nonpaged",
                    "nonpaged",
                    "pagefile",
                    "peak_pagefile",
                )
            ]

        counter = Counters()
        counter.cb = ctypes.sizeof(counter)
        current = ctypes.windll.kernel32.GetCurrentProcess
        current.restype = wintypes.HANDLE
        query = ctypes.windll.psapi.GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not query(current(), ctypes.byref(counter), counter.cb):
            raise OSError("Process memory observation failed")
        return counter.peak
    import resource

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss if sys.platform == "darwin" else rss * 1024


def percentiles(values):
    ordered = sorted(values)
    return {
        "samples": len(ordered),
        **{
            key: round(ordered[max(0, math.ceil(len(ordered) * rank) - 1)], 6) if ordered else None
            for key, rank in [("p50", 0.5), ("p95", 0.95), ("p99", 0.99), ("max", 1)]
        },
    }


def snapshot(engine):
    # Dedicated owned schema only. Core reads include every row, allowing orphan detection.
    selections = {
        "starts": (ExecutionStart, ["id", "key", "execution_id"]),
        "runs": (
            WorkflowExecution,
            [
                "id",
                "status",
                "version_id",
                "input_json",
                "output_json",
                "created_at",
                "started_at",
                "completed_at",
                "error_code",
            ],
        ),
        "jobs": (
            DurableJob,
            [
                "id",
                "execution_id",
                "status",
                "created_at",
                "claimed_at",
                "completed_at",
                "recovery_count",
                "error_code",
            ],
        ),
        "steps": (StepRun, ["id", "execution_id", "node_id", "status", "output_json"]),
        "attempts": (StepAttempt, ["id", "step_run_id", "number", "status", "error_code"]),
        "effects": (
            ToolExecution,
            ["effect_key", "step_run_id", "request_json", "status", "attempts", "result_json"],
        ),
    }
    result = {}
    with engine.connect() as conn:
        for name, (model, columns) in selections.items():
            table = model.__table__
            result[name] = [
                dict(row)
                for row in conn.execute(
                    select(*(table.c[column] for column in columns)).order_by(table.c[columns[0]]),
                ).mappings()
            ]
        events = ExecutionEvent.__table__
        result["claim_waits"] = list(
            conn.scalars(
                select(
                    events.c.details["queue_wait_seconds"].as_float(),
                ).where(events.c.entity_type == "durable_jobs", events.c.to_status == "running")
            )
        )
        result["postgresql"] = conn.scalar(text("select version()"))
        result["schema_bytes"] = conn.scalar(
            text(
                "select coalesce(sum(pg_total_relation_size(c.oid)), 0) from pg_class c "
                "join pg_namespace n on n.oid=c.relnamespace "
                "where n.nspname=current_schema() and c.relkind='r'",
            )
        )
    result["schema_bytes"] = int(result["schema_bytes"])
    return result


def reconcile(accepted, data, sink_effects, conflicts=0):
    runs = {str(row["id"]): row for row in data["runs"]}
    expected = {row["id"]: row for row in accepted}
    steps = {row["id"]: row for row in data["steps"]}
    steps_by_run = defaultdict(dict)
    for step in data["steps"]:
        steps_by_run[str(step["execution_id"])][step["node_id"]] = step
    intended = {row["id"]: {"value": row["value"]} for row in accepted if row["kind"] == "sink"}
    effects = {row["effect_key"]: row for row in data["effects"]}
    observed_runs = Counter()
    errors = []
    if (
        set(runs) != set(expected)
        or len(expected) != len(accepted)
        or len(runs) != len(data["runs"])
    ):
        errors.append("accepted_run_identity_mismatch")
    receipts = {row["key"]: str(row["execution_id"]) for row in data["starts"]}
    if receipts != {row["start_key"]: row["id"] for row in accepted} or len(receipts) != len(
        data["starts"]
    ):
        errors.append("start_receipt_mismatch")
    if any(row["status"] != "completed" for row in runs.values()):
        errors.append("noncompleted_runs")
    jobs_by_run = Counter(str(row["execution_id"]) for row in data["jobs"])
    expected_jobs = {
        key: {"condition": 3, "parallel": 4, "sink": 3}[row["kind"]]
        for key, row in expected.items()
    }
    if (
        jobs_by_run != Counter(expected_jobs)
        or any(row["status"] != "completed" for row in data["jobs"])
        or len({row["id"] for row in data["jobs"]}) != len(data["jobs"])
    ):
        errors.append("missing_or_unsettled_jobs")
    attempts_by_step = Counter(row["step_run_id"] for row in data["attempts"])
    if (
        attempts_by_step
        != Counter({step["id"]: 1 for step in steps.values() if step["status"] == "completed"})
        or any(row["status"] != "completed" for row in data["attempts"])
        or set(steps_by_run) != set(expected)
        or len(steps) != len(data["steps"])
    ):
        errors.append("attempt_or_step_mismatch")
    if len(effects) != len(data["effects"]) or set(effects) != set(sink_effects):
        errors.append("sink_ledger_identity_mismatch")
    for key, effect in effects.items():
        step = steps.get(effect["step_run_id"])
        owner = str(step["execution_id"]) if step else "missing"
        observed_runs[owner] += 1
        if (
            effect["status"] not in {"succeeded", "reconciled"}
            or effect["request_json"] != intended.get(owner)
            or sink_effects.get(key) != intended.get(owner)
            or effect["result_json"] != {"status": 200, "body": intended.get(owner)}
        ):
            errors.append("incorrect_or_unknown_effect")
    if observed_runs != Counter({identity: 1 for identity in intended}) or conflicts:
        errors.append("missing_or_duplicate_intended_effects")
    for identity, item in expected.items():
        own = steps_by_run.get(identity, {})
        run = runs.get(identity, {})
        expected_input = (
            {"value": item["value"]}
            if item["kind"] != "sink"
            else run.get("input_json", {}).get("payload", {}).get("arguments")
        )
        if (
            str(run.get("version_id")) != item["version_id"]
            or expected_input != {"value": item["value"]}
            or (item["kind"] != "sink" and run.get("input_json") != expected_input)
        ):
            errors.append("pinned_input_or_version_mismatch")
        if item["kind"] == "parallel" and runs.get(identity, {}).get("output_json") != {
            "left": item["value"],
            "right": item["value"],
        }:
            errors.append("parallel_output_mismatch")
        if item["kind"] == "condition":
            chosen = "positive" if item["value"] >= 0 else "negative"
            other = "negative" if chosen == "positive" else "positive"
            if (
                own.get(chosen, {}).get("output_json") != {"value": item["value"]}
                or own.get(other, {}).get("status") != "skipped"
            ):
                errors.append("condition_output_mismatch")
    return {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "accepted": len(accepted),
        "statuses": dict(Counter(r["status"] for r in runs.values())),
        "job_statuses": dict(Counter(r["status"] for r in data["jobs"])),
        "intended_effects": len(intended),
        "observed_effects": len(sink_effects),
        "effect_statuses": dict(Counter(r["status"] for r in effects.values())),
    }


def latencies(data):
    def interval(start, end):
        return percentiles(
            [
                (row[end] - row[start]).total_seconds()
                for row in data["runs"]
                if row[end] is not None and row[start] is not None
            ]
        )

    return {
        "seconds_nearest_rank": {
            "run_queue": interval("created_at", "started_at"),
            "execution": interval("started_at", "completed_at"),
            "end_to_end": interval("created_at", "completed_at"),
            "job_queue": percentiles([value for value in data["claim_waits"] if value is not None]),
        }
    }
