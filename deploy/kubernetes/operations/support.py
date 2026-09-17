"""Owned-cluster operations helpers. No public endpoint or production credentials."""

import hashlib
import json
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cluster import CLUSTER, LOCAL, NAMESPACE, apply, binary, kubectl, render  # noqa: E402
from cluster import ROOT as ROOT  # noqa: E402
from cluster import assert_owned as assert_owned
from cluster import command as command
from verify import fixture, get  # noqa: E402

TABLES = [
    "workflow_definitions",
    "workflow_versions",
    "workflow_executions",
    "execution_approvals",
    "step_runs",
    "step_attempts",
    "durable_jobs",
    "execution_events",
    "tool_definitions",
    "tool_versions",
    "tool_executions",
]
BASE_IMAGE = "agentops-api:kubernetes"
RELEASE_IMAGE = "agentops-api:phase102-release"


def query(statement, database="agentops"):
    return json.loads(
        kubectl(
            "-n",
            NAMESPACE,
            "exec",
            "db-0",
            "--",
            "psql",
            "-X",
            "-U",
            "agentops",
            "-d",
            database,
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            statement,
        ).strip()
    )


def rows(table, where="true", database="agentops"):
    assert table in TABLES
    return query(
        "SELECT COALESCE(json_agg(to_jsonb(q)-'claim_token'-'reservation_token'"
        f"-'credential_digest' ORDER BY q.id),'[]'::json) FROM (SELECT * FROM {table} "
        f"WHERE {where}) q",
        database,
    )


def history(identity):
    identity = str(UUID(identity))
    steps = f"SELECT id FROM step_runs WHERE execution_id='{identity}'"
    return {
        "run": rows("workflow_executions", f"id='{identity}'"),
        "steps": rows("step_runs", f"execution_id='{identity}'"),
        "attempts": rows("step_attempts", f"step_run_id IN ({steps})"),
        "jobs": rows("durable_jobs", f"execution_id='{identity}'"),
        "events": rows("execution_events", f"execution_id='{identity}'"),
        "approvals": rows("execution_approvals", f"execution_id='{identity}'"),
        "effects": rows("tool_executions", f"step_run_id IN ({steps})"),
    }


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def pods(app):
    return json.loads(kubectl("-n", NAMESPACE, "get", "pods", "-l", f"app={app}", "-o", "json"))[
        "items"
    ]


def ready(pod):
    return not pod["metadata"].get("deletionTimestamp") and any(
        item["type"] == "Ready" and item["status"] == "True"
        for item in pod["status"].get("conditions", [])
    )


def scale(replicas, wait=True):
    kubectl("-n", NAMESPACE, "scale", "deployment/worker", f"--replicas={replicas}")
    if wait:
        fixture.wait(
            lambda: (
                len(pods("worker")) == replicas
                and sum(ready(pod) for pod in pods("worker")) == replicas
            ),
            seconds=180,
        )


def rollout(name):
    return kubectl(
        "-n", NAMESPACE, "rollout", "status", "deployment/" + name, "--timeout=240s", timeout=260
    )


def sink(path="/snapshot", body=None):
    code = (
        "import json,urllib.request; "
        f"r=urllib.request.Request('http://127.0.0.1:8080{path}',"
        f"data={repr(json.dumps(body).encode()) if body is not None else 'None'},"
        "headers={'Content-Type':'application/json'}); "
        "print(urllib.request.urlopen(r,timeout=10).read().decode())"
    )
    return json.loads(
        kubectl("-n", NAMESPACE, "exec", "statefulset/effect-sink", "--", "python", "-c", code)
    )


def signal_worker(name, signal_name):
    assert signal_name in {"SIGSTOP", "SIGCONT"}
    code = r"""import os,signal
from pathlib import Path
found=[]
for path in Path('/proc').iterdir():
    if path.name.isdigit():
        try:
            args=(path/'cmdline').read_bytes().split(b'\0')
            if args[1:3]==[b'-m',b'src.worker']:
                found.append(int(path.name))
        except (FileNotFoundError,PermissionError):
            pass
assert len(found)==1,found
os.kill(found[0],getattr(signal,SIGNAL))
print(found[0])
""".replace("SIGNAL", repr(signal_name))
    return int(kubectl("-n", NAMESPACE, "exec", name, "--", "python", "-c", code).strip())


def install():
    print(apply(render("operations")), flush=True)
    kubectl("-n", NAMESPACE, "rollout", "status", "statefulset/effect-sink", "--timeout=180s")
    service_ip = get("service/effect-sink")["spec"]["clusterIP"]
    policy = {
        f"{fixture.ORG}/operations": {
            "origin": "http://effect-sink:8080",
            "methods": ["POST"],
            "allowed_private_cidrs": [service_ip + "/32"],
            "allow_plain_http": True,
            "idempotency_retention_seconds": 3600,
        }
    }
    kubectl(
        "-n",
        NAMESPACE,
        "patch",
        "configmap/runtime",
        "--type=merge",
        "-p",
        json.dumps({"data": {"HTTP_TOOL_DESTINATIONS": json.dumps(policy)}}),
    )
    for app in ["api", "worker"]:
        kubectl("-n", NAMESPACE, "set", "image", "deployment/" + app, app + "=" + BASE_IMAGE)
    kubectl("-n", NAMESPACE, "rollout", "restart", "deployment/api", "deployment/worker")
    rollout("api")
    rollout("worker")
    return policy


