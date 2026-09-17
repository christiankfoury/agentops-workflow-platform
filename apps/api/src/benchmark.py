"""Opt-in deterministic throughput benchmark. Creates and retains NEW isolated schemas."""

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from src.benchmarks.evidence import API, environment, save
from src.benchmarks.throughput import execute_stage


def database(url, capacity):
    schema = "benchmark98_" + uuid4().hex
    admin = create_engine(url)
    try:
        with admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    finally:
        admin.dispose()
    engine = create_engine(
        url,
        pool_size=capacity * 2 + 6,
        max_overflow=0,
        pool_timeout=30,
        pool_pre_ping=True,
        connect_args={"options": f"-c search_path={schema} -c statement_timeout=30000"},
    )
    config = Config(str(API / "alembic.ini"))
    config.set_main_option("script_location", str(API / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
    return engine, schema


def report_text(result):
    lines = [
        "# Deterministic throughput benchmark",
        "",
        f"Started: {result['started_at']}. Base commit: `{result['environment']['base_commit']}`.",
        "Exact measured Python/migration/lock sources are fingerprinted in `summary.json`.",
        "",
        "| Capacity | Accepted | Completed | Failed | Seconds | Completed/s | Reconciled |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for stage in result["stages"]:
        check = stage["reconciliation"]
        lines.append(
            f"| {stage['capacity']} | {check['accepted']} | "
            f"{check['statuses'].get('completed', 0)} | {check['statuses'].get('failed', 0)} | "
            f"{stage['duration_seconds']:.2f} | {stage['completed_per_second']:.3f} | "
            f"{check['passed']} |"
        )
    lines.extend(
        [
            "",
            "## Scope and limits",
            "",
            "Fixed-seed condition, parallel-join and approved loopback HTTP workflows. "
            "Fresh migrated schema per stage; bounded batches, one producer and one real "
            "worker process with the listed thread capacity. No paid models or remote effects.",
            "",
            "Service-level membership/permission checks and durable approval decisions "
            "are exercised. HTTP/OIDC ingress and human response time are excluded. "
            "Throughput includes acceptance, duplicate requests, fixture approvals and drain; "
            "migration/setup and evidence serialization are excluded. These are local "
            "observations, not production targets or 10,000 simultaneous calls.",
            "",
            "Latency percentiles use nearest rank. Execution latency includes waits after "
            "first start; end-to-end also includes initial queue time. Job queue samples come "
            "from persisted claim events. RSS is the Python process lifetime high-water mark; "
            "CPU includes its controller, workers and sink, not PostgreSQL. Database relation "
            "bytes include indexes. Shared-host/cache effects and stage order remain limits.",
            "",
            "All expected failures are zero; unsuccessful or incomplete runs remain in raw "
            "evidence and fail reconciliation. Gzipped JSONL archives retain accepted IDs, "
            "runs, jobs, steps, attempts, effects, sink observations and queue samples; each "
            "archive hash/count is in the summary. No arbitrary third-party exactly-once "
            "guarantee is implied.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--capacities", type=int, nargs="+", default=[1, 4, 16])
    parser.add_argument("--seed", type=int, default=20260916)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=14400)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if (
        args.capacities != sorted(set(args.capacities))
        or not all(1 <= value <= 32 for value in args.capacities)
        or not 3 * len(args.capacities) <= args.count <= 100000
        or not 1 <= args.batch_size <= 1000
        or not 0 < args.timeout <= 86400
    ):
        parser.error(
            "Use increasing capacities 1–32, count 3 per stage–100000, "
            "batch 1–1000 and timeout 0–86400 seconds"
        )
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        parser.error(
            "WORKFLOW_TEST_DATABASE_URL must name an authorized disposable PostgreSQL database"
        )
    args.output.mkdir(parents=True, exist_ok=False)
    result = {
        "started_at": datetime.now(UTC).isoformat(),
        "environment": environment(),
        "requested": args.count,
        "stages": [],
        "passed": False,
    }
    offset = 0
    try:
        for index, capacity in enumerate(args.capacities):
            count = args.count // len(args.capacities) + (index < args.count % len(args.capacities))
            engine, schema = database(url, capacity)
            print(
                f"Owned retained schema: {schema}; capacity {capacity}; target {count}", flush=True
            )
            try:
                stage = execute_stage(
                    engine,
                    args.output,
                    count=count,
                    capacity=capacity,
                    seed=args.seed + index,
                    offset=offset,
                    batch_size=args.batch_size,
                    timeout=args.timeout,
                )
                stage["schema"] = schema
                result["stages"].append(stage)
                save(args.output / "summary.json", result)
                offset += count
                if not stage["reconciliation"]["passed"]:
                    break
            finally:
                engine.dispose()
        result["passed"] = sum(
            s["reconciliation"]["accepted"] for s in result["stages"]
        ) == args.count and all(s["reconciliation"]["passed"] for s in result["stages"])
    except Exception as error:
        result["error_class"] = type(error).__name__
        raise
    finally:
        result["finished_at"] = datetime.now(UTC).isoformat()
        save(args.output / "summary.json", result)
        (args.output / "REPORT.md").write_text(report_text(result), encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
