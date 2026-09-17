"""Load explicitly supported mounted secrets before application modules import."""

import os
import socket
import sys
from pathlib import Path
from uuid import uuid4


def load_secrets():
    for name in (
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "TOOL_CREDENTIAL_VALUES",
        "WEBHOOK_SECRET_VALUES",
    ):
        path = os.environ.get(f"{name}_FILE")
        if path:
            if os.environ.get(name):
                raise RuntimeError(f"Configure either {name} or {name}_FILE")
            os.environ[name] = Path(path).read_text(encoding="utf-8").strip()


if __name__ == "__main__":
    load_secrets()
    if sys.argv[1:4] == ["python", "-m", "src.worker"]:
        # Replace stale readiness before Python imports the worker runtime.
        identity = f"{socket.gethostname()[:64]}:{uuid4().hex}"
        os.environ["WORKER_INSTANCE_ID"] = identity
        Path("/tmp/worker-identity").write_text(identity, encoding="utf-8")
    os.execvp(sys.argv[1], sys.argv[1:])
