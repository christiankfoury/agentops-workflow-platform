import json
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from time import monotonic, sleep

import pytest
from pydantic import ValidationError

from src.config import settings
from src.schemas.http_tool import HTTPDestination, HTTPOptions
from src.services import http_tool as http
from src.services.execution_control import AbortSignal
from src.services.graph_expressions import ExecutionError
from src.services.tool_effects import ToolFailure


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def do_GET(self):
            self.handle_call()

        def do_HEAD(self):
            self.handle_call()

        def do_POST(self):
            self.handle_call()

        def handle_call(self):
            path = self.path.split("?")[0]
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.server.calls.append((self.command, self.path, dict(self.headers), body))
            self.server.entered.set()
            code, headers = 200, {}
            content = {"value": "one"}
            if path.startswith("/status/"):
                code = int(path.rsplit("/", 1)[1])
            elif path == "/echo":
                content = {"value": self.headers.get("Authorization", "missing")}
            elif path == "/wrong-schema":
                content = {"value": 42}
            elif path in {"/redirect", "/external", "/metadata", "/loop"}:
                code = 302
                headers["Location"] = {
                    "/redirect": "/ok",
                    "/external": "http://example.invalid/",
                    "/metadata": "http://169.254.169.254/",
                    "/loop": "/loop",
                }[path]
            elif path in {"/write", "/lost", "/crash"}:
                key = self.headers.get("Idempotency-Key") or str(len(self.server.calls))
                fresh = key not in self.server.effects
                self.server.effects.setdefault(key, json.loads(body))
                content = self.server.effects[key]
                if (path == "/lost" and fresh) or path == "/crash":
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    self.close_connection = True
                    return
            payload = json.dumps(content).encode()
            if path == "/oversize":
                payload = b"x" * 2000
            elif path == "/invalid":
                payload = b"not-json"
            elif path == "/nan":
                payload = b'{"value":NaN}'
            elif path == "/delay":
                sleep(0.4)
            elif path == "/hold":
                self.server.release.wait(5)
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Set-Cookie", "secret-cookie")
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                try:
                    if path == "/drip":
                        for char in payload:
                            self.wfile.write(bytes([char]))
                            self.wfile.flush()
                            sleep(0.03)
                    else:
                        self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    fixture.calls, fixture.effects, fixture.entered = [], {}, Event()
    fixture.release = Event()
    thread = Thread(target=fixture.serve_forever, daemon=True)
    thread.start()
    fixture.origin = f"http://127.0.0.1:{fixture.server_port}"
    try:
        yield fixture
    finally:
        fixture.release.set()
        fixture.shutdown()
        fixture.server_close()
        thread.join(2)


def policy(server, **kwargs):
    return HTTPDestination(
        origin=server.origin,
        allow_plain_http=True,
        allowed_private_cidrs=["127.0.0.1/32"],
        **kwargs,
    )


def call(server, path="/ok", *, method="GET", arguments=None, control=None, timeout=2, **kwargs):
    return http.request(
        policy(server, **kwargs),
        HTTPOptions(destination="fixture", method=method, path=path),
        arguments=arguments or {},
        secret="",
        effect_key="stable-key",
        timeout_seconds=timeout,
        control=control or AbortSignal(),
    )


def test_reads_writes_and_only_structured_response_body(server):
    assert call(server, arguments={"value": "a&b"}) == {"status": 200, "body": {"value": "one"}}
    assert server.calls[0][1] == "/ok?value=a%26b"
    assert call(server, method="HEAD") == {"status": 200, "body": {}}
    assert call(server, "/oversize", method="HEAD", max_response_bytes=20) == {
        "status": 200,
        "body": {},
    }
    assert call(server, "/write", method="POST", arguments={"value": "two"})["body"] == {
        "value": "two"
    }
    assert len(server.effects) == 1
    assert "Cookie" not in server.calls[-1][2]


@pytest.mark.parametrize(
    "path,code",
    [
        ("/status/400", "tool_denied"),
        ("/status/403", "tool_denied"),
        ("/status/429", "tool_rate_limit"),
        ("/status/503", "tool_unavailable"),
        ("/invalid", "tool_response_invalid"),
        ("/nan", "tool_response_invalid"),
        ("/oversize", "tool_response_invalid"),
    ],
)
def test_errors_and_malformed_responses_are_sanitized(server, path, code):
    with pytest.raises(ToolFailure) as error:
        call(server, path, max_response_bytes=512)
    assert error.value.code == code and str(error.value) == code


