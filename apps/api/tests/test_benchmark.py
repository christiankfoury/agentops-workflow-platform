"""Real CLI acceptance and deliberately corrupted reconciliation evidence."""

import json
import os
import re
import subprocess
import sys
from copy import deepcopy

import pytest
from sqlalchemy import create_engine, text

from src.benchmark import main
from src.benchmarks.evidence import percentiles, reconcile
from src.benchmarks.fixtures import workload
from src.benchmarks.verify import load_stage, verify


def test_bounds_and_fixed_seed(tmp_path):
    assert workload(30, 17) == workload(30, 17)
    assert {item["kind"] for item in workload(30, 17)} == {"condition", "parallel", "sink"}
    assert len({item["value"] for item in workload(30, 17)}) == 30
    assert percentiles([4, 1, 3, 2]) == {"samples": 4, "p50": 2, "p95": 4, "p99": 4, "max": 4}
    for arguments in (["--count", "0"], ["--capacities", "4", "1"], ["--batch-size", "1001"]):
        with pytest.raises(SystemExit) as error:
            main(["--output", str(tmp_path / "unused"), *arguments])
        assert error.value.code == 2
    assert not (tmp_path / "unused").exists()


def test_real_cli_reconciles_and_rejects_lost_or_duplicated_evidence(tmp_path):
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL required")
    output = tmp_path / "benchmark"
    result = None
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.benchmark",
                "--count",
                "12",
                "--capacities",
                "1",
                "4",
                "--batch-size",
                "6",
                "--timeout",
                "120",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert verify(output) == {"passed": True, "accepted": 12, "sink_effects": 4}
        summary = json.loads((output / "summary.json").read_text())
        assert sum(stage["duplicate_starts_prevented"] for stage in summary["stages"]) == 2
        stage = summary["stages"][0]
        data = load_stage(output, stage)
        sink = {row["key"]: row["body"] for row in data["sink-effects"]}
        for collection in ("runs", "jobs", "starts", "attempts", "effects"):
            broken = deepcopy(data)
            broken[collection].pop()
            assert not reconcile(broken["accepted"], broken, sink)["passed"], collection
        duplicate = deepcopy(data)
        duplicate["effects"].append(duplicate["effects"][0])
        assert not reconcile(duplicate["accepted"], duplicate, sink)["passed"]
        assert not reconcile(data["accepted"], data, {})["passed"]
        path = output / stage["files"][0]["file"]
        path.write_bytes(path.read_bytes() + b"corrupt")
        with pytest.raises(ValueError, match="hash mismatch"):
            verify(output)
    finally:
        # Remove ONLY schemas whose generated names this subprocess reported owning.
        schemas = re.findall(
            r"Owned retained schema: (benchmark98_[0-9a-f]{32});",
            result.stdout if result else "",
        )
        engine = create_engine(url)
        with engine.begin() as conn:
            for schema in schemas:
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
