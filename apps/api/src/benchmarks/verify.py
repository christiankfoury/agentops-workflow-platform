"""Recompute reconciliation from hashed benchmark archives without a database."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from src.benchmarks.evidence import reconcile

KINDS = {
    "accepted",
    "starts",
    "runs",
    "jobs",
    "steps",
    "attempts",
    "effects",
    "sink-calls",
    "sink-effects",
    "claim-waits",
}


def load_stage(folder, stage):
    records = {}
    prefix = f"capacity-{stage['capacity']}-"
    expected = {f"{prefix}{kind}.jsonl.gz": kind for kind in KINDS}
    if len(stage["files"]) != len(expected) or {item["file"] for item in stage["files"]} != set(
        expected
    ):
        raise ValueError("Missing or duplicate evidence archive")
    for item in stage["files"]:
        encoded = (folder / item["file"]).read_bytes()
        if hashlib.sha256(encoded).hexdigest() != item["sha256"]:
            raise ValueError("Evidence archive hash mismatch")
        raw = gzip.decompress(encoded)
        rows = [json.loads(line) for line in raw.splitlines()]
        if len(rows) != item["records"] or len(raw) != item["uncompressed_bytes"]:
            raise ValueError("Evidence archive count mismatch")
        records[expected[item["file"]]] = rows
    return records


def verify(folder):
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    if not summary["passed"] or not summary["stages"]:
        raise ValueError("Benchmark did not complete successfully")
    all_ids, all_keys = set(), set()
    for stage in summary["stages"]:
        data = load_stage(folder, stage)
        sink = {row["key"]: row["body"] for row in data["sink-effects"]}
        if len(sink) != len(data["sink-effects"]):
            raise ValueError("Duplicate sink effect identity")
        checked = reconcile(data["accepted"], data, sink)
        if (
            not checked["passed"]
            or checked != stage["reconciliation"]
            or stage["controller_errors"]
            or stage["worker_exceptions"]
            or checked["accepted"] != stage["requested"]
        ):
            raise ValueError("Persisted evidence fails reconciliation")
        ids = {row["id"] for row in data["accepted"]}
        if ids & all_ids or set(sink) & all_keys:
            raise ValueError("Duplicate identity across stages")
        all_ids.update(ids)
        all_keys.update(sink)
    if len(all_ids) != summary["requested"]:
        raise ValueError("Requested acceptance count was not achieved")
    return {"passed": True, "accepted": len(all_ids), "sink_effects": len(all_keys)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.folder)))


if __name__ == "__main__":
    main()
