"""Run repeated Phase 99 fault scenarios or verify their archived evidence offline."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

from src.benchmarks.evidence import API, ROOT, environment, save
from tests.reliability_evidence import reconcile

EXPECTED_CASES = 15


def verify(folder):
    manifest = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    assert manifest["passed"] and len(manifest["repetitions"]) == manifest["requested_repetitions"]
    totals, statuses, identities, scenarios = Counter(), Counter(), set(), None
    for repetition in manifest["repetitions"]:
        assert repetition["exit_code"] == 0
        assert repetition["tests"] == len(repetition["files"]) == EXPECTED_CASES
        names = set()
        for entry in repetition["files"]:
            path = Path(entry["file"])
            assert not path.is_absolute() and ".." not in path.parts
            encoded = (folder / path).read_bytes()
            assert hashlib.sha256(encoded).hexdigest() == entry["sha256"]
            record = json.loads(gzip.decompress(encoded))
            assert record["passed"]
            result = reconcile(record)
            assert result == record["reconciliation"]
            assert record["scenario"] not in names
            names.add(record["scenario"])
            assert not identities.intersection(record["accepted"])
            identities.update(record["accepted"])
            statuses.update(result["run_statuses"])
            totals.update({key: value for key, value in result.items() if type(value) is int})
        assert scenarios is None or names == scenarios, "Each repetition must cover every scenario"
        scenarios = names
    return {
        "passed": True,
        "scenario_count": len(scenarios),
        "totals": dict(totals),
        "run_statuses": dict(statuses),
    }


def run(args):
    if not os.environ.get("WORKFLOW_TEST_DATABASE_URL"):
        raise ValueError("WORKFLOW_TEST_DATABASE_URL must name a disposable test database")
    if not 1 <= args.repeat <= 10:
        raise ValueError("Repeat must be between 1 and 10")
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    provenance = environment()
    provenance["test_source_sha256"] = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for path in sorted((API / "tests").glob("*.py"))
    }
    manifest = {
        "started_at": datetime.now(UTC).isoformat(),
        "environment": provenance,
        "requested_repetitions": args.repeat,
        "repetitions": [],
        "passed": False,
    }
    try:
        for index in range(1, args.repeat + 1):
            target = folder / f"repeat-{index}"
            target.mkdir()
            with (target / "pytest.log").open("wb") as log:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "tests/test_reliability_experiments.py",
                        "-q",
                        f"--junitxml={target / 'junit.xml'}",
                    ],
                    cwd=API,
                    env={**os.environ, "RELIABILITY_OUTPUT": str(target), "PYTEST_ADDOPTS": ""},
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=1200,
                )
            files = []
            for path in sorted(target.glob("*.json")):
                raw = path.read_bytes()
                record = json.loads(raw)
                encoded = gzip.compress(raw, mtime=0)
                archived = path.with_suffix(".json.gz")
                archived.write_bytes(encoded)
                files.append(
                    {
                        "file": archived.relative_to(folder).as_posix(),
                        "sha256": hashlib.sha256(encoded).hexdigest(),
                        "scenario": record["scenario"],
                        "passed": record["passed"],
                        "measurements": record["measurements"],
                    }
                )
                path.unlink()  # This new output directory owns these just-created files.
            suites = ElementTree.parse(target / "junit.xml").getroot().findall("testsuite")
            counts = {
                key: sum(int(suite.attrib[key]) for suite in suites)
                for key in ("tests", "failures", "errors", "skipped")
            }
            item = {"index": index, "exit_code": result.returncode, **counts, "files": files}
            manifest["repetitions"].append(item)
            save(folder / "summary.json", manifest)
            print(
                json.dumps({key: value for key, value in item.items() if key != "files"}),
                flush=True,
            )
            if result.returncode or any(counts[key] for key in ("failures", "errors", "skipped")):
                break
        manifest["passed"] = len(manifest["repetitions"]) == args.repeat and all(
            item["exit_code"] == 0
            and item["tests"] == len(item["files"]) == EXPECTED_CASES
            and not any(item[key] for key in ("failures", "errors", "skipped"))
            and all(entry["passed"] for entry in item["files"])
            for item in manifest["repetitions"]
        )
    finally:
        manifest["finished_at"] = datetime.now(UTC).isoformat()
        save(folder / "summary.json", manifest)
    if manifest["passed"]:
        try:
            manifest["verification"] = verify(folder)
        except Exception as error:
            manifest["passed"] = False
            manifest["verification_error"] = type(error).__name__
            save(folder / "summary.json", manifest)
            raise
        save(folder / "summary.json", manifest)
        print(json.dumps(manifest["verification"]), flush=True)
    return 0 if manifest["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    execute = sub.add_parser("run")
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--repeat", type=int, default=3)
    check = sub.add_parser("verify")
    check.add_argument("folder", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(verify(args.folder)))
        return 0
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
