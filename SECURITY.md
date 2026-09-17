# Security Policy

## Supported version and reporting

Security fixes target the latest commit on `main`; older forks/commits are not
maintained releases. Do not open a public issue for a suspected vulnerability.
Use GitHub private vulnerability reporting from the repository's Security tab.
If unavailable, request a private channel through the maintainer's profile before
sharing details. Include affected component, reproduction, impact and mitigation;
do not access data belonging to others.

## Runtime boundaries

[Verified identity](docs/IDENTITY.md) checks issuer/audience/signature/expiry and
resolves server-owned users, organizations, memberships and service scopes.
Revocable browser sessions use hashed tokens and production Secure/HttpOnly
cookies. Caller role/actor claims do not grant permission in identity mode.
Tenant checks cover reads, nested resources, writes, aggregates and exports;
sensitive decisions recheck authority within their transaction.

Published workflows and tool contracts are immutable. Approval hashes bind exact
reviewed data; edits supersede old decisions. Side-effecting actions recheck their
approval and configured policy at dispatch. Tool output cannot add credentials,
permissions or declared tools. Graph code nodes use registered handlers; uploaded
arbitrary code is unsupported. [Tools](docs/TOOL_CONTRACTS.md) ·
[LLM tools](docs/LLM_TOOL_CALLING.md).

Worker credentials stay in protected server configuration, referenced by tenant
aliases. HTTP policies constrain destinations/methods and vetted addresses;
PostgreSQL tools use configured read-only queries. Trace readers mask known
credential fields and exclude internal ownership tokens, but cannot identify
arbitrary secrets embedded in prose. Never put credentials in workflow payloads,
issue text, prompts, logs or committed environment files.

## Deployment scope

The root Compose profile is loopback-only development with local credentials and
development identity behavior. Public startup requires production identity and
HTTPS configuration. Use the [production](docs/PRODUCTION_CONTAINERS.md) or
[Kubernetes](docs/KUBERNETES.md) runbooks for separate migration, secret references,
non-root containers, probes, limits and intended ingress. Keep database/worker
access private and configure deployment network/egress controls.

Recorded local acceptance uses a synthetic TLS/OIDC fixture and an owned single-node
cluster. The hosted profile is unperformed. Container hardening, passing tests and
dependency audits are not a production penetration test, compliance certification
or guarantee against all authorization/network threats. Identity provisioning,
secret rotation, real account policy and operational recovery require the target's
own configuration and verification.

## Validation and known limits

CI runs tests, fresh database migration, lint/type checks, builds, configuration
renders and dependency audits. [Evidence](docs/PLATFORM_EVIDENCE.md) links identity,
tenant/permission, approval, tool and deployed checks. No arbitrary-provider
exactly-once effect guarantee is made; ambiguous writes remain explicit.
Cancellation cannot undo a remote action. Automatic session refresh, general
notifications and hosted failover are not implemented/verified capabilities.
