"""Authenticated ingress, migration, operator metrics and PVC acceptance."""

import argparse
import gzip
import hashlib
import importlib.util
import json
from contextlib import closing
from datetime import UTC, datetime

from cluster import LOCAL, NAMESPACE, ROOT, assert_owned, command, job, kubectl, render

spec = importlib.util.spec_from_file_location(
    "production_verify", ROOT / "deploy/verification/verify.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def get(resource, namespace=NAMESPACE):
    return json.loads(kubectl("-n", namespace, "get", resource, "-o", "json"))


def restart_pod(selector):
    pods = json.loads(kubectl("-n", NAMESPACE, "get", "pods", "-l", selector, "-o", "json"))
    assert len(pods["items"]) == 1
    before = pods["items"][0]
    kubectl("-n", NAMESPACE, "delete", "pod", before["metadata"]["name"], "--wait=true")

    def replacement():
        current = json.loads(kubectl("-n", NAMESPACE, "get", "pods", "-l", selector, "-o", "json"))
        for pod in current["items"]:
            if pod["metadata"]["uid"] != before["metadata"]["uid"] and any(
                condition["type"] == "Ready" and condition["status"] == "True"
                for condition in pod["status"].get("conditions", [])
            ):
                return pod
        return None

    after = fixture.wait(replacement, seconds=180)
    return {"before": before["metadata"]["uid"], "after": after["metadata"]["uid"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".local/kubernetes/verification")
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=False)
    assert_owned()
    evidence = {
        "started_at": datetime.now(UTC).isoformat(),
        "passed": False,
        "deployment": json.loads((LOCAL / "deployment.json").read_text()),
        "source_hashes": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
            for path in [
                *(ROOT / "deploy").rglob("*"),
                ROOT / "apps/api/Dockerfile.production",
                ROOT / "apps/api/container_entrypoint.py",
                ROOT / "apps/web/Dockerfile.production",
                ROOT / "apps/web/container-entrypoint.mjs",
                ROOT / "apps/web/src/lib/api-url.ts",
            ]
            if path.is_file() and "__pycache__" not in path.parts
        },
    }
    try:
        initial_pods = get("pods")["items"]
        migration_name = evidence["deployment"]["first_migration_job"]
        migration_finished = get("job/" + migration_name)["status"]["completionTime"]
        application_pods = [
            pod
            for pod in initial_pods
            if pod["metadata"].get("labels", {}).get("app")
            in {"api", "web", "worker", "gateway", "oidc"}
        ]
        assert len(application_pods) == 5
        assert all(
            pod["metadata"]["creationTimestamp"] >= migration_finished for pod in application_pods
        )
        assert all(pod["spec"]["automountServiceAccountToken"] is False for pod in initial_pods)
        evidence["migration_before_application_pods"] = True
        evidence["application_service_account_tokens_disabled"] = True
        pvc_before = get("pvc/data-db-0")["metadata"]["uid"]
        migration = next(item for item in render() if item["kind"] == "Job")
        name = "identity-" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        evidence["identity_provisioning"] = job(
            migration,
            name,
            [
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
                fixture.ORG,
                "--organization-name",
                "Disposable Kubernetes verification",
                "--role",
                "admin",
            ],
        )
        with closing(fixture.login(untrusted_status=404)) as client:
            assert client.get("/ready").status_code == 200
            definition = fixture.publish(client, fixture.graph())
            identity = fixture.start(client, definition, {"payload": {"value": 42}})
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
            run = fixture.wait(lambda: fixture.completed(client, identity))
            assert run["output_json"] == {"value": 42} and run["version_id"] == definition[1]
            evidence["run"] = run
            evidence["approval"] = fixture.request(
                client, "GET", f"/execution-approvals/{approval['id']}"
            )
            page = client.get("/workflow-definitions")
            assert page.status_code == 200 and definition[0] in page.text
            evidence["authenticated_ssr"] = True
            evidence["pod_replacements"] = {
                name: restart_pod(f"app={name}") for name in ["db", "api", "worker"]
            }
            fixture.wait(lambda: client.get("/ready").status_code == 200)
            assert fixture.completed(client, identity)["output_json"] == {"value": 42}
            assert (
                fixture.request(client, "GET", f"/execution-approvals/{approval['id']}")
                == evidence["approval"]
            )
            assert "Local verifier" in client.get("/account").text
            evidence["persistence_after_replacement"] = True
            assert get("pvc/data-db-0")["metadata"]["uid"] == pvc_before
            evidence["persistent_volume_claim_uid"] = pvc_before
            evidence["tenant_metrics_status"] = client.get("/api/operations/metrics").status_code
            assert evidence["tenant_metrics_status"] == 200
        metrics_name = "metrics-" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        kubectl("-n", NAMESPACE, "create", "job", metrics_name, "--from=cronjob/worker-metrics")
        kubectl(
            "-n",
            NAMESPACE,
            "wait",
            "--for=condition=complete",
            f"job/{metrics_name}",
            "--timeout=90s",
        )
        metrics = kubectl("-n", NAMESPACE, "logs", f"job/{metrics_name}")
        assert 'agentops_workers{status="running"} 1' in metrics
        (output / "worker-metrics.txt").write_text(metrics)
        evidence["migration"] = get("job/" + evidence["deployment"]["migration_job"])
        evidence["first_migration"] = get("job/" + migration_name)
        evidence["nodes"] = json.loads(kubectl("get", "nodes", "-o", "json"))
        evidence["pods"] = get("pods")
        evidence["pvc"] = get("pvc")
        evidence["ingress"] = get("ingress", "agentops-ingress")
        evidence["images"] = json.loads(
            command(
                "docker",
                "image",
                "inspect",
                "agentops-api:kubernetes",
                "agentops-web:kubernetes-v2",
                "agentops-gateway:kubernetes",
                "agentops-oidc-fixture:kubernetes",
                "traefik:v3.7.13",
            )
        )
        evidence["passed"] = True
    finally:
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        raw = {
            key: evidence.pop(key)
            for key in ["migration", "first_migration", "nodes", "pods", "pvc", "ingress", "images"]
            if key in evidence
        }
        if raw:
            archive = gzip.compress(json.dumps(raw, indent=2).encode(), mtime=0)
            (output / "cluster-evidence.json.gz").write_bytes(archive)
            evidence["raw_evidence"] = {
                "path": "cluster-evidence.json.gz",
                "sha256": hashlib.sha256(archive).hexdigest(),
            }
            evidence["image_ids"] = {
                next(
                    (tag for tag in item["RepoTags"] if ":kubernetes" in tag),
                    item["RepoTags"][0],
                ): item["Id"]
                for item in raw.get("images", [])
            }
        (output / "summary.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Kubernetes acceptance passed: {output}")


if __name__ == "__main__":
    main()
