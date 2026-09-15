import time
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.database import get_db
from src.main import app
from src.models.identity import IdentitySession, Membership, Organization, ServicePrincipal, User
from src.provision_identity import main as provision_main
from src.services.identity import authenticate, create_session, resolve_principal, token_hash
from tests.test_workflow_transactions_postgres import database as database

ISSUER = "https://identity.example.test/"
AUDIENCE = "agentops-local-test"
NONCE = "local-nonce-for-session-verification"


@pytest.fixture(scope="module")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def auth_config(monkeypatch, signing_key):
    monkeypatch.setattr(settings, "identity_enabled", True)
    monkeypatch.setattr(settings, "oidc_issuer", ISSUER)
    monkeypatch.setattr(settings, "oidc_audience", AUDIENCE)
    monkeypatch.setattr(settings, "oidc_jwks_url", ISSUER + "jwks")
    monkeypatch.setattr(
        "src.services.identity.jwks_client",
        lambda url: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: signing_key.public_key(),
        ),
    )


def signed_token(key, **overrides):
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "alice",
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "nonce": NONCE,
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="RS256")


def provision(db, *, kind="user"):
    user = User(issuer=ISSUER, subject="alice", display_name="Alice", kind=kind)
    org = Organization(name="Example organization")
    db.add_all([user, org])
    db.flush()
    member = Membership(user_id=user.id, organization_id=org.id, role="viewer")
    db.add(member)
    db.commit()
    return user, org, member


def test_verified_identity_ignores_forged_role_and_actor(auth_config, signing_key, database):
    with Session(database) as db:
        user, org, member = provision(db)
        token = signed_token(signing_key, role="admin", organization_id="forged", actor="forged")
        principal = resolve_principal(db, authenticate(db, "Bearer " + token), str(org.id))
        assert principal.role == "viewer" and principal.user_id == user.id
        assert principal.organization_id == org.id
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/uploaded-inputs",
                    headers={
                        "authorization": "Bearer " + token,
                        "x-agentops-role": "admin",
                        "x-organization-id": str(org.id),
                    },
                    json={"title": "forged", "input_type": "sales_report", "raw_text": "input"},
                )
                assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://attacker.example"},
        {"aud": "different-app"},
        {"exp": 1},
        {"iat": int(time.time()) + 3600},
        {"sub": ""},
        {"aud": [AUDIENCE, "another-client"]},
        {"azp": "another-client"},
    ],
)
def test_invalid_claims_are_rejected(auth_config, signing_key, database, changes):
    with Session(database) as db:
        provision(db)
        token = signed_token(signing_key, **changes)
        with pytest.raises(HTTPException) as error:
            authenticate(db, "Bearer " + token)
        assert error.value.status_code == 401 and token not in error.value.detail


def test_invalid_signature_and_unsigned_tokens_fail(auth_config, database):
    different_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with Session(database) as db:
        for token in [
            signed_token(different_key),
            "not.a.jwt",
            jwt.encode({"sub": "alice"}, "", algorithm="none"),
        ]:
            with pytest.raises(HTTPException) as error:
                authenticate(db, "Bearer " + token)
            assert error.value.status_code == 401


@pytest.mark.parametrize("disabled", ["user", "membership", "organization"])
def test_disabled_records_reject_access(auth_config, signing_key, database, disabled):
    with Session(database) as db:
        user, org, member = provision(db)
        {"user": user, "membership": member, "organization": org}[disabled].active = False
        db.commit()
        with pytest.raises(HTTPException) as error:
            resolve_principal(
                db, authenticate(db, "Bearer " + signed_token(signing_key)), str(org.id)
            )
        assert error.value.status_code == 403


