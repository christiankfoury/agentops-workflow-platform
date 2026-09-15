import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from urllib.parse import urlparse

import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models.identity import IdentitySession, Membership, Organization, ServicePrincipal, User


@dataclass(frozen=True)
class Principal:
    role: str
    user_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    service_principal_id: uuid.UUID | None = None
    scopes: frozenset[str] = frozenset()


@lru_cache(maxsize=4)
def jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, timeout=5, lifespan=300)


def verify_token(token: str, *, nonce: str | None = None) -> dict:
    if not settings.identity_enabled:
        raise HTTPException(503, "Identity sign-in is not enabled")
    if not all([settings.oidc_issuer, settings.oidc_audience, settings.oidc_jwks_url]):
        raise HTTPException(503, "Identity provider is not configured")
    if urlparse(settings.oidc_jwks_url).scheme != "https":
        raise HTTPException(503, "Identity signing keys require HTTPS")
    if not token or len(token) > 16384:
        raise HTTPException(401, "Invalid identity token")
    try:
        key = jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            options={"require": ["iss", "sub", "aud", "exp", "iat"], "strict_aud": True},
        )
        if not isinstance(claims["sub"], str) or not claims["sub"]:
            raise jwt.InvalidTokenError()
        if any(type(claims[key]) is not int for key in ["exp", "iat"]):
            raise jwt.InvalidTokenError()
        if claims.get("azp", settings.oidc_audience) != settings.oidc_audience:
            raise jwt.InvalidTokenError()
        if nonce is not None and claims.get("nonce") != nonce:
            raise jwt.InvalidTokenError()
        return claims
    except (jwt.PyJWTError, ValueError, TypeError, OSError) as exc:
        # Never include raw tokens, provider response bodies or claims in errors.
        raise HTTPException(401, "Invalid identity token") from exc


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def user_for_claims(db: Session, claims: dict) -> User:
    user = db.scalar(
        select(User).where(
            User.issuer == claims["iss"],
            User.subject == claims["sub"],
            User.active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(403, "Identity is not provisioned or is disabled")
    return user


def authenticate(db: Session, authorization: str | None) -> User:
    if not settings.identity_enabled:
        raise HTTPException(503, "Identity sign-in is not enabled")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() == "bearer":
        return user_for_claims(db, verify_token(token))
    if scheme.lower() == "session" and 20 <= len(token) <= 128:
        session = db.get(IdentitySession, token_hash(token))
        if session and not session.revoked and session.expires_at > datetime.now(UTC):
            user = db.get(User, session.user_id)
            if user and user.active and user.kind == "user":
                return user
    raise HTTPException(401, "Invalid or missing identity session")


def memberships(db: Session, user: User):
    return db.execute(
        select(Membership, Organization)
        .join(
            Organization,
            Membership.organization_id == Organization.id,
        )
        .where(
            Membership.user_id == user.id,
            Membership.active.is_(True),
            Organization.active.is_(True),
        )
        .order_by(Organization.name, Organization.id)
    ).all()


def resolve_principal(db: Session, user: User, organization_id: str | None) -> Principal:
    try:
        selected = uuid.UUID(organization_id) if organization_id else None
    except ValueError as exc:
        raise HTTPException(400, "Invalid organization selection") from exc
    if user.kind == "service":
        service = db.scalar(
            select(ServicePrincipal)
            .join(Organization)
            .where(
                ServicePrincipal.user_id == user.id,
                ServicePrincipal.active.is_(True),
                Organization.active.is_(True),
            )
        )
        if service is None or (selected is not None and selected != service.organization_id):
            raise HTTPException(403, "Service principal cannot access this organization")
        return Principal(
            service.role, user.id, service.organization_id, service.id, frozenset(service.scopes)
        )
    choices = memberships(db, user)
    if selected is None and len(choices) == 1:
        selected = choices[0][0].organization_id
    for membership, _organization in choices:
        if membership.organization_id == selected:
            return Principal(membership.role, user.id, membership.organization_id)
    raise HTTPException(403, "Select an organization with an active membership")


def create_session(db: Session, token: str, nonce: str) -> tuple[str, datetime]:
    claims = verify_token(token, nonce=nonce)
    user = user_for_claims(db, claims)
    if user.kind != "user" or not memberships(db, user):
        raise HTTPException(403, "An active user membership is required")
    expires = datetime.fromtimestamp(
        min(
            claims["exp"],
            datetime.now(UTC).timestamp() + settings.identity_session_seconds,
        ),
        UTC,
    )
    opaque_token = secrets.token_urlsafe(32)
    db.add(
        IdentitySession(token_hash=token_hash(opaque_token), user_id=user.id, expires_at=expires)
    )
    db.commit()
    return opaque_token, expires
