"""Download versioned local CLIs with official SHA-256 checks; never change PATH."""

import hashlib
import json
import platform
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / ".local/kubernetes"
KIND_VERSION = "v0.33.0"
KUBERNETES_VERSION = "v1.37.0"
NODE_IMAGE = (
    "kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5"
)


def download(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def install():
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "darwin"}[platform.system()]
    arch = {"AMD64": "amd64", "x86_64": "amd64", "arm64": "arm64", "aarch64": "arm64"}[
        platform.machine()
    ]
    suffix = ".exe" if system == "windows" else ""
    base = f"https://github.com/kubernetes-sigs/kind/releases/download/{KIND_VERSION}"
    kind_url = f"{base}/kind-{system}-{arch}"
    kubectl_url = (
        f"https://dl.k8s.io/release/{KUBERNETES_VERSION}/bin/{system}/{arch}/kubectl{suffix}"
    )
    LOCAL.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, version, url, checksum_url in [
        ("kind", KIND_VERSION, kind_url, kind_url + ".sha256sum"),
        ("kubectl", KUBERNETES_VERSION, kubectl_url, kubectl_url + ".sha256"),
    ]:
        expected = download(checksum_url).decode().split()[0].lower()
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise RuntimeError("Invalid official checksum response")
        target = LOCAL / f"{name}-{version}{suffix}"
        content = target.read_bytes() if target.exists() else download(url)
        if hashlib.sha256(content).hexdigest() != expected:
            raise RuntimeError(f"Checksum mismatch for {name}; existing files were preserved")
        if not target.exists():
            target.write_bytes(content)
            target.chmod(0o755)
        result[name] = {"path": str(target), "version": version, "url": url, "sha256": expected}
        print(f"Verified {name} {version} ({system}/{arch})")
    (LOCAL / "tools.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    install()
