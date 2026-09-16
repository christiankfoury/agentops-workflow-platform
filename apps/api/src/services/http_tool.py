"""Bounded HTTP transport with vetted-IP connections and no implicit redirects/retries."""

import http.client
import json
import socket
import ssl
from datetime import UTC, datetime
from ipaddress import ip_address, ip_network
from threading import BoundedSemaphore, Event, Lock, Thread, Timer
from time import monotonic
from urllib.parse import urlencode, urljoin, urlsplit

from src.config import settings
from src.schemas.http_tool import HTTPDestination, HTTPOptions, valid_path
from src.schemas.tool import bounded
from src.services.tool_effects import Reconciliation, ToolAdapter, ToolFailure, digest

DNS_SLOTS = BoundedSemaphore(8)
FORBIDDEN_NETWORKS = tuple(
    ip_network(value)
    for value in [
        "169.254.0.0/16",
        "100.100.100.200/32",
        "fe80::/10",
        "fd00:ec2::254/128",
        "64:ff9b::/96",
        "64:ff9b:1::/48",
        "2002::/16",
        "2001::/32",
    ]
)


def destination(organization_id, options):
    options = HTTPOptions.model_validate(options)
    raw = settings.http_tool_destinations.get(f"{organization_id}/{options.destination}")
    if raw is None:
        raise ToolFailure("tool_denied", uncertain=False)
    policy = HTTPDestination.model_validate(raw)
    if options.method not in policy.methods:
        raise ToolFailure("tool_denied", uncertain=False)
    return options, policy


def allowed_address(value, policy):
    address = ip_address(value)
    if getattr(address, "ipv4_mapped", None):
        return allowed_address(str(address.ipv4_mapped), policy)
    if (
        address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
        or any(
            address in network
            for network in FORBIDDEN_NETWORKS
            if network.version == address.version
        )
    ):
        return False
    return address.is_global or any(
        address in ip_network(cidr)
        for cidr in policy.allowed_private_cidrs
        if ip_network(cidr).version == address.version
    )


class Budget:
    def __init__(self, seconds, control):
        self.end = monotonic() + seconds
        self.control = control
        self.lock = Lock()
        self.sockets = []
        self.closed = False
        self.unregister = control.on_abort(self.close)
        self.timer = Timer(max(0, seconds), self.close)
        self.timer.daemon = True
        self.timer.start()

    def remaining(self):
        self.control.raise_if_aborted()
        remaining = self.end - monotonic()
        if remaining <= 0 or self.closed:
            raise ToolFailure("tool_timeout")
        return remaining

    def track(self, sock):
        with self.lock:
            self.sockets.append(sock)
            if self.closed:
                sock.close()
        self.remaining()
        return sock

    def close(self):
        with self.lock:
            self.closed = True
            for sock in self.sockets:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()

    def finish(self):
        self.timer.cancel()
        self.unregister()
        self.close()


