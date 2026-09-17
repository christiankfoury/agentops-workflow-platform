# Local Kubernetes deployment results

Phase 101 local acceptance passed on **2026-09-17, 07:29:11–07:30:17 UTC**.
This is a real disposable kind deployment with synthetic identity and deterministic
workflows. No hosted cluster or paid model provider was used.

## Environment and provenance

- Owned cluster: `agentops-phase101`; application namespace `agentops`, ingress
  namespace `agentops-ingress`. Kubernetes **v1.37.0**, containerd **2.3.4**,
  Debian 13 node on Docker Desktop/WSL2. kind **v0.33.0** and pinned node digest
  are recorded in the [acceptance manifest](evidence/phase101/summary.json).
- Source base: `753daaace23675032af348263deeeacbbe074a2d` plus the Phase 101 working
  changes. The manifest retains **33 normalized source hashes**, image IDs and
  first/latest migration Job IDs. Image revision labels identify the base commit,
  not a subsequently created implementation commit; gateway reuses the measured
  Phase 100 image. Hashes and Git history identify the tested changes.
- Dedicated kubeconfig; loopback HTTPS ingress on port 8443. The Phase 100 services
  were stopped to free the port; their named database volume was retained. Existing
  preview/benchmark databases and the user's default kubeconfig were preserved.
- Local profile uses a persistent PostgreSQL PVC and the explicit automatic-login
  OIDC fixture. Hosted profile passed rendering and server schema validation only.

## Observed acceptance

| Check | Observed result |
| --- | --- |
| Ordered migration | Fresh Job migrated through `f097_worker_presence` before application Pod creation; subsequent migration was a successful no-op. |
| Routing/authentication | Real TLS ingress, PKCE login, secure HttpOnly session, unauthenticated API 401 and unknown ingress host 404. |
| Published workflow | Run `c6bc94fc-6515-4681-91b8-708afcf15791` pinned version `f355bba2-cff1-4d95-8de8-74c3f54c825b`; repeated start request returned the same run. |
| Human approval | Approval `f7786bd0-c399-4c29-abf2-1a3f19489719` approved its retained payload hash; completed output was `{"value":42}`. |
| UI | Authenticated server-rendered definition list contained the published definition. |
| Persistence | Database, API and worker Pods were deleted/recreated with different UIDs. PVC UID stayed `f8dce1c4-7c2c-4d37-a98a-7c41d1f9cc26`; output, version, approval and session remained valid. |
| Metrics | Operator CronJob exported 1 completed run, 3 completed jobs, 2 completed attempts, 3 claims, 1 running worker, 0 stale jobs, 0 lease recoveries and 0 abandoned attempts. Tenant metrics returned HTTP 200. |
| Pod controls | Recorded Pods had no application API token, non-root execution, read-only roots, dropped capabilities, no privilege escalation, and resource requests/limits. |
| RBAC | Live authorization checks denied Secret listing to the runtime account and denied ingress Secret listing in `agentops`; ingress could list Secrets in `agentops-ingress`. |

These are one-workflow deployment checks, not throughput measurements or fault
recovery benchmarks. Metrics are in [worker-metrics.txt](evidence/phase101/worker-metrics.txt).

## Validation and corrections

- Both profiles rendered and passed Kubernetes server-side dry-run. All final
  Deployments reached readiness; migration Jobs completed successfully.
- Production-runtime tests: **5 passed in 99.21s**. Web tests: **66 passed**,
  including Kubernetes-without-Docker-marker routing, Docker routing, native
  development fallback and explicit private API URL behavior. Typecheck, lint,
  deployment-script Ruff and production image builds passed.
- The first API build used the repository root instead of the API build context;
  the corrected command passed. The first helper render assumed a single JSON
  object; it now decodes kubectl's multi-object output. Neither attempt started
  application workloads prematurely.
- The first web rollout failed readiness because `/.dockerenv` is absent under
  containerd. Kubernetes environment detection fixes the internal API URL fallback.
  The rebuilt image `agentops-web:kubernetes-v2` passed actual readiness and the
  full authenticated acceptance. Failed rollout logs are retained, not relabeled
  as successful checks. Cold image pulls/imports were allowed to finish.
- Independent inspection matched all 33 source hashes and the raw evidence SHA,
  reconciled run/approval/version IDs and inspected actual Pod security/resources.
  Documentation links/fences and `git diff --check` passed.

## Evidence and limits

- [Acceptance manifest](evidence/phase101/summary.json).
- [Lossless cluster/image/Pod/migration archive](evidence/phase101/cluster-evidence.json.gz),
  SHA-256 `a85a019ac59548046e417d275a2168fce842ef249777a2b918bdf3127cab20a3`.
- [Independent review](evidence/phase101/independent-review.json) and
  [validation logs, including failed attempts](evidence/phase101/validation-logs.json.gz).
- [Deployment and secret-provisioning runbook](KUBERNETES.md).

The fixture demonstrates local ingress, authentication, persistence and deployment
configuration. It does not demonstrate multi-node availability, a managed database,
external identity administration, network-policy isolation, image CVE scanning or
hosted security posture. The local database uses a bootstrap owner. Operator metrics
are exported to Job logs; no Prometheus stack is installed. Rollout/scaling fault
reconciliation, backup/restore and compatible rollback are Phase 102 work.

Commit, CI and post-push review outcomes are maintained in
[phase-progress.md](phase-progress.md); local acceptance alone does not complete
the phase delivery gate.
