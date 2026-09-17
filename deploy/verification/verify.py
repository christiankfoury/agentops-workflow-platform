"""Exercise real production containers. Leaves the owned stack/data for inspection."""

import argparse
import gzip
import hashlib
import json
import ssl
import subprocess
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]
ORG = "10000000-0000-4000-8000-000000000100"
PROJECT = "agentops-phase100"
COMPOSE = [
    "docker",
    "compose",
    "-p",
    PROJECT,
    "--env-file",
    str(ROOT / ".local/production/compose.env"),
    "-f",
    str(ROOT / "deploy/compose.production.yml"),
    "-f",
    str(ROOT / "deploy/compose.verification.yml"),
]


def command(*args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=300)
    if result.returncode:
        # Commands contain only paths and fixture identifiers, never raw secrets.
        raise RuntimeError(f"Command failed: {args}: {result.stderr[-2000:]}")
    return result.stdout


def compose(*args):
    return command(*COMPOSE, *args)


def wait(check, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.5)
    raise AssertionError("Verification deadline exceeded")


def obj(**fields):
    return {"type": "object", "properties": fields, "required": list(fields)}


def ref(field, node=None):
    return {
        "op": "ref",
        "ref": {
            "source": "node" if node else "input",
            "path": [field],
            **({"node_id": node} if node else {}),
        },
    }


def graph(approval=True, length=1):
    payload = obj(value={"type": "number"})
    nodes = []
    if approval:
        review = obj(
            approved={"type": "boolean"},
            quality_score={"type": "number"},
            issues={
                "type": "array",
                "items": obj(
                    claim={"type": "string"},
                    problem={"type": "string"},
                    severity={"type": "string"},
                ),
            },
            retry_recommended={"type": "boolean"},
        )
        nodes.append(
            {
                "id": "gate",
                "type": "approval",
                "config": {},
                "input_schema": obj(payload=payload, review=review),
                "output_schema": payload,
                "inputs": {
                    "payload": ref("payload"),
                    "review": {
                        "op": "literal",
                        "value": {
                            "approved": True,
                            "quality_score": 1,
                            "issues": [],
                            "retry_recommended": False,
                        },
                    },
                },
            }
        )
    for index in range(length):
        previous = nodes[-1]["id"] if nodes else None
        nodes.append(
            {
                "id": f"step{index}",
                "type": "code",
                "config": {"handler": "builtin.identity", "version": 1},
                "input_schema": payload,
                "output_schema": payload,
                "inputs": {"value": ref("value", previous)},
            }
        )
    return {
        "entry_node": nodes[0]["id"],
        "input_schema": obj(payload=payload) if approval else payload,
        "output_schema": payload,
        "outputs": {"value": ref("value", nodes[-1]["id"])},
        "nodes": nodes,
        "edges": [{"source": a["id"], "target": b["id"]} for a, b in zip(nodes, nodes[1:])],
    }


def login(origin="https://localhost:8443", ca=None, untrusted_status=421):
    client = httpx.Client(
        base_url=origin,
        verify=ssl.create_default_context(cafile=str(ca or ROOT / ".local/production/ca.crt")),
        follow_redirects=True,
        timeout=15,
    )
    assert (
        client.get("/api/health", headers={"host": "attacker.test"}).status_code == untrusted_status
    )
    assert client.get("/api/workflow-definitions").status_code == 401
    response = client.get("/auth/sign-in")
    assert response.status_code == 200 and "Local verifier" in response.text
    cookie = next(c for c in client.cookies.jar if c.name == "agentops-session")
    assert cookie.secure and cookie.has_nonstandard_attr("HttpOnly")
    client.headers.update({"authorization": f"Session {cookie.value}", "x-organization-id": ORG})
    return client


def request(client, method, path, **kwargs):
    response = client.request(method, "/api" + path, **kwargs)
    assert response.is_success, f"{method} {path}: {response.status_code} {response.text[:500]}"
    return response.json()


def publish(client, definition_graph):
    definition = request(
        client,
        "POST",
        "/workflow-definitions",
        json={"name": "Production verification " + str(uuid4())[:8], "graph": definition_graph},
    )
    version = request(
        client,
        "POST",
        f"/workflow-definitions/{definition['id']}/publish",
        json={"expected_revision": definition["draft_revision"]},
    )
    return definition["id"], version["id"]


def start(client, definition, payload):
    body = {
        "definition_id": definition[0],
        "version_id": definition[1],
        "input": payload,
        "idempotency_key": "verification:" + str(uuid4()),
    }
    result = request(client, "POST", "/workflow-executions", json=body)
    assert request(client, "POST", "/workflow-executions", json=body)["id"] == result["id"]
    return result["id"]