def publish_tool_graph(client, path, label):
    payload = fixture.obj(value={"type": "string"})
    output = fixture.obj(status={"type": "integer"}, body=payload)
    retry = {
        "max_attempts": 3,
        "initial_delay_seconds": 0,
        "retryable_errors": ["tool_unavailable", "tool_timeout", "worker_abandoned"],
    }
    tool = fixture.request(
        client,
        "POST",
        "/tools",
        json={
            "name": label,
            "contract": {
                "adapter": "http",
                "input_schema": payload,
                "output_schema": output,
                "side_effecting": True,
                "timeout_seconds": 180,
                "retry": retry,
                "options": {"destination": "operations", "method": "POST", "path": path},
            },
        },
    )
    envelope = fixture.obj(
        node_id={"type": "string"},
        tool_id={"type": "string"},
        version={"type": "integer"},
        arguments=payload,
    )
    gate = fixture.graph()["nodes"][0]
    gate["input_schema"]["properties"]["payload"] = envelope
    gate["output_schema"] = envelope
    gate["inputs"]["payload"] = {
        "op": "literal",
        "value": {
            "node_id": "action",
            "tool_id": tool["definition_id"],
            "version": 1,
            "arguments": {"value": label},
        },
    }
    definition = {
        "entry_node": "gate",
        "input_schema": fixture.obj(),
        "output_schema": payload,
        "outputs": {
            "value": {
                "op": "ref",
                "ref": {
                    "source": "node",
                    "node_id": "action",
                    "path": ["body", "value"],
                },
            }
        },
        "nodes": [
            gate,
            {
                "id": "action",
                "type": "tool",
                "input_schema": payload,
                "output_schema": output,
                "timeout_seconds": 240,
                "retry": retry,
                "config": {"tool_id": tool["definition_id"], "version": 1, "approval_node": "gate"},
                "inputs": {
                    "value": {
                        "op": "ref",
                        "ref": {
                            "source": "node",
                            "node_id": "gate",
                            "path": ["arguments", "value"],
                        },
                    }
                },
            },
        ],
        "edges": [{"source": "gate", "target": "action"}],
    }
    return fixture.publish(client, definition)


def approve(client, identity):
    approval = fixture.wait(
        lambda: fixture.request(
            client, "GET", "/execution-approvals", params={"execution_id": identity}
        )
    )[0]
    fixture.request(
        client,
        "POST",
        f"/execution-approvals/{approval['id']}/decide",
        json={"action": "approve", "expected_payload_hash": approval["payload_hash"]},
    )


def refresh_session(client):
    # The explicit local OIDC fixture issues five-minute tokens. Renew normally
    # between long experiments instead of weakening production expiry checks.
    with closing(fixture.login(untrusted_status=404)) as fresh:
        client.cookies.clear()
        client.cookies.update(fresh.cookies)
        client.headers["authorization"] = fresh.headers["authorization"]


def reconcile(client, identities):
    refresh_session(client)
    results = []
    for identity in identities:
        run = fixture.wait(lambda: fixture.completed(client, identity), seconds=240)
        evidence = history(identity)
        assert all(item["status"] == "completed" for item in evidence["jobs"])
        assert len(evidence["effects"]) == 1
        effect = evidence["effects"][0]
        assert effect["status"] == "succeeded" or (
            effect["status"] == "reconciled"
            and (effect["reconciliation"] or {}).get("outcome") == "succeeded"
        )
        assert effect["result_json"]["body"] == effect["request_json"]
        assert run["output_json"] == effect["request_json"]
        assert evidence["approvals"][0]["status"] == "approved"
        assert run["version_id"] == evidence["approvals"][0]["version_id"]
        results.append(evidence)
    receipts = sink()
    effects = {item["key"]: item for item in receipts["effects"]}
    for evidence in results:
        effect = evidence["effects"][0]
        assert effect["effect_key"] in effects
        assert json.loads(effects[effect["effect_key"]]["payload"]) == effect["request_json"]
    return results


def backup_restore(destination):
    before = {table: rows(table) for table in TABLES}
    assert all(row["status"] not in {"queued", "running"} for row in before["durable_jobs"])
    assert before["tool_executions"] and before["execution_approvals"]
    base = [
        binary("kubectl"),
        "--kubeconfig",
        str(LOCAL / "kubeconfig"),
        "--context",
        "kind-" + CLUSTER,
        "-n",
        NAMESPACE,
        "exec",
    ]
    with destination.open("xb") as stream:
        subprocess.run(
            [*base, "db-0", "--", "pg_dump", "-U", "agentops", "-d", "agentops", "--format=custom"],
            stdout=stream,
            check=True,
            timeout=180,
        )
    database = "restore_" + destination.stem.replace("-", "_")
    assert database.replace("_", "").isalnum() and len(database) < 63
    kubectl("-n", NAMESPACE, "exec", "db-0", "--", "createdb", "-U", "agentops", database)
    with destination.open("rb") as stream:
        subprocess.run(
            [
                *base,
                "-i",
                "db-0",
                "--",
                "pg_restore",
                "-U",
                "agentops",
                "-d",
                database,
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
            ],
            stdin=stream,
            check=True,
            timeout=180,
        )
    after = {table: rows(table, database=database) for table in TABLES}
    assert before == after
    assert (
        query("SELECT to_json(version_num) FROM alembic_version", database)
        == "f097_worker_presence"
    )
    return {
        "restored_database": database,
        "backup_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "backup_bytes": destination.stat().st_size,
        "tables": {
            table: {"count": len(value), "sha256": fingerprint(value)}
            for table, value in before.items()
        },
        "matched": True,
    }
