"""Independent, file-backed reconciliation for disposable Phase 99 experiments."""

import json
import os
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import monotonic

import pytest
from sqlalchemy import select

from src.benchmarks.evidence import json_text, save, snapshot
from src.models.execution_approval import ExecutionApproval
from src.models.execution_recovery import ExecutionRecovery
from src.models.schedule import ScheduleFire
from src.models.tool import ToolExecution
from src.models.workflow_execution import ExecutionEvent


def state(database):
    data = snapshot(database)
    # The shared test fixture uses schema translation, not connection search_path.
    # Its current_schema() relation-size observation is therefore not applicable.
    data.pop("schema_bytes")
    with database.connect() as conn:
        for name, model in (
            ("events", ExecutionEvent),
            ("approvals", ExecutionApproval),
            ("recoveries", ExecutionRecovery),
            ("fires", ScheduleFire),
            ("effects", ToolExecution),
        ):
            data[name] = [dict(row) for row in conn.execute(select(model.__table__)).mappings()]
    # Identical representation for live checks and independent offline verification.
    return json.loads(json_text(data))


def reconcile(record):
    data = record["frames"][-1]["state"]
    runs = {row["id"]: row for row in data["runs"]}
    accepted = set(record["accepted"])
    assert set(runs) == accepted and len(runs) == len(data["runs"]), "Accepted ID mismatch"
    assert {key: row["status"] for key, row in runs.items()} == record["expected_statuses"]
    assert all(row["status"] in {"completed", "failed", "cancelled"} for row in runs.values())
    receipts = {row["execution_id"] for row in data["starts"] + data["recoveries"]}
    assert receipts == accepted, "Missing start or recovery admission receipt"
    jobs = {row["id"]: row for row in data["jobs"]}
    admissions = Counter(
        row["entity_id"]
        for row in data["events"]
        if row["entity_type"] == "durable_jobs" and row["from_status"] is None
    )
    assert admissions == Counter({key: 1 for key in jobs}), "Queued job admission mismatch"
    assert len(jobs) == len(data["jobs"])
    earlier = {
        row["id"] for frame in record["frames"] for row in frame.get("state", {}).get("jobs", [])
    }
    assert earlier == set(jobs), "A previously observed job disappeared"
    assert all(row["execution_id"] in accepted for row in jobs.values())
    assert all(row["status"] in {"completed", "failed", "cancelled"} for row in jobs.values())
    steps = {row["id"]: row for row in data["steps"]}
    assert all(row["execution_id"] in accepted for row in steps.values())
    assert all(row["step_run_id"] in steps for row in data["attempts"])
    assert all(row["status"] in {"completed", "failed", "cancelled"} for row in data["attempts"])
    intended, observed = record["intended_effects"], record["sink"]["effects"]
    ledger = {row["effect_key"]: row for row in data["effects"]}
    assert len(ledger) == len(data["effects"]), "Duplicate ledger identity"
    assert len(observed) == len(intended), "Lost or duplicate intended sink effects"
    owners = Counter()
    for key, effect in ledger.items():
        owner = steps[effect["step_run_id"]]["execution_id"]
        owners[owner] += 1
        assert effect["request_json"] == intended[owner]
        assert effect["status"] in {"succeeded", "reconciled", "unknown"}
        if record["sink"]["idempotent"]:
            assert observed[key] == intended[owner], "Sink identity/body mismatch"
        if effect["status"] != "unknown":
            assert effect["result_json"] == {"status": 200, "body": intended[owner]}
    assert owners == Counter({key: 1 for key in intended}), "Intended effect owner mismatch"
    if record["sink"]["idempotent"]:
        assert set(observed) == set(ledger)
    else:
        assert Counter(map(json_text, observed.values())) == Counter(
            map(json_text, intended.values())
        )
    unknown = sum(row["status"] == "unknown" for row in ledger.values())
    assert unknown == record["expected_unknown"], "Unexpected unresolved remote outcome"
    return {
        "accepted": len(accepted),
        "run_statuses": dict(Counter(row["status"] for row in runs.values())),
        "jobs": len(jobs),
        "job_statuses": dict(Counter(row["status"] for row in jobs.values())),
        "attempts": len(data["attempts"]),
        "intended_effects": len(intended),
        "observed_effects": len(observed),
        "unknown_effects": unknown,
        "lost_jobs": 0,
        "lost_effects": 0,
        "duplicate_effects": 0,
        "sink_requests": len(record["sink"]["calls"]),
        "sink_duplicates_prevented": (
            len(record["sink"]["calls"]) - len(observed) if record["sink"]["idempotent"] else 0
        ),
    }


class Evidence:
    def __init__(self, name, database):
        self.database = database
        self.started = monotonic()
        self.record = {
            "scenario": name,
            "started_at": datetime.now(UTC).isoformat(),
            "accepted": [],
            "frames": [],
            "measurements": {},
            "intended_effects": {},
            "expected_unknown": 0,
            "sink": {"idempotent": True, "calls": [], "effects": {}},
            "passed": False,
        }

    def accept(self, identity, effect=None):
        identity = str(identity)
        assert identity not in self.record["accepted"]
        self.record["accepted"].append(identity)
        if effect is not None:
            self.record["intended_effects"][identity] = effect

    def mark(self, name, *, capture=True, **details):
        frame = {
            "name": name,
            "at": datetime.now(UTC).isoformat(),
            "elapsed_seconds": monotonic() - self.started,
            "details": details,
        }
        if capture:
            frame["state"] = state(self.database)
        self.record["frames"].append(frame)
        return monotonic()

    def finish(self, expected, *, since, sink=None, idempotent=True, unknown=0, **measurements):
        self.record["measurements"].update(recovery_seconds=monotonic() - since, **measurements)
        if sink is not None:
            self.record["sink"] = {
                "idempotent": idempotent,
                "calls": list(sink.calls),
                "effects": dict(sink.effects),
            }
        self.record["expected_statuses"] = {str(key): value for key, value in expected.items()}
        self.record["expected_unknown"] = unknown
        self.mark("settled")
        self.record["reconciliation"] = reconcile(self.record)
        self.record["passed"] = True


@pytest.fixture
def evidence(request, database, monkeypatch):
    from pydantic import SecretStr

    from src.config import settings

    monkeypatch.setattr(settings, "identity_enabled", False)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr(""))
    item = Evidence(request.node.name, database)
    yield item
    folder = os.environ.get("RELIABILITY_OUTPUT")
    if folder:
        target = Path(folder)
        assert target.is_dir(), "Experiment runner must create the output directory"
        name = sha256(request.node.nodeid.encode()).hexdigest()[:16] + ".json"
        assert not (target / name).exists(), "Never overwrite earlier experiment evidence"
        save(target / name, item.record)