def completed(client, identity):
    result = request(client, "GET", f"/workflow-executions/{identity}")
    assert result["status"] not in {"failed", "cancelled"}, result
    return result if result["status"] == "completed" else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/evidence/phase100")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=False)
    evidence = {
        "started_at": datetime.now(UTC).isoformat(),
        "passed": False,
        "base_commit": command("git", "rev-parse", "HEAD").strip(),
        "project": PROJECT,
    }
    evidence["source_hashes"] = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for folder in ["apps/api/src", "deploy"]
        for path in (ROOT / folder).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    try:
        # Explicit project labels prevent accidentally operating on another stack.
        for identity in compose("ps", "-q").split():
            inspect = json.loads(command("docker", "inspect", identity))[0]
            assert inspect["Config"]["Labels"]["com.docker.compose.project"] == PROJECT
        compose(
            "run",
            "--rm",
            "--no-deps",
            "migrate",
            "python",
            "-m",
            "src.provision_identity",
            "--issuer",
            "https://localhost:8443/oidc",
            "--subject",
            "local-verifier",
            "--display-name",
            "Local verifier",
            "--organization-id",
            ORG,
            "--organization-name",
            "Disposable production verification",
            "--role",
            "admin",
        )
        with closing(login()) as client:
            assert client.get("/ready").status_code == 200
            definition = publish(client, graph())
            identity = start(client, definition, {"payload": {"value": 42}})
            approvals = wait(
                lambda: request(
                    client, "GET", "/execution-approvals", params={"execution_id": identity}
                )
            )
            approval = approvals[0]
            request(
                client,
                "POST",
                f"/execution-approvals/{approval['id']}/decide",
                json={"action": "approve", "expected_payload_hash": approval["payload_hash"]},
            )
            run = wait(lambda: completed(client, identity))
            assert run["output_json"] == {"value": 42}
            assert run["version_id"] == definition[1]
            evidence["approval_run"] = run
            evidence["approval"] = request(client, "GET", f"/execution-approvals/{approval['id']}")
            assert client.get("/workflow-definitions").status_code == 200
            compose("restart", "db", "api", "worker", "web")
            wait(lambda: client.get("/ready").status_code == 200)
            assert completed(client, identity)["output_json"] == {"value": 42}
            assert (
                request(client, "GET", f"/execution-approvals/{approval['id']}")
                == evidence["approval"]
            )
            assert "Local verifier" in client.get("/account").text
            evidence["restart_persistence"] = True
            compose("stop", "db")
            try:
                assert client.get("/api/ready").status_code == 503
                assert client.get("/ready").status_code == 503
                assert client.get("/api/health").status_code == 200
                evidence["dependency_readiness"] = {"api": 503, "web": 503, "liveness": 200}
            finally:
                compose("start", "db")
                compose("restart", "worker")
            wait(lambda: client.get("/ready").status_code == 200)
            worker_id = compose("ps", "-q", "worker").strip()
            wait(
                lambda: (
                    json.loads(command("docker", "inspect", worker_id))[0]["State"]["Health"][
                        "Status"
                    ]
                    == "healthy"
                )
            )
            burst = publish(client, graph(False, 24))
            accepted = [start(client, burst, {"value": i}) for i in range(8)]
            evidence["accepted_burst_ids"] = accepted
            before = request(client, "GET", "/operations")
            evidence["before_shutdown"] = before
            assert before["jobs"].get("queued", 0) + before["jobs"].get("running", 0) > 0
            compose("stop", "worker")  # Actual Docker SIGTERM with 60-second grace.
            state = json.loads(command("docker", "inspect", worker_id))[0]["State"]
            evidence["worker_shutdown"] = {"state": state}
            try:
                assert state["ExitCode"] == 0 and not state["OOMKilled"], state
                after = request(client, "GET", "/operations")
                assert after["jobs"].get("running", 0) == 0
                time.sleep(2)
                assert request(client, "GET", "/operations")["claims"] == after["claims"]
                evidence["worker_shutdown"].update(
                    {
                        "before": before,
                        "after": after,
                        "claims_stable_while_stopped": True,
                    }
                )
            finally:
                compose("start", "worker")
            evidence["burst_runs"] = [
                wait(lambda identity=i: completed(client, identity)) for i in accepted
            ]
            assert [r["output_json"]["value"] for r in evidence["burst_runs"]] == list(range(8))
            evidence["operations"] = request(client, "GET", "/operations")
            evidence["jobs"] = {
                i: request(client, "GET", f"/workflow-executions/{i}/jobs")
                for i in [identity, *accepted]
            }
            assert all(
                j["status"] == "completed" for jobs in evidence["jobs"].values() for j in jobs
            )
            assert all(evidence["jobs"].values())
            job_ids = [j["id"] for jobs in evidence["jobs"].values() for j in jobs]
            assert len(job_ids) == len(set(job_ids))
        evidence["images"] = []
        for name in [
            "agentops-api:production",
            "agentops-web:production",
            "agentops-gateway:production",
        ]:
            item = json.loads(command("docker", "image", "inspect", name))[0]
            assert item["Config"]["User"] not in {"", "root", "0", "0:0"}
            history = command("docker", "history", "--no-trunc", name)
            metadata = json.dumps(item) + history
            for secret_name in ["database_password", "tls.key", "oidc.key"]:
                secret = (ROOT / ".local/production" / secret_name).read_text().strip()
                assert secret not in metadata, "A generated secret was embedded in image metadata"
            if "gateway" not in name:
                files = command(
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--read-only",
                    "--entrypoint",
                    "sh",
                    name,
                    "-c",
                    "find /app -type f \\( -name '.env*' -o -name '*.key' \\)",
                )
                assert not files.strip(), "Unexpected environment/key file in application image"
            evidence["images"].append(
                {
                    "name": name,
                    "id": item["Id"],
                    "user": item["Config"]["User"],
                    "generated_secrets_absent_from_metadata": True,
                }
            )
        evidence["passed"] = True
    finally:
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        raw = gzip.compress(json.dumps(evidence, indent=2).encode(), mtime=0)
        (output / "verification.json.gz").write_bytes(raw)
        summary = {
            key: evidence[key] for key in ["started_at", "finished_at", "passed", "base_commit"]
        }
        summary.update(
            {
                "archive": "verification.json.gz",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "accepted_ids": [evidence["approval_run"]["id"]]
                + evidence.get("accepted_burst_ids", [])
                if "approval_run" in evidence
                else [],
                "terminal_jobs": sum(len(jobs) for jobs in evidence.get("jobs", {}).values()),
                "images": evidence.get("images", []),
            }
        )
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Production verification passed; evidence:", output)


if __name__ == "__main__":
    main()
