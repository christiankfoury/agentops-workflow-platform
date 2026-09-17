# Production containers

Phase 100 provides separate API/worker and Next.js standalone runtime images.
Development still uses the root `docker-compose.yml`. Kubernetes deployment is
tracked separately. This profile is a reproducible production-mode local test,
not evidence of a hosted security assessment or production availability SLA.

## Runtime contract

- API and workers use the same locked Python dependencies and application image.
  The image contains runtime code and migrations, not tests, `.env`, keys or dev
  dependencies. Both entry points require verified identity with HTTPS issuer and
  JWKS endpoints outside development/test. API trusted hosts are explicit.
- Web uses Node 24 LTS and Next.js standalone output, with runtime OIDC settings.
  Browser traffic uses the TLS gateway; server requests use private `api:8000`.
  `/api/*` is forwarded to the API. API credentials never enter browser JavaScript.
- Runtime services use non-root users, read-only filesystems, temporary scratch
  storage, dropped capabilities, no privilege escalation, bounded CPU/memory,
  rotating stdout logs and a 60-second termination grace. PostgreSQL alone writes
  its named persistent volume. Database and application ports are private; only
  gateway HTTPS is published, bound to loopback by default.
- `/health` is process liveness; `/ready` checks database reachability on the API
  and API readiness on the web. Worker health checks the current process instance's
  unexpired database presence. The entrypoint replaces its local identity before
  importing the worker, preventing an old heartbeat from satisfying readiness.
  Presence is telemetry, not lease authority. A small container init forwards
  signals even during Python imports and reaps child processes.
  OIDC availability is verified during sign-in, not polled on each health check.
- SIGTERM stops worker claims and drains current work. Work exceeding the grace
  may be killed; lease expiry/fencing and configured recovery limits apply. This
  does not make arbitrary external effects exactly once. See
  [reliability results](RELIABILITY_RESULTS.md).
- Secret files are read before process startup. Supported API variables are
  `DATABASE_URL_FILE`, `OPENAI_API_KEY_FILE`, `TOOL_CREDENTIAL_VALUES_FILE` and
  `WEBHOOK_SECRET_VALUES_FILE`; web supports `OIDC_CLIENT_SECRET_FILE`. Setting
  both a nonempty direct variable and its file variant fails closed. File access
  must permit the container UID; never put secret values into image build args.
  Mounted-file rotation requires a service restart. Compose secrets are file
  mounts, not an encrypted secret store; protect host files and backups.

## Reproduce the isolated verification

Requires Docker Compose, Python 3.12/uv, sufficient disk and roughly 4 GiB of
available container memory. Run from the repository root. The commands create
only the named `agentops-phase100` stack and a fresh `.local/production` directory.
The setup refuses to overwrite existing credentials. Do not reuse this identity
fixture on a public interface: it automatically signs in a synthetic local user.

```powershell
uv run --directory apps/api python ../../deploy/verification/setup.py
docker compose --env-file .local/production/compose.env -f deploy/compose.production.yml build migrate web gateway
docker compose -p agentops-phase100 --env-file .local/production/compose.env -f deploy/compose.production.yml -f deploy/compose.verification.yml build oidc
docker compose -p agentops-phase100 --env-file .local/production/compose.env -f deploy/compose.production.yml -f deploy/compose.verification.yml up -d --wait
uv run --directory apps/api python ../../deploy/verification/verify.py --output .local/production/verification
uv run --directory apps/api python ../../deploy/verification/drain.py
```

The generated TLS certificates expire after seven days. Certificates and private
keys stay in the ignored directory. No host trust store is changed. The test client verifies TLS
against that CA; API/web trust it only through the explicit verification overlay.
On POSIX, setup restricts the parent directory to its owner while allowing
non-root containers to read the bind-mounted files. On Windows, protect the
directory using the user's filesystem ACLs. These are disposable test secrets.

Verification provisions an admin through the existing direct-database bootstrap,
then follows the browser OIDC authorization-code flow with state, nonce, PKCE,
signature verification and secure session cookies. It publishes a deterministic
approval/code graph, checks start deduplication, approves and completes it,
restarts services and checks persisted state/session, stops PostgreSQL to observe
readiness failure, then tests actual worker SIGTERM amid a queued burst. All
accepted runs/jobs must reconcile after restart. Provider keys and external
destinations are empty; no paid model or external effect is invoked.

The commands write new evidence under `.local/production` and refuse to replace
old evidence. Use `--output` to select another unused location for a
corrected rerun. Leave the stack for inspection, or stop its services without
deleting the named volume. Never run volume deletion against an unrelated stack.

The separate drain check takes a bounded lock on `step_attempts` only in this
owned disposable database, waits for a real claimed job, sends container SIGTERM,
observes its draining heartbeat, releases the checkpoint and requires clean exit
with the original job completed without lease recovery. It restarts the worker
and checks the remaining continuation. Do not run this fixture against shared or
production data. The database releases an abandoned fixture lock after 45 seconds.

## Configure a real identity provider and TLS

Use only `deploy/compose.production.yml`, without the verification overlay.
Provision files in a protected directory and set `SECRET_DIR` to its absolute
path. Required files: `database_password`, matching `database_url`,
`oidc_client_secret` (empty for a public PKCE client), `tls.crt`, `tls.key`.
Use an explicit PostgreSQL URL and your provider's HTTPS issuer, JWKS,
authorization/token URLs, client ID and exact `APP_ORIGIN/auth/callback` redirect.
Set `PUBLIC_HOST` to that origin's hostname; the gateway rejects other hosts.
The environment names are listed in the Compose file; none contain embedded
credentials. Register users/memberships with `python -m src.provision_identity`
under an authorized database administrator identity. There is no public signup.

The default gateway binds loopback. A public ingress/TLS/firewall configuration
is a separate deployment decision. Restrict trusted API hosts to the actual
proxy/private service names. Provider credentials and tool destinations require
explicit configuration; only allow reviewed network destinations and least
privilege service credentials. Logs disable raw API access URLs; gateway and
verification provider do not log authentication query strings.

The included PostgreSQL container uses its bootstrap database owner for this
single-database profile. A hosted deployment should provision separate migration
and application roles with only the required grants; this profile does not claim
database role separation, network-policy enforcement or an OS-image vulnerability
assessment. API and web package dependency audits remain required by CI.

## Migration and rollout order

1. Back up and verify database compatibility for the target release. Pin built
   image digests and record source revision using `SOURCE_REVISION` build arg.
2. Build API/web once; use the API image for the one-shot `migrate` service.
   Run `alembic upgrade head` once and require exit zero before API/workers start.
   Never run competing migration commands from every application replica.
3. Start API, workers, web and gateway. Require readiness, authenticated smoke
   verification and worker metrics before routing normal work.
4. For updates, keep old/new workers compatible with existing graph versions and
   schema. Additive migrations precede rollout; destructive migrations require a
   separate staged plan and backup/restore verification. Image rollback is safe
   only when that image understands the current schema and persisted versions.
5. Stop claims with SIGTERM; retain lease time and adequate termination grace.
   Verify recovered work and unknown effects before retrying non-idempotent work.

Phase 100 adds no migration. Deployment evidence and measured limitations are
recorded in the [progress tracker](phase-progress.md).
