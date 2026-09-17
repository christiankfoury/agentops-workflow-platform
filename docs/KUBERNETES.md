# Kubernetes deployment

Phase 101 supplies a Kustomize application base, an isolated Traefik ingress
controller, a disposable local profile and a hosted configuration profile.
Phase 102 covers rollout, failure and backup/restore experiments separately.
The local profile is a single-node verification environment, not a high-availability
database or a claim of production security certification.

## Prerequisites and boundaries

- Docker with Linux containers, sufficient memory (the measured Docker VM has
  about 7.7 GiB), Python/uv and the repository's locked build tools.
- HTTPS port `127.0.0.1:8443` available. Stop only a known owned verification
  stack if it occupies that port; preserve its database volume.
- [kind v0.33.0](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0),
  Kubernetes v1.37.0 and the node digest in
  [tools.py](../deploy/kubernetes/tools.py). The script verifies official binary
  SHA-256 checksums, writes only `.local/kubernetes`, and does not change PATH.
- Every kubectl command uses the dedicated kubeconfig and context below. Never
  substitute the user's default context. `cluster.py` also verifies kind ownership
  and the loopback API server before mutations.
- Local TLS/OIDC uses the synthetic fixture from
  [the container runbook](PRODUCTION_CONTAINERS.md). It has a seven-day certificate,
  no external account or paid provider. Keep private files under ignored `.local`;
  do not commit them or install the fixture CA into the operating system.

## Repeat the local deployment

Run from the repository root. On Linux/macOS omit `.exe` from binary paths and
adapt shell variables; the Python helpers are portable. The setup command refuses
to overwrite `.local/production`; reuse an existing unexpired fixture or explicitly
choose a fresh workspace. Preserve previous evidence and database volumes.

```powershell
uv run --directory apps/api python ../../deploy/verification/setup.py
uv run --directory apps/api python ../../deploy/kubernetes/tools.py
$kind = "$PWD/.local/kubernetes/kind-v0.33.0.exe"
$kubectl = "$PWD/.local/kubernetes/kubectl-v1.37.0.exe"
$kubeconfig = "$PWD/.local/kubernetes/kubeconfig"
& $kind create cluster --name agentops-phase101 --config deploy/kubernetes/kind.yaml --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5 --kubeconfig $kubeconfig --wait 180s
$revision = git rev-parse HEAD
docker build -f apps/api/Dockerfile.production --build-arg SOURCE_REVISION=$revision -t agentops-api:kubernetes apps/api
docker build -f apps/web/Dockerfile.production --build-arg SOURCE_REVISION=$revision -t agentops-web:kubernetes-v2 .
docker build -f deploy/Dockerfile.gateway -t agentops-gateway:kubernetes deploy
docker build -f deploy/verification/Dockerfile --build-arg API_IMAGE=agentops-api:kubernetes -t agentops-oidc-fixture:kubernetes deploy/verification
& $kind load docker-image agentops-api:kubernetes agentops-web:kubernetes-v2 agentops-gateway:kubernetes agentops-oidc-fixture:kubernetes --name agentops-phase101
uv run --directory apps/api python ../../deploy/kubernetes/cluster.py deploy
uv run --directory apps/api python ../../deploy/kubernetes/verify.py --output .local/kubernetes/verification
```

Check each command's exit status before proceeding. The deploy helper renders both
profiles, creates namespaced configuration and secrets, performs server-side schema
dry runs, waits for persistent PostgreSQL, runs a uniquely named migration Job to
completion, then starts application workloads. It does **not** apply the entire
profile concurrently. A failed migration prevents starting the new workloads.
The fixture's random database password is generated in memory and supplied through
stdin to Kubernetes; an existing Secret is preserved on rerun.

