"""Controlled loopback writes and an exclusively owned PostgreSQL outage target."""

import json
import shutil
import socket
import subprocess
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.database import Base
from src.models.identity import Organization
from src.models.tenant import DEFAULT_ORGANIZATION_ID


def wait_for(predicate, seconds=30):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        if predicate():
            return
        sleep(0.02)
    raise TimeoutError("Disposable fixture did not reach the requested boundary")


@pytest.fixture
def sink():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            supplied = self.headers.get("Idempotency-Key")
            with self.server.lock:
                key = supplied or f"unkeyed-{len(self.server.calls) + 1}"
                fresh = key not in self.server.effects
                self.server.calls.append({"path": self.path, "key": supplied, "body": body})
                self.server.effects.setdefault(key, body)
                assert self.server.effects[key] == body
            if self.path == "/timeout" and fresh:
                sleep(0.7)  # Contract timeout is 0.2s; the effect already exists.
            payload = json.dumps(body).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except OSError:
                pass  # Expected when the timed-out client has closed its socket.

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.calls, server.effects, server.lock = [], {}, Lock()
    server.origin = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, stderr=subprocess.STDOUT).strip()


@contextmanager
def outage_database():
    if not shutil.which("docker"):
        pytest.skip("Docker is required for the real PostgreSQL outage scenario")
    identity = uuid4().hex
    name = "agentops-phase99-" + identity
    # An unspecified Docker host port can change on stop/start. Reserve a free
    # loopback port number and explicitly retain that endpoint for this container.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        requested_port = probe.getsockname()[1]
    container = docker(
        "run",
        "--detach",
        "--name",
        name,
        "--label",
        f"agentops.phase99={identity}",
        "--memory",
        "512m",
        "--cpus",
        "2",
        "--publish",
        f"127.0.0.1:{requested_port}:5432",
        "--env",
        "POSTGRES_USER=fault_fixture",
        "--env",
        "POSTGRES_PASSWORD=fault_fixture",
        "--env",
        "POSTGRES_DB=fault_fixture",
        "postgres:16-alpine",
    )
    engine = None

    def owned(action):
        info = json.loads(docker("inspect", container))[0]
        assert info["Name"] == "/" + name
        assert info["Config"]["Labels"]["agentops.phase99"] == identity
        assert action in {"stop", "start", "remove"}
        return docker(
            *(
                {
                    "stop": ["stop", "--time", "1"],
                    "start": ["start"],
                    "remove": ["rm", "--force", "--volumes"],
                }[action]
            ),
            container,
        )

    try:
        info = json.loads(docker("inspect", container))[0]
        port = info["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
        url = f"postgresql://fault_fixture:fault_fixture@127.0.0.1:{port}/fault_fixture"
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 2})

        def ready():
            try:
                with engine.connect() as conn:
                    return conn.scalar(text("select 1")) == 1
            except Exception:
                return False

        wait_for(ready, 60)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(Organization(id=DEFAULT_ORGANIZATION_ID, name="Disposable outage fixture"))
            db.commit()
        yield (
            engine,
            owned,
            ready,
            {"container": container, "container_name": name, "image": info["Image"]},
        )
    finally:
        if engine is not None:
            engine.dispose()
        owned("remove")
