# Deployment

Choose a profile deliberately. The root Compose file is development tooling;
production images and isolated verification profiles live under `deploy/`.
The required local container/Kubernetes deployments were measured. A hosted
profile exists, but no hosted target has been deployed or verified.

| Path | Use | Recorded evidence |
| --- | --- | --- |
| [Root Compose](../docker-compose.yml) | Loopback development, reload/source mounts, local credentials | CI configuration check |
| [Production containers](PRODUCTION_CONTAINERS.md) | Immutable web/API/worker images, separate migration, protected configuration, health/readiness and drain | [Authenticated local container results](PRODUCTION_CONTAINER_RESULTS.md) |
| [Kubernetes](KUBERNETES.md) | Local kind/PVC profile and hosted external-DB profile; services/ingress, secret references, limits and metrics | [Local cluster results](KUBERNETES_RESULTS.md) |
| [Operations harness](KUBERNETES_OPERATIONS.md) | Owned local cluster only: rollout, scaling, loss/fencing, outage, restore and rollback | [Measured operations](KUBERNETES_OPERATIONS_RESULTS.md) |

## Local Docker development

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build
docker compose ps
```

Web is `http://localhost:3000`, API `http://localhost:8000`, PostgreSQL is bound
to loopback port 5432. API startup applies Alembic migrations; the worker starts
after API health. The root profile has development identity behavior and local
credentials. Do not expose it publicly. `docker compose logs` inspects services;
`docker compose down` stops/removes containers while retaining named volumes.
Do not add `--volumes` when preserving datasets.

Open `/demo` and seed the full illustrative dataset to explore the business UI
without provider calls. Seeding also installs the business templates. For an
empty organization without demo records, an administrator can install the
[sales/feedback/incident templates](BUSINESS_TEMPLATES.md) explicitly. Installation
publishes configuration but does not call a provider. Worker credentials and quota
are required for subsequent live LLM runs.

## Native development

Use Python 3.12, Node.js 24 and the repository's uv/pnpm lockfiles. Provision a
local PostgreSQL database and set `DATABASE_URL` consistently for API, CLI and
workers. Follow [identity](IDENTITY.md) if enabling verified local sessions.

```powershell
pnpm install --frozen-lockfile
uv sync --directory apps/api --locked --dev
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m src.seed_prompts
```

Run each long-lived service in its own terminal:

```powershell
uv run --directory apps/api uvicorn src.main:app --host 127.0.0.1 --port 8000
uv run --directory apps/api python -m src.worker
pnpm --dir apps/web dev --hostname 127.0.0.1 --port 3000
```

These are separate commands, not a sequential service launcher. Web server requests
use `API_INTERNAL_URL` when configured; `NEXT_PUBLIC_API_URL` is the public API
address/fallback. Container server requests must use service DNS. No browser
credential value belongs in a `NEXT_PUBLIC_*` variable. See environment examples
in [API](../apps/api/.env.example) and [web](../apps/web/.env.local.example).

## Production configuration boundary

Public startup requires `ENVIRONMENT=production`, verified identity and HTTPS
OIDC configuration. Use registered issuer/audience/JWKS, exact callback origin,
PKCE sign-in, provisioned memberships and protected database/tool credentials.
Shared development keys or caller-selected role headers do not replace this.
[Identity and permissions](IDENTITY.md) is canonical for configuration/provisioning.

Apply migrations as an ordered release step before serving upgraded workloads.
Keep PostgreSQL and worker endpoints private; expose only the intended TLS web/API
routing. Configure bounded rate/transport policies and network egress. Runtime
container probes distinguish process health from database readiness; worker
readiness checks that container's own unexpired presence.

Use the production/Kubernetes runbooks for exact build, secret generation,
migration, deployment, verification and cleanup commands. Their fixture profile
uses synthetic TLS/OIDC for the owned local environment only. It is not a real
identity provider or a public deployment recommendation. Secrets and binary
backups stay outside Git; only redacted evidence and hashes are committed.

## Upgrade, backout and recovery

Accepted runs retain their graph and worker ownership across later publication.
Business-template feature flags choose the legacy path for future starts only;
keep workers available for accepted durable work. Additive migrations protect
retained identities/history; some downgrades deliberately refuse existing data.
Do not infer that image rollback permits schema deletion.

The [operations verification](KUBERNETES_OPERATIONS_RESULTS.md) tested a distinct
metadata-only image release at the same application/schema version, then rolled
back to the known baseline. It restored a binary PostgreSQL backup into a fresh
database and rechecked 11 workflow/tool history tables. Original databases/PVCs
were retained. This is not cluster-role, Secret, registry or provider-data recovery.

## Validation and remaining work

CI migrates fresh PostgreSQL, runs API/web tests and builds, renders local/hosted/
operations Kubernetes profiles and Compose configuration, and audits dependencies.
A successful render is not a deployment. Local authenticated deployment and
operations evidence are separate from CI configuration checks.

Hosted target/access, real identity-provider and tool-account acceptance,
multi-node failure, managed-DB failover, production backups/restore objectives,
network policy enforcement and security review belong to a separately configured
rollout. None was silently substituted with fixture evidence.
[Security policy](../SECURITY.md) · [Phase ledger](phase-progress.md).