The verification command provisions the synthetic administrator in this database,
uses a real HTTPS authorization-code/PKCE login through ingress, publishes and runs
an approval/code graph, and checks the resulting value `42`. It checks authenticated
SSR, replaces owned database/API/worker Pods, confirms version/output/approval/session
persistence, and exports worker metrics. It refuses to overwrite its output folder.
Browser access uses [the local HTTPS UI](https://localhost:8443); the fixture CA must
be trusted by the individual client. Do not disable TLS checks in automated tests.

## Runtime and operational configuration

See [the base](../deploy/kubernetes/base/kustomization.yaml) and
[local overlay](../deploy/kubernetes/local/kustomization.yaml).

- Application Pods use a service account with no mounted Kubernetes API token,
  non-root UIDs, dropped capabilities, read-only roots, bounded writable volumes,
  resource requests/limits and restricted Pod Security admission.
- API/web health probes check the process; readiness checks database/API dependencies.
  Worker startup/readiness checks its exact registered process identity and fresh
  heartbeat. Process exit restarts it; a temporary DB failure is not a liveness kill.
- API and worker images use `tini` for signal forwarding and child reaping. Pods have
  60 seconds to stop; workers stop taking new jobs and drain owned work. Leases fence
  late owners and recover unfinished work, subject to the documented effect limits.
- Application rollouts allow one surge Pod and zero unavailable Pods. This consumes
  spare capacity. Worker concurrency defaults to two per replica; each process can
  open up to eight DB connections. Budget connections and CPU before scaling.
- Local PostgreSQL uses a 1 GiB PVC. Pod replacement retains it; deleting the cluster
  destroys local storage. A PVC is not a backup. Never delete the cluster as routine
  validation cleanup while evidence/data is needed.
- Secrets are volume references: `database/database_url`, `identity/oidc_client_secret`,
  and ingress `platform-tls` (`tls.crt`, `tls.key`). Local-only signing/CA/password
  resources are absent from the hosted overlay. Kubernetes Secret storage is base64,
  not encryption; configure at-rest encryption and administrator access appropriately.
- The controller watches only `agentops-ingress`, whose gateway Service points to
  the application's internal gateway. Its namespaced Secret permissions cannot read
  application DB/OIDC secrets. Cluster discovery is limited to nodes/IngressClasses.
  This is RBAC isolation; no default-deny network policy is claimed.
- `worker-metrics` is an operator CronJob that writes aggregate Prometheus text to
  Kubernetes logs once per minute. It has no public endpoint and is not a Prometheus
  monitoring stack. Authenticated tenant metrics remain `/api/operations/metrics`.

```powershell
& $kubectl --kubeconfig $kubeconfig --context kind-agentops-phase101 -n agentops get pods,pvc,jobs
& $kubectl --kubeconfig $kubeconfig --context kind-agentops-phase101 -n agentops create job inspect-metrics --from=cronjob/worker-metrics
& $kubectl --kubeconfig $kubeconfig --context kind-agentops-phase101 -n agentops logs job/inspect-metrics
& $kubectl --kubeconfig $kubeconfig --context kind-agentops-phase101 -n agentops scale deployment/worker --replicas=2
```

Wait for the metrics Job to complete before reading logs. Scaling is an operator
action; the separate Phase 102 evidence records whether it was exercised.

## Hosted profile: configure before applying

[The hosted overlay](../deploy/kubernetes/hosted/kustomization.yaml) contains no local
PostgreSQL or automatic-login identity fixture. It is a configuration starting point,
not a deployed service. An authorized cluster, registry, DNS/TLS and managed database
must be supplied before deployment. Keep a separate explicit hosted kubeconfig.

1. Set immutable registry image digests in a site-specific Kustomize overlay. Build
   from the reviewed commit and publish to the operator's authorized registry.
2. Replace all `example.invalid` and `configure-client-id` values: `APP_ORIGIN`,
   issuer, audience/client ID, authorization/token/JWKS URLs, gateway `PUBLIC_HOST`,
   ingress rule and TLS hosts. Register the exact `/auth/callback` redirect URL.
3. Provision a supported PostgreSQL database and a TLS-verified `database_url` file
   using its managed endpoint. Use the provider's CA/`sslmode=verify-full` settings.
   Separate migration/runtime DB privileges where required by the deployment policy;
   the local fixture uses a bootstrap owner and does not demonstrate that separation.
4. Create namespaces and the referenced Secrets from protected files, for example
   `kubectl --kubeconfig <owned-config> -n agentops create secret generic database --from-file=database_url=<protected-file>`.
   Provision OIDC client secret and the TLS Secret similarly. Never put secret values
   in command arguments, Git, rendered manifests, evidence or terminal history.
5. Render the site overlay and run server-side dry-run. Apply service accounts,
   configuration and infrastructure, wait for DB connectivity, create a uniquely
   named migration Job and require success **before** applying new Deployments.
   Do not run the local-only `cluster.py deploy` against a hosted context.
6. Configure load-balancer/DNS routing, storage/log retention, encrypted Secret
   storage, network controls and monitoring for the target environment. Check actual
   readiness, authenticated execution, approvals and metrics before exposing users.

No hosted target/access has been supplied in this run. Local results cannot establish
managed-service availability, internet exposure controls, multi-node scheduling,
high availability, registry policy or disaster recovery for a hosted environment.

Ingress configuration follows the [Traefik Kubernetes Ingress provider](https://doc.traefik.io/traefik/reference/install-configuration/providers/kubernetes/kubernetes-ingress/).
Rollout fields follow [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/).
