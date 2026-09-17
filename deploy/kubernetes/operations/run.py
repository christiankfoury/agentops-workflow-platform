"""Run controlled local Kubernetes recovery experiments; preserve all evidence/data."""

import argparse
import gzip
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime
from uuid import uuid4

from support import (
    BASE_IMAGE,
    LOCAL,
    NAMESPACE,
    RELEASE_IMAGE,
    ROOT,
    TABLES,
    approve,
    assert_owned,
    backup_restore,
    command,
    fingerprint,
    fixture,
    get,
    history,
    install,
    kubectl,
    pods,
    publish_tool_graph,
    query,
    ready,
    reconcile,
    refresh_session,
    rollout,
    rows,
    scale,
    signal_worker,
    sink,
)


def direct_health(app, path):
    if app == "api":
        code = """import urllib.request,urllib.error
try:
    print(urllib.request.urlopen('http://localhost:8000/PATH',timeout=5).status)
except urllib.error.HTTPError as error:
    print(error.code)
""".replace("PATH", path)
        args = ["python", "-c", code]
    else:
        args = [
            "node",
            "-e",
            f"fetch('http://127.0.0.1:3000/{path}').then(r=>console.log(r.status))",
        ]
    return int(kubectl("-n", NAMESPACE, "exec", "deployment/" + app, "--", *args).strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".local/kubernetes/operations")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=False)
    assert_owned()
    evidence = {
        "started_at": datetime.now(UTC).isoformat(),
        "passed": False,
        "base_commit": command("git", "rev-parse", "HEAD").strip(),
        "accepted": [],
        "cases": {},
        "source_hashes": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
            for path in (ROOT / "deploy/kubernetes").rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        },
    }
    paused = None

    def checkpoint():
        (output / "summary.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    def batch(client, name, count, path="/write", decide=True):
        refresh_session(client)
        definition = publish_tool_graph(client, path, "operations-" + name + "-" + uuid4().hex[:8])
        identities = []
        for _ in range(count):
            body = {
                "definition_id": definition[0],
                "version_id": definition[1],
                "input": {},
                "idempotency_key": "operations:" + uuid4().hex,
            }
            record = {"case": name, "request": body, "id": None}
            evidence["accepted"].append(record)
            checkpoint()
            record["id"] = fixture.request(client, "POST", "/workflow-executions", json=body)["id"]
            checkpoint()
            assert (
                fixture.request(client, "POST", "/workflow-executions", json=body)["id"]
                == record["id"]
            )
            identities.append(record["id"])
        if decide:
            for identity in identities:
                approve(client, identity)
        return identities

    def held(client, name):
        identity = batch(client, name, 1, "/hold")[0]

        def dispatched():
            item = history(identity)
            return item if item["effects"] and item["effects"][0]["dispatched"] else None

        state = fixture.wait(dispatched)
        key = state["effects"][0]["effect_key"]
        fixture.wait(lambda: any(item["key"] == key for item in sink()["effects"]))
        owner = next(job for job in state["jobs"] if job["status"] == "running")
        name = owner["worker_id"].split(":")[0]
        assert any(pod["metadata"]["name"] == name for pod in pods("worker"))
        return identity, key, name, state

    try:
        evidence["destination_policy"] = install()
        evidence["postgres_version"] = query("SELECT to_json(version())")
        baseline_keys = {row["key"] for row in sink()["effects"]}
        with closing(fixture.login(untrusted_status=404)) as client:
            ids = batch(client, "baseline", 1)
            evidence["cases"]["baseline"] = reconcile(client, ids)
            print("Baseline approved write reconciled", flush=True)

            ids = batch(client, "rolling", 6, "/slow")
            active = fixture.wait(lambda: rows("durable_jobs", "status='running'"))
            for app in ["api", "worker"]:
                kubectl(
                    "-n", NAMESPACE, "set", "image", "deployment/" + app, app + "=" + RELEASE_IMAGE
                )
            samples = []
            with ThreadPoolExecutor(max_workers=2) as pool:
                updates = [pool.submit(rollout, app) for app in ["api", "worker"]]
                while not all(update.done() for update in updates):
                    samples.append(
                        {
                            "at": datetime.now(UTC).isoformat(),
                            "api": client.get("/api/health").status_code,
                            "web": client.get("/ready").status_code,
                        }
                    )
                    time.sleep(1)
                for update in updates:
                    update.result()
            evidence["cases"]["rolling"] = {
                "active_jobs_before_update": active,
                "http_samples": samples,
                "runs": reconcile(client, ids),
                "release": RELEASE_IMAGE,
                "application_and_schema_change": False,
                "deployments": {app: get("deployment/" + app) for app in ["api", "worker"]},
            }
            assert client.get("/ready").status_code == 200
            print("Rolling API/worker update reconciled", flush=True)

            scale(3)
            fleet = query(
                "SELECT json_agg(json_build_object('id',id,'status',status)) "
                "FROM worker_presence WHERE status='running' AND expires_at>clock_timestamp()"
            )
            assert len(fleet) == 3
            ids = batch(client, "scaling", 9, "/slow")
            evidence["cases"]["scaling"] = {
                "registered_workers": fleet,
                "pods": pods("worker"),
                "runs": reconcile(client, ids),
            }
            scale(1)
            print("Three-replica worker execution reconciled", flush=True)

            identity, key, name, before = held(client, "pod-loss")
            old_uid = get("pod/" + name)["metadata"]["uid"]
            kubectl(
                "-n", NAMESPACE, "delete", "pod", name, "--grace-period=0", "--force", "--wait=true"
            )
            result = reconcile(client, [identity])
            assert any(job["recovery_count"] >= 1 for job in result[0]["jobs"])
            sink("/release", {"key": key})
            evidence["cases"]["pod_loss"] = {
                "old_pod_uid": old_uid,
                "before": before,
                "after": result,
            }
            print("Active worker Pod loss and duplicate receipt reconciled", flush=True)

            identity, key, name, before = held(client, "stale-owner")
            paused = name
            pid = signal_worker(name, "SIGSTOP")
            scale(2, wait=False)
            fixture.wait(
                lambda: any(
                    pod["metadata"]["name"] != name and ready(pod) for pod in pods("worker")
                ),
                seconds=180,
            )
            result = reconcile(client, [identity])
            stable = fingerprint(history(identity))
            sink("/release", {"key": key})
            signal_worker(name, "SIGCONT")
            paused = None
            logs = fixture.wait(
                lambda: (
                    text
                    if "late result discarded"
                    in (text := kubectl("-n", NAMESPACE, "logs", name, "--tail=40"))
                    else None
                ),
                seconds=60,
            )
            assert fingerprint(history(identity)) == stable
            evidence["cases"]["stale_owner"] = {
                "pod": name,
                "pid": pid,
                "before": before,
                "after": result,
                "history_hash_before_resume": stable,
                "history_unchanged_after_resume": True,
                "worker_log": logs,
            }
            scale(1)
            print("Resumed stale owner discarded its late result; history unchanged", flush=True)

            ids = batch(client, "readiness", 2, decide=False)
            for identity in ids:
                fixture.wait(
                    lambda: fixture.request(
                        client, "GET", "/execution-approvals", params={"execution_id": identity}
                    )
                )
            try:
                kubectl("-n", NAMESPACE, "scale", "statefulset/db", "--replicas=0")
                kubectl("-n", NAMESPACE, "wait", "--for=delete", "pod/db-0", "--timeout=90s")
                fixture.wait(
                    lambda: all(not ready(pod) for app in ["api", "web"] for pod in pods(app))
                )
                probes = {
                    app: {path: direct_health(app, path) for path in ["health", "ready"]}
                    for app in ["api", "web"]
                }
                assert all(value == {"health": 200, "ready": 503} for value in probes.values())
            finally:
                kubectl("-n", NAMESPACE, "scale", "statefulset/db", "--replicas=1")
                kubectl("-n", NAMESPACE, "rollout", "status", "statefulset/db", "--timeout=180s")
                for app in ["api", "web", "worker"]:
                    fixture.wait(lambda: all(ready(pod) for pod in pods(app)), seconds=240)
            for identity in ids:
                approve(client, identity)
            evidence["cases"]["readiness"] = {
                "dependency_outage_probes": probes,
                "runs": reconcile(client, ids),
                "worker_pods_after": pods("worker"),
            }
            print("Database outage readiness and retained approvals verified", flush=True)

            scale(0)
            backup = LOCAL / ("phase102_" + uuid4().hex[:12] + ".dump")
            evidence["cases"]["backup_restore"] = backup_restore(backup)
            before_sink = sink()
            old_sink = get("pod/effect-sink-0")["metadata"]["uid"]
            kubectl("-n", NAMESPACE, "delete", "pod", "effect-sink-0", "--wait=true")
            fixture.wait(
                lambda: any(
                    ready(pod) and pod["metadata"]["uid"] != old_sink for pod in pods("effect-sink")
                ),
                seconds=120,
            )
            assert sink() == before_sink
            evidence["cases"]["sink_persistence"] = {
                "old_uid": old_sink,
                "new_uid": get("pod/effect-sink-0")["metadata"]["uid"],
                "receipt_hash": fingerprint(before_sink),
                "matched": True,
            }
            print("Backup restored into fresh database; sink PVC retained receipts", flush=True)

            for app in ["api", "worker"]:
                kubectl(
                    "-n", NAMESPACE, "set", "image", "deployment/" + app, app + "=" + BASE_IMAGE
                )
            scale(1)
            rollout("api")
            ids = batch(client, "rollback", 1)
            evidence["cases"]["rollback"] = {
                "image": BASE_IMAGE,
                "runs": reconcile(client, ids),
                "schema": "f097_worker_presence",
            }
            identities = [record["id"] for record in evidence["accepted"]]
            results = reconcile(client, identities)
            keys = {item["effects"][0]["effect_key"] for item in results}
            receipts = sink()
            assert {item["key"] for item in receipts["effects"]} - baseline_keys == keys
            evidence["reconciliation"] = {
                "accepted": len(identities),
                "completed": len(results),
                "distinct_effects": len(keys),
                "sink_calls_for_suite": sum(item["key"] in keys for item in receipts["calls"]),
                "lost_accepted_runs": 0,
                "duplicate_effects": 0,
                "restored_history_verified": True,
            }
            evidence["sink"] = receipts
            evidence["final_tables"] = {table: rows(table) for table in TABLES}
            assert all(
                row["status"] == "completed" for row in evidence["final_tables"]["durable_jobs"]
            )
            evidence["pods"] = get("pods")
            evidence["nodes"] = json.loads(kubectl("get", "nodes", "-o", "json"))
            evidence["replicasets"] = get("replicasets")
            metrics_name = "metrics-phase102-" + uuid4().hex[:8]
            kubectl("-n", NAMESPACE, "create", "job", metrics_name, "--from=cronjob/worker-metrics")
            kubectl(
                "-n",
                NAMESPACE,
                "wait",
                "--for=condition=complete",
                "job/" + metrics_name,
                "--timeout=90s",
            )
            metrics = kubectl("-n", NAMESPACE, "logs", "job/" + metrics_name)
            assert 'agentops_workers{status="running"} 1' in metrics
            (output / "worker-metrics.txt").write_text(metrics)
            evidence["images"] = json.loads(
                command(
                    "docker",
                    "image",
                    "inspect",
                    BASE_IMAGE,
                    RELEASE_IMAGE,
                    "agentops-operations-sink:phase102",
                )
            )
            evidence["passed"] = True
            print("All operations experiments reconciled", flush=True)
    finally:
        if paused:
            try:
                signal_worker(paused, "SIGCONT")
            except Exception as error:
                evidence["resume_cleanup_error"] = type(error).__name__
                evidence["passed"] = False
        for operation in [
            lambda: kubectl("-n", NAMESPACE, "scale", "statefulset/db", "--replicas=1"),
            lambda: scale(1),
        ]:
            try:
                operation()
            except Exception as error:
                evidence.setdefault("cleanup_errors", []).append(type(error).__name__)
                evidence["passed"] = False
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        raw = {
            key: evidence.pop(key)
            for key in ["cases", "sink", "final_tables", "pods", "images", "nodes", "replicasets"]
            if key in evidence
        }
        archive = gzip.compress(json.dumps(raw, indent=2).encode(), mtime=0)
        (output / "operations-evidence.json.gz").write_bytes(archive)
        evidence["raw_evidence"] = {
            "path": "operations-evidence.json.gz",
            "sha256": hashlib.sha256(archive).hexdigest(),
        }
        checkpoint()
    assert evidence["passed"], "Operations cleanup did not finish successfully"
    print(f"Operations acceptance passed: {output}", flush=True)


if __name__ == "__main__":
    main()
