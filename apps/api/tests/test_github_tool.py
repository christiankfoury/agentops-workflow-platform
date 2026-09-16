import json
import socket
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError

from src.config import settings
from src.models.tenant import DEFAULT_ORGANIZATION_ID as ORGANIZATION
from src.services import github_tool as github
from src.services.execution_control import AbortSignal
from src.services.graph_expressions import ExecutionError
from src.services.tool_effects import ToolFailure

SECRET = "github-fixture-secret"
CONTENT = {"title": "Investigate fixture", "body": "Approved details"}


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            self.handle_call()

        def do_POST(self):
            self.handle_call()

        def handle_call(self):
            body = json.loads(
                self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}"
            )
            self.server.calls.append((self.command, self.path, dict(self.headers), body))
            status, headers = 200, {}
            if self.server.error:
                status, payload, headers = self.server.error
            elif self.command == "POST":
                payload = {
                    **body,
                    "number": len(self.server.issues) + 1,
                    "state": "open",
                    "user": {"id": 7},
                }
                self.server.issues.append(payload)
                if self.server.lost:
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                status = 201
            else:
                query = parse_qs(urlsplit(self.path).query)
                page, count = int(query.get("page", [1])[0]), int(query.get("per_page", [10])[0])
                payload = deepcopy(self.server.issues[(page - 1) * count : page * count])
                if self.server.response is not None:
                    payload = self.server.response
            encoded = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(encoded)

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    fixture.calls, fixture.issues, fixture.error = [], [], None
    fixture.lost, fixture.response = False, None
    fixture.origin = f"http://127.0.0.1:{fixture.server_port}"
    thread = Thread(target=fixture.serve_forever, daemon=True)
    thread.start()
    try:
        yield fixture
    finally:
        fixture.shutdown()
        fixture.server_close()
        thread.join(2)


def configure(server, monkeypatch, **changes):
    raw = {
        "owner": "acme",
        "repo": "work",
        "credential_alias": "github-fixture",
        "actor_id": 7,
        "operations": ["read_issues", "create_issue"],
        "origin": server.origin,
        "allow_plain_http": True,
        "allowed_private_cidrs": ["127.0.0.1/32"],
        **changes,
    }
    monkeypatch.setattr(settings, "github_tool_repositories", {f"{ORGANIZATION}/work": raw})
    return raw


def adapter(server, monkeypatch, *, write=False, organization=ORGANIZATION, **changes):
    configure(server, monkeypatch, **changes)
    return github.adapter(
        SimpleNamespace(
            options={"repository": "work", "operation": "create_issue" if write else "read_issues"}
        ),
        organization,
        SimpleNamespace(source_alias="github-fixture"),
    )


def invoke(adapter, *, reconcile=False, arguments=None, **changes):
    return (adapter.reconcile if reconcile else adapter.invoke)(
        **{
            "arguments": arguments or {},
            "secret": SECRET,
            "effect_key": "stable-effect",
            "timeout_seconds": 3,
            "control": AbortSignal(),
            **changes,
        },
    )


def test_read_pagination_filters_pull_requests_and_pins_protocol(server, monkeypatch):
    for number in range(1, 4):
        server.issues.append(
            {"number": number, "title": f"Issue {number}", "body": None, "state": "open"}
        )
    server.issues[1]["pull_request"] = {"url": "untrusted"}
    read = adapter(server, monkeypatch, max_pages=2)
    result = invoke(read, arguments={"per_page": 2})
    assert [value["number"] for value in result["issues"]] == [1]
    assert result["next_page"] == 2 and not result["page_limit_reached"]
    assert result["issues"][0]["url"] == "https://github.com/acme/work/issues/1"
    assert invoke(read, arguments={"per_page": 1, "page": 2}) == {
        "issues": [],
        "next_page": None,
        "page_limit_reached": True,
    }
    method, path, headers, _ = server.calls[0]
    assert method == "GET" and path.startswith("/repos/acme/work/issues?")
    assert headers["Authorization"] == "Bearer " + SECRET
    assert headers["X-GitHub-Api-Version"] == "2026-03-10"
    with pytest.raises(ToolFailure, match="tool_input_invalid"):
        invoke(read, arguments={"page": 3})


def test_lost_create_reconciles_without_another_post(server, monkeypatch):
    write = adapter(server, monkeypatch, write=True)
    server.lost = True
    with pytest.raises(ToolFailure, match="tool_unavailable") as error:
        invoke(write, arguments=CONTENT)
    assert error.value.uncertain
    suffix = "\n\n<!-- agentops:" + github.marker("stable-effect", SECRET) + " -->"
    assert server.issues[0]["body"] == CONTENT["body"] + suffix
    result = invoke(write, reconcile=True, arguments=CONTENT)
    assert result.outcome == "succeeded" and result.result["issue"]["body"] == CONTENT["body"]
    assert [call[0] for call in server.calls] == ["POST", "GET"]
    assert "Idempotency-Key" not in server.calls[0][2]


