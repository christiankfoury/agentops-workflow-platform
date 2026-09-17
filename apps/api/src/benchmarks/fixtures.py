"""Bounded graphs and an independent loopback effect sink for reproducible runs."""

import json
import random
import re
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread

from pydantic import SecretStr
from sqlalchemy.orm import Session

from src.config import settings
from src.models.identity import Membership, User
from src.models.tenant import DEFAULT_ORGANIZATION_ID as OWNER
from src.schemas.http_tool import HTTPDestination
from src.schemas.tool import ToolContract, ToolCreate
from src.schemas.workflow_definition import DefinitionCreate
from src.services import tool_catalog, workflow_definitions
from src.services.identity import Principal
from src.services.tenancy import bind_tenant


def obj(**fields):
    return {"type": "object", "properties": fields, "required": list(fields)}


NUMBER, STRING = {"type": "number"}, {"type": "string"}
VALUE = obj(value=NUMBER)
REVIEW = obj(
    approved={"type": "boolean"},
    quality_score=NUMBER,
    issues={"type": "array", "items": obj(claim=STRING, problem=STRING, severity=STRING)},
    retry_recommended={"type": "boolean"},
)
APPROVED = {"approved": True, "quality_score": 1, "issues": [], "retry_recommended": False}
ENVELOPE = obj(node_id=STRING, tool_id=STRING, version={"type": "integer"}, arguments=VALUE)


def literal(value):
    return {"op": "literal", "value": value}


def ref(field, node=None):
    return {
        "op": "ref",
        "ref": {
            "source": "node" if node else "input",
            "path": field.split("."),
            **({"node_id": node} if node else {}),
        },
    }


def edge(source, target, label=None):
    return {"source": source, "target": target, **({"label": label} if label else {})}


def identity(name, value):
    return {
        "id": name,
        "type": "code",
        "config": {"handler": "builtin.identity", "version": 1},
        "input_schema": VALUE,
        "output_schema": VALUE,
        "inputs": {"value": value},
    }


def graphs(tool_id):
    condition = {
        "entry_node": "choice",
        "input_schema": VALUE,
        "nodes": [
            {
                "id": "choice",
                "type": "condition",
                "config": {
                    "cases": [
                        {
                            "label": "positive",
                            "when": {
                                "op": "gte",
                                "args": [ref("value"), literal(0)],
                            },
                        }
                    ],
                    "default": "negative",
                },
            },
            identity("positive", ref("value")),
            identity("negative", ref("value")),
        ],
        "edges": [edge("choice", "positive", "positive"), edge("choice", "negative", "negative")],
    }
    parallel = {
        "entry_node": "fork",
        "input_schema": VALUE,
        "output_schema": obj(left=NUMBER, right=NUMBER),
        "outputs": {"left": ref("left", "join"), "right": ref("right", "join")},
        "nodes": [
            {
                "id": "fork",
                "type": "parallel",
                "config": {
                    "mode": "fork",
                    "join_node": "join",
                    "branches": [
                        {"name": "left", "entry_node": "left"},
                        {"name": "right", "entry_node": "right"},
                    ],
                },
            },
            identity("left", ref("value")),
            identity("right", ref("value")),
            {
                "id": "join",
                "type": "parallel",
                "config": {
                    "mode": "join",
                    "fork_node": "fork",
                },
                "input_schema": obj(left=NUMBER, right=NUMBER),
                "output_schema": obj(left=NUMBER, right=NUMBER),
                "inputs": {"left": ref("value", "left"), "right": ref("value", "right")},
            },
        ],
        "edges": [
            edge("fork", "left", "left"),
            edge("fork", "right", "right"),
            edge("left", "join"),
            edge("right", "join"),
        ],
    }
    sink = {
        "entry_node": "gate",
        "input_schema": obj(payload=ENVELOPE),
        "nodes": [
            {
                "id": "gate",
                "type": "approval",
                "config": {"deadline_seconds": 3600},
                "input_schema": obj(payload=ENVELOPE, review=REVIEW),
                "output_schema": ENVELOPE,
                "inputs": {"payload": ref("payload"), "review": literal(APPROVED)},
            },
            {
                "id": "action",
                "type": "tool",
                "input_schema": VALUE,
                "output_schema": obj(status={"type": "integer"}, body=VALUE),
                "inputs": {"value": ref("arguments.value", "gate")},
                "config": {"tool_id": str(tool_id), "version": 1, "approval_node": "gate"},
            },
        ],
        "edges": [edge("gate", "action")],
    }
    return {"condition": condition, "parallel": parallel, "sink": sink}