def test_request_limit_and_nested_query_reject_before_io(server):
    for kwargs in [
        {"method": "POST", "arguments": {"value": "x" * 1000}, "max_request_bytes": 100},
        {"arguments": {"value": {"nested": "not-query"}}},
    ]:
        with pytest.raises(ToolFailure, match="tool_input_invalid"):
            call(server, **kwargs)
    assert server.calls == []


def test_redirects_are_bounded_same_origin_read_only_and_revalidated(server):
    assert call(server, "/redirect", max_redirects=1)["status"] == 200
    assert len(server.calls) == 2
    for path in ["/external", "/metadata", "/loop"]:
        with pytest.raises(ToolFailure, match="tool_denied"):
            call(server, path, max_redirects=1)
    before = len(server.calls)
    with pytest.raises(ToolFailure, match="tool_denied"):
        call(server, "/redirect", method="POST", max_redirects=1)
    assert len(server.calls) == before + 1


@pytest.mark.parametrize("path", ["/delay", "/drip"])
def test_absolute_deadline_includes_slow_response(server, path):
    start = monotonic()
    with pytest.raises(ToolFailure, match="tool_timeout"):
        call(server, path, timeout=0.1)
    assert monotonic() - start < 0.8


def test_abort_closes_inflight_response(server):
    control = AbortSignal()
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(call, server, "/delay", control=control, timeout=10)
        assert server.entered.wait(2)
        control.abort()
        with pytest.raises((ExecutionError, ToolFailure)):
            future.result(1)


@pytest.mark.parametrize(
    "address",
    [
        "169.254.169.254",
        "100.100.100.200",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fe80::1",
        "fd00:ec2::254",
        "64:ff9b::a9fe:a9fe",
        "2002:a9fe:a9fe::",
        "::ffff:169.254.169.254",
        "10.0.0.1",
        "127.0.0.1",
    ],
)
def test_unauthorized_networks_and_metadata_cannot_pass(address):
    public = HTTPDestination(origin="https://example.com")
    assert not http.allowed_address(address, public)
    if address in {"169.254.169.254", "fd00:ec2::254", "100.100.100.200"}:
        private = public.model_copy(
            update={"allowed_private_cidrs": [address + ("/128" if ":" in address else "/32")]}
        )
        assert not http.allowed_address(address, private)
    assert http.allowed_address("8.8.8.8", public)


