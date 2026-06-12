from __future__ import annotations

import hmac
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic

from fastapi import Depends, Header, HTTPException, Request

from src.config import settings

ROLE_VIEWER = "viewer"
ROLE_OPERATOR = "operator"
ROLE_ADMIN = "admin"
VALID_ROLES = {ROLE_VIEWER, ROLE_OPERATOR, ROLE_ADMIN}

_rate_limit_hits: dict[str, deque[float]] = defaultdict(deque)


@dataclass(frozen=True)
class Principal:
    role: str


def require_api_key(
    x_agentops_api_key: str | None = Header(default=None),
    x_agentops_role: str | None = Header(default=None),
) -> Principal:
    if not settings.api_auth_enabled:
        return Principal(role=ROLE_ADMIN)

    expected_key = settings.api_key_value
    if not expected_key:
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    if x_agentops_api_key is None or not hmac.compare_digest(
        x_agentops_api_key,
        expected_key,
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    role = (x_agentops_role or ROLE_VIEWER).strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=403, detail="Invalid API role")
    return Principal(role=role)


def require_role(*allowed_roles: str) -> Callable[[Principal], Principal]:
    allowed = set(allowed_roles)

    def dependency(
        principal: Principal = Depends(require_api_key),
    ) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient API role")
        return principal

    return dependency


def enforce_rate_limit(request: Request) -> None:
    limit = settings.api_rate_limit_per_minute
    if limit <= 0:
        return

    client_host = request.client.host if request.client is not None else "unknown"
    key = f"{client_host}:{request.url.path}"
    now = monotonic()
    window_start = now - 60
    hits = _rate_limit_hits[key]
    while hits and hits[0] < window_start:
        hits.popleft()
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    hits.append(now)


def reset_rate_limit_state() -> None:
    _rate_limit_hits.clear()
