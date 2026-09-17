"""Operations restricted to this repository's disposable kind cluster."""

import argparse
import base64
import copy
import json
import secrets
import subprocess
import time

from tools import LOCAL, NODE_IMAGE, ROOT

CLUSTER = "agentops-phase101"
NAMESPACE = "agentops"


def command(*args, stdin=None, timeout=300):
    result = subprocess.run(
        [str(arg) for arg in args],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=timeout,
    )
    if result.returncode:
        # Input may contain Secret data. Never include it or stdout in errors.
        raise RuntimeError(f"Command failed: {args}: {result.stderr[-2000:]}")
    return result.stdout


def binary(name):
    return json.loads((LOCAL / "tools.json").read_text())[name]["path"]


def kubectl(*args, stdin=None, timeout=300):
    return command(
        binary("kubectl"),
        "--kubeconfig",
        LOCAL / "kubeconfig",
        "--context",
        f"kind-{CLUSTER}",
        *args,
        stdin=stdin,
        timeout=timeout,
    )


def assert_owned():
    nodes = json.loads(command("docker", "inspect", f"{CLUSTER}-control-plane"))
    assert nodes[0]["Config"]["Labels"]["io.x-k8s.kind.cluster"] == CLUSTER
    config = json.loads(kubectl("config", "view", "--minify", "-o", "json"))
    assert config["clusters"][0]["cluster"]["server"].startswith("https://127.0.0.1:")


def render(profile="local"):
    yaml = command(binary("kubectl"), "kustomize", ROOT / "deploy/kubernetes" / profile)
    stream = kubectl(
        "create", "--dry-run=client", "--validate=false", "-f", "-", "-o", "json", stdin=yaml
    ).strip()
    result = []
    decoder = json.JSONDecoder()
    while stream:
        item, end = decoder.raw_decode(stream)
        result.extend(item["items"] if item["kind"] == "List" else [item])
        stream = stream[end:].lstrip()
    return result


def apply(items, dry_run=False):
    if not items:
        return ""
    return kubectl(
        "apply",
        *(["--dry-run=server"] if dry_run else []),
        "-f",
        "-",
        stdin=json.dumps({"apiVersion": "v1", "kind": "List", "items": items}),
    )


def secret(name, files, namespace=NAMESPACE):
    item = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": name, "namespace": namespace},
        "type": "kubernetes.io/tls" if name == "platform-tls" else "Opaque",
        "data": {key: base64.b64encode(value).decode() for key, value in files.items()},
    }
    # Do not overwrite an existing installation's credentials on rerun.
    existing = kubectl("-n", namespace, "get", "secret", name, "--ignore-not-found", "-o", "name")
    if not existing.strip():
        kubectl("create", "-f", "-", stdin=json.dumps(item))


def provision_secrets():
    fixture = ROOT / ".local/production"
    password = secrets.token_urlsafe(32)
    secret(
        "database",
        {
            "password": password.encode(),
            "database_url": f"postgresql://agentops:{password}@db:5432/agentops".encode(),
        },
    )
    secret("identity", {"oidc_client_secret": b""})
    secret("fixture-ca", {"ca.crt": (fixture / "ca.crt").read_bytes()})
    secret("fixture-signing", {"oidc.key": (fixture / "oidc.key").read_bytes()})
    for namespace in [NAMESPACE, "agentops-ingress"]:
        secret(
            "platform-tls",
            {name: (fixture / name).read_bytes() for name in ["tls.crt", "tls.key"]},
            namespace,
        )


def job(template, name, args=None):
    item = copy.deepcopy(template)
    item["metadata"]["name"] = name
    if args:
        item["spec"]["template"]["spec"]["containers"][0]["args"] = args
    kubectl("create", "-f", "-", stdin=json.dumps(item))
    kubectl(
        "-n",
        NAMESPACE,
        "wait",
        "--for=condition=complete",
        f"job/{name}",
        "--timeout=200s",
        timeout=220,
    )
    return kubectl("-n", NAMESPACE, "logs", f"job/{name}")


def deploy():
    assert_owned()
    items = render()
    foundation = {
        "Namespace",
        "ServiceAccount",
        "Role",
        "RoleBinding",
        "ClusterRole",
        "ClusterRoleBinding",
        "IngressClass",
        "ConfigMap",
        "Service",
    }
    print(apply([item for item in items if item["kind"] in foundation]), flush=True)
    provision_secrets()
    # Validate both complete profiles against the actual API schema. Hosted is not applied.
    print(apply(items, dry_run=True), flush=True)
    print(apply(render("hosted"), dry_run=True), flush=True)
    print(apply([item for item in items if item["kind"] == "StatefulSet"]), flush=True)
    kubectl("-n", NAMESPACE, "rollout", "status", "statefulset/db", "--timeout=600s", timeout=660)
    migration = next(item for item in items if item["kind"] == "Job")
    name = f"migrate-{int(time.time())}"
    print(job(migration, name), flush=True)
    history = json.loads(kubectl("-n", NAMESPACE, "get", "jobs", "-o", "json"))["items"]
    first_migration = min(
        (
            item
            for item in history
            if item["metadata"]["name"].startswith("migrate-")
            and item["status"].get("succeeded") == 1
        ),
        key=lambda item: item["metadata"]["creationTimestamp"],
    )["metadata"]["name"]
    workloads = [item for item in items if item["kind"] in {"Deployment", "Ingress", "CronJob"}]
    print(apply(workloads), flush=True)
    for item in workloads:
        if item["kind"] == "Deployment":
            print(
                kubectl(
                    "-n",
                    item["metadata"]["namespace"],
                    "rollout",
                    "status",
                    "deployment/" + item["metadata"]["name"],
                    "--timeout=600s",
                    timeout=660,
                ),
                flush=True,
            )
    (LOCAL / "deployment.json").write_text(
        json.dumps(
            {
                "cluster": CLUSTER,
                "node_image": NODE_IMAGE,
                "migration_job": name,
                "first_migration_job": first_migration,
                "base_commit": command("git", "rev-parse", "HEAD").strip(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "check"])
    action = parser.parse_args().action
    if action == "deploy":
        deploy()
    else:
        assert_owned()
        print(kubectl("get", "nodes", "-o", "wide"))