@pytest.mark.parametrize("change", ["missing", "author", "title", "duplicate", "marker"])
def test_ambiguous_or_forged_reconciliation_never_claims_absence(server, monkeypatch, change):
    write = adapter(server, monkeypatch, write=True)
    invoke(write, arguments=CONTENT)
    if change == "missing":
        server.issues.clear()
    elif change == "duplicate":
        server.issues.append({**server.issues[0], "number": 2})
    elif change == "author":
        server.issues[0]["user"]["id"] = 8
    elif change == "title":
        server.issues[0]["title"] = "different"
    else:
        server.issues[0]["body"] = CONTENT["body"] + "\n\n<!-- agentops:forged -->"
    assert invoke(write, reconcile=True, arguments=CONTENT).outcome == "unknown"
    assert sum(call[0] == "POST" for call in server.calls) == 1


@pytest.mark.parametrize(
    "status,headers,message,code,uncertain,delay",
    [
        (401, {}, "expired secret", "tool_denied", False, None),
        (403, {}, "denied secret", "tool_denied", False, None),
        (404, {}, "missing", "tool_denied", False, None),
        (422, {}, "invalid", "tool_input_invalid", False, None),
        (503, {}, "unavailable", "tool_unavailable", True, None),
        (429, {"Retry-After": "120"}, "rate", "tool_rate_limit", False, 120),
        (403, {}, "secondary rate limit", "tool_rate_limit", False, 60),
        (403, {"Retry-After": "bad"}, "rate", "tool_rate_limit", False, 3600),
    ],
)
def test_provider_error_taxonomy_and_backoff(
    server, monkeypatch, status, headers, message, code, uncertain, delay
):
    read = adapter(server, monkeypatch)
    server.error = status, {"message": message}, headers
    with pytest.raises(ToolFailure) as error:
        invoke(read)
    assert error.value.code == code and error.value.uncertain == uncertain
    assert error.value.retry_after_seconds == delay and str(error.value) == code


@pytest.mark.parametrize("arguments", [{"owner": "foreign"}, {"page": True}, {"per_page": 101}])
def test_read_input_cannot_expand_scope(server, monkeypatch, arguments):
    read = adapter(server, monkeypatch)
    with pytest.raises(ToolFailure, match="tool_input_invalid"):
        invoke(read, arguments=arguments)
    assert not server.calls


def test_tenant_operation_credential_and_marker_injection_denied(server, monkeypatch):
    with pytest.raises(ToolFailure, match="tool_denied"):
        adapter(server, monkeypatch, organization="foreign")
    with pytest.raises(ToolFailure, match="tool_denied"):
        adapter(server, monkeypatch, write=True, operations=["read_issues"])
    write = adapter(server, monkeypatch, write=True)
    with pytest.raises(ToolFailure, match="tool_input_invalid"):
        invoke(write, arguments={"title": "test", "body": "<!-- agentops:forged -->"})
    with pytest.raises(ToolFailure, match="tool_denied"):
        github.adapter(
            SimpleNamespace(options={"repository": "work", "operation": "read_issues"}),
            ORGANIZATION,
            SimpleNamespace(source_alias="foreign"),
        )
    assert not server.calls


@pytest.mark.parametrize(
    "response",
    [
        {},
        [None],
        [{"number": True, "title": "bad", "state": "open"}],
        [{"number": 1, "title": "bad", "state": []}],
        [{"number": 1, "title": "big", "body": "x" * 130000, "state": "open"}],
    ],
)
def test_malformed_and_oversized_results_are_rejected(server, monkeypatch, response):
    read = adapter(server, monkeypatch)
    server.response = response
    with pytest.raises(ToolFailure, match="tool_response_invalid"):
        invoke(read)


def test_primary_rate_reset_uses_provider_date_and_excessive_delays_fail_closed():
    headers = {
        "Date": "Mon, 01 Jan 2024 00:00:00 GMT",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1704067325",
    }

    def failure():
        response = SimpleNamespace(
            status=403,
            getheader=lambda key, default=None: headers.get(key, default),
            read1=BytesIO(b"{}").read1,
        )
        return github.response_error(response, SimpleNamespace(remaining=lambda: 1))

    assert failure().retry_after_seconds == 125
    headers["Retry-After"] = "999999"
    assert failure().code == "tool_denied"


def test_reconciliation_cancellation_stops_pagination(server, monkeypatch):
    write = adapter(server, monkeypatch, write=True)
    server.issues = [
        {"number": n, "title": "Unrelated", "body": "", "state": "open"} for n in range(1, 11)
    ]
    control = AbortSignal()
    original = github.http_tool.request

    def abort_after_page(*args, **kwargs):
        result = original(*args, **kwargs)
        control.abort()
        return result

    monkeypatch.setattr(github.http_tool, "request", abort_after_page)
    with pytest.raises(ExecutionError, match="cancelled"):
        invoke(write, reconcile=True, arguments=CONTENT, control=control)
    assert len(server.calls) == 1 and server.calls[0][0] == "GET"


@pytest.mark.parametrize("timing", ["NaN", "-1", "Infinity"])
def test_malformed_numeric_backoff_uses_conservative_fallback(timing):
    headers = {"Retry-After": timing}
    response = SimpleNamespace(
        status=429, getheader=lambda key, default=None: headers.get(key, default)
    )
    assert github.response_error(response, None).retry_after_seconds == 3600


def test_create_policy_requires_explicit_reconciliation_read_permission(server, monkeypatch):
    with pytest.raises(ValidationError):
        adapter(server, monkeypatch, write=True, operations=["create_issue"])
    assert not server.calls