def workload(count, seed, offset=0):
    rng = random.Random(seed)
    kinds = ["condition", "parallel", "sink"]
    order = [kinds[index % 3] for index in range(count)]
    rng.shuffle(order)
    return [
        {
            "index": offset + index,
            "kind": kind,
            "value": (offset + index + 1) * (-1 if rng.randrange(2) else 1),
        }
        for index, kind in enumerate(order)
    ]


class Sink(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), SinkHandler)
        self.lock, self.effects, self.calls, self.conflicts = Lock(), {}, [], 0
        self.origin = f"http://127.0.0.1:{self.server_port}"


class SinkHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        key = self.headers.get("Idempotency-Key", "")
        size = int(self.headers.get("Content-Length", "0"))
        if self.path != "/effects" or not re.fullmatch(r"[0-9a-f]{64}", key) or not 0 < size < 2048:
            self.send_error(400)
            return
        body = json.loads(self.rfile.read(size))
        with self.server.lock:
            self.server.calls.append({"key": key, "body": body})
            conflict = key in self.server.effects and self.server.effects[key] != body
            if conflict:
                self.server.conflicts += 1
            else:
                self.server.effects.setdefault(key, body)
        encoded = json.dumps(body).encode()
        self.send_response(409 if conflict else 200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


@contextmanager
def fixture_settings(sink):
    """Only use in the dedicated benchmark process, never alongside an API server."""
    overrides = {
        "identity_enabled": True,
        "openai_api_key": SecretStr(""),
        "http_tool_destinations": {
            f"{OWNER}/benchmark": HTTPDestination(
                origin=sink.origin,
                methods={"POST"},
                allow_plain_http=True,
                allowed_private_cidrs=["127.0.0.1/32"],
                idempotency_retention_seconds=86400,
                max_request_bytes=2048,
                max_response_bytes=2048,
            ).model_dump(mode="json")
        },
    }
    previous = {key: getattr(settings, key) for key in overrides}
    thread = Thread(target=sink.serve_forever, daemon=True)
    thread.start()
    try:
        for key, value in overrides.items():
            setattr(settings, key, value)
        yield
    finally:
        sink.shutdown()
        sink.server_close()
        thread.join(5)
        for key, value in previous.items():
            setattr(settings, key, value)


@contextmanager
def session(engine, principal):
    with Session(engine, expire_on_commit=False) as db:
        bind_tenant(db, OWNER)
        db.info["principal"] = principal
        yield db


def prepare(engine):
    with Session(engine) as db:
        user = User(
            issuer="https://benchmark.invalid",
            subject="fixture-admin",
            display_name="Synthetic benchmark approver",
        )
        db.add(user)
        db.flush()
        db.add(Membership(user_id=user.id, organization_id=OWNER, role="admin"))
        db.commit()
        principal = Principal("admin", user.id, OWNER)
    with session(engine, principal) as db:
        tool = tool_catalog.create(
            db,
            ToolCreate(
                name="Loopback benchmark sink",
                contract=ToolContract(
                    adapter="http",
                    input_schema=VALUE,
                    output_schema=obj(status={"type": "integer"}, body=VALUE),
                    side_effecting=True,
                    options={"destination": "benchmark", "method": "POST", "path": "/effects"},
                ),
            ),
        )
        definitions = {}
        for kind, graph in graphs(tool.definition_id).items():
            definition = workflow_definitions.create_definition(
                db,
                DefinitionCreate(name=f"Benchmark {kind}", graph=graph),
            )
            published = workflow_definitions.publish(db, definition.id, 1)
            definitions[kind] = {"definition_id": definition.id, "version_id": published.id}
        return principal, definitions, str(tool.definition_id)


def run_input(item, tool_id):
    if item["kind"] != "sink":
        return {"value": item["value"]}
    return {
        "payload": {
            "node_id": "action",
            "tool_id": tool_id,
            "version": 1,
            "arguments": {"value": item["value"]},
        }
    }