def test_all_dns_answers_checked_and_connection_pins_validated_ip(server, monkeypatch):
    lookup = socket.getaddrinfo
    calls = []

    def addresses(host, port, **kwargs):
        calls.append(host)
        return lookup("127.0.0.1", port, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", addresses)
    server.origin = f"http://fixture.invalid:{server.server_port}"
    assert call(server)["status"] == 200
    assert calls == ["fixture.invalid"]  # No connect-time DNS lookup/rebinding.

    def mixed(host, port, **kwargs):
        return [*lookup("127.0.0.1", port, **kwargs), *lookup("169.254.169.254", port, **kwargs)]

    monkeypatch.setattr(socket, "getaddrinfo", mixed)
    with pytest.raises(ToolFailure, match="tool_denied"):
        call(server)
    assert len(server.calls) == 1


def test_dns_timeout_and_cancel_cannot_dispatch_after_late_lookup(server, monkeypatch):
    entered, release = Event(), Event()
    lookup = socket.getaddrinfo

    def slow(*args, **kwargs):
        entered.set()
        release.wait(2)
        return lookup(*args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", slow)
    try:
        with pytest.raises(ToolFailure, match="tool_timeout"):
            call(server, timeout=0.1)
        assert entered.is_set() and not server.calls
    finally:
        release.set()


def test_redirect_dns_is_checked_again_without_forwarding_credentials(server, monkeypatch):
    lookup, count = socket.getaddrinfo, 0

    def rebound(host, port, **kwargs):
        nonlocal count
        count += 1
        return lookup("127.0.0.1" if count == 1 else "169.254.169.254", port, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", rebound)
    with pytest.raises(ToolFailure, match="tool_denied"):
        http.request(
            policy(server, credential_alias="fixture", max_redirects=1),
            HTTPOptions(destination="fixture", path="/redirect"),
            arguments={},
            secret="fixture-only-secret",
            effect_key="read",
            timeout_seconds=2,
            control=AbortSignal(),
        )
    assert count == 2 and len(server.calls) == 1


def test_transport_ignores_proxy_environment_and_bounds_resolver_capacity(server, monkeypatch):
    from threading import BoundedSemaphore

    monkeypatch.setenv("HTTP_PROXY", "http://169.254.169.254:80")
    monkeypatch.setenv("HTTPS_PROXY", "http://169.254.169.254:80")
    assert call(server)["status"] == 200
    slots = BoundedSemaphore(1)
    slots.acquire()
    monkeypatch.setattr(http, "DNS_SLOTS", slots)
    with pytest.raises(ToolFailure, match="tool_unavailable"):
        call(server)
    assert len(server.calls) == 1


@pytest.mark.parametrize(
    "options",
    [
        {"path": "//evil.test"},
        {"path": "/\\evil.test"},
        {"path": "/\r\nHeader:x"},
        {"path": "/x?secret=y"},
        {"headers": {"Authorization": "forged"}},
        {"method": "CONNECT"},
    ],
)
def test_workflows_cannot_override_transport_headers_or_destinations(options):
    with pytest.raises(ValidationError):
        HTTPOptions(destination="fixture", **options)


def test_tenant_destination_method_and_credential_policy(server, monkeypatch):
    from types import SimpleNamespace

    contract = SimpleNamespace(options={"destination": "fixture", "method": "POST"})
    raw = policy(server, methods={"POST"}, credential_alias="fixture").model_dump(mode="json")
    monkeypatch.setattr(settings, "http_tool_destinations", {"tenant/fixture": raw})
    for organization, credential in [
        ("other", SimpleNamespace(source_alias="fixture")),
        ("tenant", None),
        ("tenant", SimpleNamespace(source_alias="other")),
    ]:
        with pytest.raises(ToolFailure, match="tool_denied"):
            http.adapter(contract, organization, credential)
    contract.options["method"] = "GET"
    with pytest.raises(ToolFailure, match="tool_denied"):
        http.adapter(contract, "tenant", SimpleNamespace(source_alias="fixture"))
    assert not server.calls


def test_provider_idempotency_replay_retention_and_private_policy_binding(server, monkeypatch):
    from types import SimpleNamespace

    contract = SimpleNamespace(
        options={"destination": "fixture", "method": "POST", "path": "/lost"}
    )
    raw = policy(server, methods={"POST"}, idempotency_retention_seconds=120).model_dump(
        mode="json"
    )
    monkeypatch.setattr(settings, "http_tool_destinations", {"tenant/fixture": raw})
    adapter = http.adapter(contract, "tenant", None)
    kwargs = dict(
        arguments={"value": "one"},
        secret="",
        effect_key="one-effect",
        timeout_seconds=2,
        control=AbortSignal(),
        effect_age_seconds=0,
    )
    with pytest.raises(ToolFailure, match="tool_unavailable"):
        adapter.invoke(**kwargs)
    assert adapter.reconcile(**kwargs).result["body"] == {"value": "one"}
    assert len(server.effects) == 1 and len(server.calls) == 2
    # Worker wall-clock rollback must not extend provider retention. Old code
    # based on local datetime and this timestamp would replay an expired key.
    kwargs["effect_created_at"] = datetime.now(UTC) - timedelta(seconds=121)
    kwargs["effect_age_seconds"] = 121

    class SkewedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) - timedelta(hours=1)

    monkeypatch.setattr(http, "datetime", SkewedClock, raising=False)
    assert adapter.reconcile(**kwargs).outcome == "unknown" and len(server.calls) == 2
    kwargs["effect_age_seconds"] = -1
    assert adapter.reconcile(**kwargs).outcome == "unknown" and len(server.calls) == 2
    raw["methods"] = ["POST", "GET"]
    changed = http.adapter(contract, "tenant", None)
    assert changed.policy_identity != adapter.policy_identity
    raw["methods"].reverse()
    assert changed.policy_identity == http.adapter(contract, "tenant", None).policy_identity


def test_tls_verifies_original_hostname_after_ip_pinning(server, monkeypatch, tmp_path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), False)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = tmp_path / "cert.pem", tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    create = ssl.create_default_context
    monkeypatch.setattr(ssl, "create_default_context", lambda: create(cafile=str(cert_path)))
    # Force IPv4 so both Windows and Linux use this fixture's listener.
    lookup = socket.getaddrinfo
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda host, port, **kw: lookup("127.0.0.1", port, **kw)
    )
    server.origin = f"https://localhost:{server.server_port}"
    assert call(server)["status"] == 200
    server.origin = f"https://wrong.invalid:{server.server_port}"
    with pytest.raises(ToolFailure, match="tool_unavailable"):
        call(server)
    assert len(server.calls) == 1