def resolve(host, port, policy, budget):
    # DNS cannot be cancelled portably. Bound outstanding daemon resolvers; timed-out
    # resolution can never initiate a connection and releases its slot on return.
    if not DNS_SLOTS.acquire(blocking=False):
        raise ToolFailure("tool_unavailable", uncertain=False)
    done, result = Event(), []

    def lookup():
        try:
            result.extend(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except OSError:
            pass
        finally:
            DNS_SLOTS.release()
            done.set()

    Thread(target=lookup, daemon=True).start()
    while not done.wait(min(0.05, budget.remaining())):
        pass
    budget.remaining()
    if not result:
        raise ToolFailure("tool_unavailable", uncertain=False)
    if any(not allowed_address(item[4][0], policy) for item in result):
        raise ToolFailure("tool_denied", uncertain=False)
    return result[0]


def connection(url, policy, budget):
    host, port = url.hostname, url.port or (443 if url.scheme == "https" else 80)
    family, kind, proto, _, address = resolve(host, port, policy, budget)
    sock = budget.track(socket.socket(family, kind, proto))
    sock.settimeout(budget.remaining())
    # No second hostname lookup: connect to the exact address already vetted.
    sock.connect(address)
    if url.scheme == "https":
        context = ssl.create_default_context()
        context.set_alpn_protocols(["http/1.1"])
        sock = budget.track(
            context.wrap_socket(sock, server_hostname=host, do_handshake_on_connect=False)
        )
        sock.do_handshake()
    conn = http.client.HTTPConnection(host, port, timeout=budget.remaining())
    conn.sock = sock
    return conn


def request(policy, options, *, arguments, secret, effect_key, timeout_seconds, control, **_):
    bounded(arguments)
    body = None
    target = policy.origin + options.path
    if options.method in {"GET", "HEAD"}:
        if any(isinstance(value, (dict, list)) or value is None for value in arguments.values()):
            raise ToolFailure("tool_input_invalid", uncertain=False)
        if arguments:
            target += "?" + urlencode(arguments)
    else:
        body = json.dumps(arguments, allow_nan=False, separators=(",", ":")).encode()
    if len(target.encode()) > min(8192, policy.max_request_bytes) or (
        body is not None and len(body) > policy.max_request_bytes
    ):
        raise ToolFailure("tool_input_invalid", uncertain=False)
    headers = {"Accept": "application/json", "Accept-Encoding": "identity", "Connection": "close"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if secret:
        if (
            not policy.credential_alias
            or len(secret) > 4096
            or any(ord(char) < 32 or ord(char) > 126 for char in secret)
        ):
            raise ToolFailure("tool_denied", uncertain=False)
        headers[policy.credential_header] = (
            "Bearer " if policy.credential_header == "Authorization" else ""
        ) + secret
    if policy.idempotency_retention_seconds and options.method not in {"GET", "HEAD"}:
        headers["Idempotency-Key"] = effect_key
    budget, sent, conn = Budget(timeout_seconds, control), False, None
    try:
        for redirects in range(policy.max_redirects + 1):
            url = urlsplit(target)
            conn = connection(url, policy, budget)
            budget.remaining()
            path = valid_path(url.path or "/") + ("?" + url.query if url.query else "")
            sent = True  # An exception during request() may occur after remote acceptance.
            conn.request(options.method, path, body=body, headers=headers)
            response = conn.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location", "")
                next_url = urlsplit(urljoin(target, location))
                if (
                    options.method not in {"GET", "HEAD"}
                    or redirects >= policy.max_redirects
                    or not location
                    or next_url.username is not None
                    or next_url.fragment
                    or (next_url.scheme, next_url.netloc) != (url.scheme, url.netloc)
                    or len(next_url.geturl()) > 8192
                ):
                    raise ToolFailure("tool_denied")
                valid_path(next_url.path or "/")
                target = next_url.geturl()
                conn.close()
                continue
            if response.status >= 400:
                code = (
                    "tool_rate_limit"
                    if response.status == 429
                    else "tool_unavailable"
                    if response.status >= 500 or response.status in {408, 425}
                    else "tool_denied"
                )
                raise ToolFailure(code)
            if not 200 <= response.status < 300:
                raise ToolFailure("tool_response_invalid")
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise ToolFailure("tool_response_invalid")
            length = response.getheader("Content-Length")
            transfer = response.getheader("Transfer-Encoding")
            if transfer not in {None, "chunked"} or (transfer and length is not None):
                raise ToolFailure("tool_response_invalid")
            if length is not None and (
                not length.isdigit() or int(length) > policy.max_response_bytes
            ):
                raise ToolFailure("tool_response_invalid")
            content = bytearray()
            while True:
                budget.remaining()
                chunk = response.read1(min(8192, policy.max_response_bytes + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > policy.max_response_bytes:
                    raise ToolFailure("tool_response_invalid")
            budget.remaining()
            if length is not None and options.method != "HEAD" and len(content) != int(length):
                raise ToolFailure("tool_response_invalid")
            if options.method == "HEAD" or response.status == 204:
                payload = {}
            else:
                media = response.getheader("Content-Type", "").split(";")[0].strip().lower()
                if media != "application/json" and not media.endswith("+json"):
                    raise ToolFailure("tool_response_invalid")
                payload = json.loads(content)
            result = {"status": response.status, "body": payload}
            bounded(result)
            return result
        raise ToolFailure("tool_denied")
    except ToolFailure as error:
        if not sent:
            error.uncertain = False
        raise
    except (TimeoutError, OSError, http.client.HTTPException) as error:
        code = (
            "tool_timeout"
            if isinstance(error, TimeoutError) or monotonic() >= budget.end
            else "tool_unavailable"
        )
        raise ToolFailure(code, uncertain=sent) from None
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ToolFailure("tool_response_invalid", uncertain=sent) from None
    finally:
        if conn:
            conn.close()
        budget.finish()


def adapter(contract, organization_id, credential):
    options, policy = destination(organization_id, contract.options)
    if (credential.source_alias if credential else None) != policy.credential_alias:
        raise ToolFailure("tool_denied", uncertain=False)

    def invoke(**kwargs):
        kwargs.pop("options", None)  # Use the already validated, server-bound options.
        return request(policy, options, **kwargs)

    def reconcile(**kwargs):
        age = (datetime.now(UTC) - kwargs["effect_created_at"]).total_seconds()
        if age + kwargs["timeout_seconds"] >= policy.idempotency_retention_seconds:
            return Reconciliation("unknown")
        return Reconciliation("succeeded", invoke(**kwargs))

    return ToolAdapter(
        invoke,
        recovery="reconcile" if policy.idempotency_retention_seconds else "none",
        reconcile=reconcile,
        side_effecting=options.method not in {"GET", "HEAD"},
        requires_approval=True,
        policy_identity=digest(
            {**policy.model_dump(mode="json"), "methods": sorted(policy.methods)}
        ),
    )
