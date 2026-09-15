"""Membership-derived permissions shared by request handlers and service operations."""

from functools import wraps

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models.identity import Membership, Organization, ServicePrincipal, User
from src.services.identity import Principal
from src.services.tenancy import tenant_id

PERMISSIONS = {
    "read": {"viewer", "operator", "reviewer", "admin"},
    "export": {"viewer", "operator", "reviewer", "admin"},
    "workflow.start": {"operator", "admin"},
    "workflow.draft": {"operator", "admin"},
    "workflow.control": {"operator", "admin"},
    "input.write": {"operator", "admin"},
    # Legacy comparison execution includes automatic approval decisions.
    "evaluation.run": {"admin"},
    "approval.decide": {"reviewer", "admin"},
    "approval.override": {"admin"},
    "prompt.manage": {"admin"},
    "settings.manage": {"admin"},
    "membership.manage": {"admin"},
    "credentials.manage": {"admin"},
    "workflow.publish": {"admin"},
    "demo.seed": {"admin"},
    "audit.read": {"admin"},
}


def permits(principal: Principal, action: str) -> bool:
    return principal.role in PERMISSIONS.get(action, set()) and (
        principal.service_principal_id is None or action in principal.scopes
    )


def current_principal(db: Session, *, lock: bool = False) -> Principal:
    if not isinstance(db, Session):
        return Principal(role="admin")  # Local domain-test doubles have no identity store.
    principal = db.info.get("principal")
    if not settings.identity_enabled:
        return principal or Principal(role="admin")
    if principal is None or principal.user_id is None:
        raise HTTPException(403, "A verified principal is required")
    if principal.organization_id != tenant_id(db):
        raise HTTPException(403, "Principal and organization scope do not match")
    # Scalar projections bypass cached ORM identities. Decision-time locks serialize
    # against membership/account disablement until the short transaction commits.
    model = ServicePrincipal if principal.service_principal_id else Membership
    columns = [model.role, model.scopes] if model is ServicePrincipal else [model.role]
    query = (
        select(*columns)
        .join(User, User.id == model.user_id)
        .join(Organization, Organization.id == model.organization_id)
        .where(
            model.user_id == principal.user_id,
            model.organization_id == principal.organization_id,
            model.active.is_(True),
            User.active.is_(True),
            Organization.active.is_(True),
            User.kind == ("service" if model is ServicePrincipal else "user"),
        )
    )
    if model is ServicePrincipal:
        query = query.where(model.id == principal.service_principal_id)
    if lock:
        db.execute(
            select(Organization.id)
            .where(
                Organization.id == principal.organization_id,
            )
            .with_for_update(read=True)
        )
        query = query.with_for_update(read=True)
    with db.no_autoflush:
        row = db.execute(query).one_or_none()
    if row is None:
        raise HTTPException(403, "Membership is no longer active")
    return Principal(
        row[0],
        principal.user_id,
        principal.organization_id,
        principal.service_principal_id,
        frozenset(row[1]) if model is ServicePrincipal else frozenset(),
    )


def authorize(db: Session, action: str, *, lock: bool = False) -> Principal:
    principal = current_principal(db, lock=lock)
    if not permits(principal, action):
        raise HTTPException(
            403,
            "Insufficient API role"
            if principal.service_principal_id is None
            else "Insufficient service scope or role",
        )
    return principal


def request_action(method: str, path: str) -> str:
    if method in {"GET", "HEAD"}:
        if path.startswith("/access/audit"):
            return "audit.read"
        if path.startswith("/access/members"):
            return "membership.manage"
        return "export" if "/export/" in path else "read"
    prefix = path.split("/")[1]
    if prefix == "workflow-executions":
        return (
            "workflow.start" if path.rstrip("/") == "/workflow-executions" else "workflow.control"
        )
    if prefix == "workflow-definitions":
        if path.rstrip("/").endswith(("/publish", "/archive")):
            return "workflow.publish"
        return "read" if path.rstrip("/").endswith("/validate") else "workflow.draft"
    if prefix == "workflow-runs":
        if path.rstrip("/") == "/workflow-runs":
            return "workflow.start"
        return "evaluation.run" if "evaluation-comparison" in path else "workflow.control"
    return {
        "human-approvals": "approval.decide",
        "execution-approvals": "approval.decide",
        "uploaded-inputs": "input.write",
        "prompt-versions": "prompt.manage",
        "agent-settings": "settings.manage",
        "evaluation-results": "evaluation.run",
        "demo": "demo.seed",
        "access": "membership.manage",
    }.get(prefix, "unknown")


def requires_permission(action: str):
    def decorate(function):
        @wraps(function)
        def guarded(db, *args, **kwargs):
            authorize(db, action)
            return function(db, *args, **kwargs)

        return guarded

    return decorate
