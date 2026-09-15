# Identity and organization membership

Phase 67 adds an OIDC-compatible identity boundary, disabled by default. Public
API startup is blocked until tenant isolation and role enforcement in Phases
68–69 are complete. This phase alone does not make legacy data tenant-safe.
Existing prototype API-key mode remains available for local development.

## Verified identity

The API verifies RS256 JWT signatures against the configured HTTPS JWKS endpoint,
exact issuer/audience, required subject/issued-at/expiry and authorized party when
present. Signing key URLs and algorithms never come from token claims. Unknown
users are rejected; email domains and token role claims cannot grant membership.

`users` binds issuer plus subject to a server-owned identity. Active organization
memberships grant viewer/operator/reviewer/admin roles. `X-Organization-ID` selects
a membership and grants no authority itself. Caller role/actor claims and
`X-AgentOps-Role` are ignored in identity mode. Account, organization and membership
disablement is checked on subsequent requests.

Service identities share the unique issuer/subject binding and use a separate
`service_principals` record containing one organization, viewer/operator role,
explicit scopes and enablement. They cannot establish browser sessions.
Operation-specific scope enforcement follows in the Phase 69 role gate.

## Browser flow

`/account` offers sign-in and organization selection. Authorization code sign-in
uses state, nonce and S256 PKCE. The server exchanges the code and the API verifies
the ID token and nonce. The browser receives a random session token in an HttpOnly,
SameSite=Lax cookie. PostgreSQL stores only its SHA-256 hash. Provider tokens never
enter browser storage, URLs or the session table. Production cookies require
Secure and configured production endpoints require HTTPS.

Sessions expire at the earlier of provider token expiry or the configured session
lifetime (one hour by default). Sign-out revokes the database session. Automatic
refresh and provider-wide logout are not implemented; expiry requires sign-in.
The shared web API client forwards the session and selected organization from the
server. Both organization selection and API access check active membership.

## Configuration and provisioning

Run `uv run --directory apps/api alembic upgrade head`. Migration `f067_identity`
adds identity tables without assigning ownership to historical business data;
the reversible legacy backfill belongs to Phase 68.

API configuration: `IDENTITY_ENABLED=true`, `OIDC_ISSUER`, `OIDC_AUDIENCE`,
`OIDC_JWKS_URL`, and optional `IDENTITY_SESSION_SECONDS`.

Web configuration: `IDENTITY_ENABLED=true`, `APP_ORIGIN`, `OIDC_AUTHORIZE_URL`,
`OIDC_TOKEN_URL`, `OIDC_CLIENT_ID`, and `OIDC_CLIENT_SECRET` for a confidential
client. The API audience must match the web client ID for ID-token exchange.
Register `<APP_ORIGIN>/auth/callback` exactly with the provider. Keep credentials
in environment or secret storage. See the API/web environment example files.

An administrator with direct database access can provision a human membership:

```powershell
uv run --directory apps/api python -m src.provision_identity --issuer https://issuer.example/ --subject provider-subject --display-name "Example User" --organization-id 00000000-0000-0000-0000-000000000100 --organization-name "Example" --role admin
```

Use the provider's verified subject, not a caller-supplied email. The command is
idempotent for matching records and refuses implicit reactivation, role changes
or conversion of service identities. The UUID above is an example. Membership
administration and audit follow in Phase 69.

## Validation and limits

`test_identity.py` uses locally generated RSA keys and real PostgreSQL schemas
for claim/signature forgery, revocation, expiry, disabled membership, service
boundaries, role-header forgery and session APIs. Web route tests exercise PKCE,
callback state, nonce forwarding, opaque session cookies and failed exchanges.
These are fixtures: no live provider registration or hosted sign-in was performed.

Reference contracts: [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
and [PyJWT verification API](https://pyjwt.readthedocs.io/en/stable/api.html).