def test_opaque_session_is_hashed_expiring_and_revocable(auth_config, signing_key, database):
    with Session(database) as db:
        user, org, member = provision(db)
        opaque, expires = create_session(db, signed_token(signing_key), NONCE)
        stored = db.scalars(select(IdentitySession)).one()
        assert stored.token_hash == token_hash(opaque) and stored.token_hash != opaque
        assert expires <= datetime.now(UTC) + timedelta(seconds=601)
        assert authenticate(db, "Session " + opaque).id == user.id
        stored.revoked = True
        db.commit()
        with pytest.raises(HTTPException):
            authenticate(db, "Session " + opaque)
        stored.revoked = False
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        with pytest.raises(HTTPException):
            authenticate(db, "Session " + opaque)


def test_session_nonce_and_membership_required(auth_config, signing_key, database):
    with Session(database) as db:
        user, org, member = provision(db)
        with pytest.raises(HTTPException):
            create_session(db, signed_token(signing_key), "wrong-nonce")
        member.active = False
        db.commit()
        with pytest.raises(HTTPException):
            create_session(db, signed_token(signing_key), NONCE)
        assert db.scalars(select(IdentitySession)).all() == []


def test_service_principal_is_organization_and_scope_bound(auth_config, signing_key, database):
    with Session(database) as db:
        user, org, _member = provision(db, kind="service")
        service = ServicePrincipal(
            user_id=user.id,
            organization_id=org.id,
            role="operator",
            scopes=["workflow:read", "workflow:start"],
        )
        db.add(service)
        db.commit()
        principal = resolve_principal(
            db, authenticate(db, "Bearer " + signed_token(signing_key)), None
        )
        assert principal.service_principal_id == service.id
        assert principal.scopes == {"workflow:read", "workflow:start"}
        with pytest.raises(HTTPException):
            resolve_principal(db, user, "00000000-0000-0000-0000-000000000001")
        with pytest.raises(HTTPException):
            create_session(db, signed_token(signing_key), NONCE)
        service.active = False
        db.commit()
        with pytest.raises(HTTPException):
            resolve_principal(db, user, None)


def test_identity_endpoints_session_and_logout(auth_config, signing_key, database):
    with Session(database) as db:
        user, org, member = provision(db)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                assert client.get("/identity/me").status_code == 401
                created = client.post(
                    "/identity/sessions",
                    json={
                        "nonce": NONCE,
                    },
                    headers={"authorization": "Bearer " + signed_token(signing_key)},
                )
                assert created.status_code == 201
                assert created.headers["cache-control"] == "no-store"
                headers = {"authorization": "Session " + created.json()["session_token"]}
                me = client.get("/identity/me", headers=headers)
                assert me.json()["organizations"][0]["id"] == str(org.id)
                assert me.json()["organizations"][0]["role"] == "viewer"
                assert (
                    client.delete("/identity/sessions/current", headers=headers).status_code == 204
                )
                assert client.get("/identity/me", headers=headers).status_code == 401
        finally:
            app.dependency_overrides.clear()


def test_unconfigured_identity_blocks_public_startup(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError, match="verified identity"):
        with TestClient(app):
            pass


def test_bootstrap_is_idempotent_and_refuses_implicit_role_change(database, monkeypatch):
    org_id = str(uuid.uuid4())
    arguments = [
        "provision_identity",
        "--issuer",
        ISSUER,
        "--subject",
        "bootstrap-user",
        "--display-name",
        "Bootstrap User",
        "--organization-id",
        org_id,
        "--organization-name",
        "Bootstrap",
        "--role",
        "admin",
    ]
    monkeypatch.setattr("sys.argv", arguments)
    monkeypatch.setattr("src.provision_identity.SessionLocal", sessionmaker(bind=database))
    provision_main()
    provision_main()
    with Session(database) as db:
        assert len(db.scalars(select(User)).all()) == 1
        assert len(db.scalars(select(Membership)).all()) == 1
    monkeypatch.setattr("sys.argv", arguments[:-1] + ["viewer"])
    with pytest.raises(SystemExit):
        provision_main()
    with Session(database) as db:
        assert db.scalars(select(Membership)).one().role == "admin"
