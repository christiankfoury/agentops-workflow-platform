# Production container verification — Phase 100

## Result and scope

The final local production-mode acceptance passed on **2026-09-17,
05:59:09–06:01:47 UTC**: **9 accepted workflows, 9 completed workflows and 203
completed jobs**, with start deduplication, signed OIDC authentication, human
approval, restart persistence, dependency readiness and real container SIGTERM.
No provider or external effect was invoked. This is a disposable Docker Compose
deployment, not a hosted or Kubernetes deployment.

- [Final manifest](evidence/phase100-final/summary.json) identifies accepted runs,
  image IDs, source base and SHA-256 of the
  [lossless raw archive](evidence/phase100-final/verification.json.gz).
- [Independent review](evidence/phase100-final/independent-review.json) recomputed
  the archive hash and run/job reconciliation, matched all **195 recorded source
  fingerprints**, checked the published definition appeared in authenticated
  server-rendered HTML, and inspected actual container configuration.
- [Active checkpoint drain](evidence/phase100-final/active-drain.json) separately
  proves shutdown while a job really owns a lease. The fixture observes the
  draining heartbeat, releases a bounded database lock, requires exit 0 and the
  original job completed with zero lease recoveries, then completes the queued
  continuation. The record includes the exact fixture source hash.
- The [repeat with the final fixture CLI](evidence/phase100-final/active-drain-recheck.json)
  passed again on a separate accepted execution, including the same active-lease
  drain and two completed jobs. The principal suite plus these two checks accepted
  **11 runs and reconciled 207 completed jobs**; earlier failed attempts are separate.

The principal run used source base
`894f3429153c867fd9dc1e21fc99d0bbfd07dbf4` plus the Phase 100 working-tree change.
Runtime/deployment fingerprints in the archive identify the measured code before
its implementation commit. The additional active-drain fixture has its own source
fingerprint. Commit, CI and post-push review references are maintained in
[phase progress](phase-progress.md).

## Verified behavior

| Check | Observed result |
| --- | --- |
| Production builds | API/worker image, Node 24.21.0 standalone web image and unprivileged Caddy gateway built successfully |
| Database initialization | Fresh named volume migrated through `f097_worker_presence` before application startup |
| Authentication | HTTPS certificate verified against the ephemeral test CA; authorization code, PKCE, state/nonce, RS256 token verification and secure HttpOnly session cookie completed |
| Negative access | Unauthenticated definitions returned 401; untrusted gateway Host returned 421 |
| Version and approval | Published version remained pinned; approved payload `{value: 42}` produced the expected output |
| Persistence | API/web/worker/database restart retained run output, exact approval record and usable session |
| Dependency failure | Stopping owned PostgreSQL produced API/web readiness 503 while API liveness remained 200; recovery restored readiness |
| Stop future claims | SIGTERM exited 0 with eight queued jobs, no running jobs and stable claim count while stopped; restart completed all eight 24-node runs |
| Drain active ownership | Separate bounded checkpoint-lock fixture observed a running job and draining heartbeat; SIGTERM waited for release and exited 0; the original job completed without recovery |
| Runtime configuration | API/worker 768 MiB and 1 CPU each; web 512 MiB and 1 CPU; gateway 128 MiB and 0.5 CPU; all four healthy, non-root, read-only, init enabled, all capabilities dropped, no privilege escalation, rotating logs |
| Image/config safety | No generated secret in image metadata/history; no `.env*` or private `.key` file under application image `/app`; no application source bind mounts; provider key/destinations empty |

The main SIGTERM sample had queued work at its observation boundary, so it is
not used to claim an active checkpoint drained. The separate active-drain record
provides that evidence. PostgreSQL's 45-second idle transaction deadline releases
the controlled fixture lock if the test client disappears. It is confined to the
owned disposable stack and must not be run against shared data.

## Measured images

| Runtime | Image ID | Runtime user |
| --- | --- | --- |
| API and worker | `sha256:79094b95a6545fb9d613c31a956bdab5550e15745519a5026ddcad1ba52dacda` | `10001:10001` |
| Web | `sha256:c8edb5357ca5b00335fd04d758af29c5264bee26c5d0a5523be96f0cda42bcfb` | `node` |
| Gateway | `sha256:e5cff3e4a6ce24770a5c13f5222e491e33c1f05b90a49c05017de0c66a916d37` | `10001:10001` |

Host: Windows 11 with Docker Desktop 27.2.0, a 16-logical-CPU Linux VM and about
7.7 GiB allocated VM memory. The profile uses PostgreSQL 16, Python 3.12,
Next.js 16.3.3, Caddy 2.10.2 and locked application dependencies. Runtime limits
above are configuration bounds, not measured peak consumption or throughput.

## Failures found and corrected before commit

1. A first focused-test command named a nonexistent test file and ran no tests.
   The corrected run passed 41 tests with one setup error: a fixture `CREATE TABLE`
   exceeded its ten-second statement deadline during concurrent image building.
   A repeat passed **42/42 in 300.11s**. After the worker fix, its affected queue,
   lease, presence and operations suite passed **33/33 in 207.35s**.
2. Frontend lint rejected CommonJS imports in the new launcher. The ESM launcher
   passed lint and **65 smoke tests**; typecheck and actual production build passed.
3. Caddy's base binary retained a low-port file capability, conflicting with the
   dropped capability set. The gateway image removes that capability, uses
   unprivileged ports, and has a real health probe. Scratch-directory ownership
   was corrected; startup success alone was not treated as health evidence.
4. The [first archived attempt](evidence/phase100/summary.json) rejected a host
   check because Caddy reordered the proxy before the rejection handler. An
   explicit `route` now preserves rejection-first evaluation, following
   [Caddy's route semantics](https://caddyserver.com/docs/caddyfile/directives/route).
5. The [second attempt](evidence/phase100-recheck/summary.json) passed signed login
   but found an HTTPX fixture lifecycle error; the already-open client now closes
   correctly without entering twice.
6. The [third attempt](evidence/phase100-acceptance/summary.json) passed workflow,
   approval, restart and outage checks, but SIGTERM arrived during worker startup
   and the container needed a forced kill. Old hostname-based presence could also
   satisfy readiness during restart. Runtime containers now use an init process;
   the worker entrypoint replaces its instance identity before imports, and health
   requires that exact identity. A regression rejects an old live heartbeat.
   All nine runs from that earlier attempt subsequently completed and remain in
   the disposable database; failed evidence was retained, not relabeled.

An account usage/automatic-approval interruption briefly prevented additional
commands. Work resumed after account status and successful command execution
confirmed access was available. No validation success was inferred from that wait.

## Reproduce and limits

Follow [production container setup](PRODUCTION_CONTAINERS.md). Use a new output
directory for each run; the committed artifacts are immutable prior evidence.
The main verifier and active-drain fixture intentionally exercise different
shutdown boundaries. Preserve the named database volume to inspect results.

These checks use a synthetic, private OIDC provider and short-lived local TLS
certificates. They prove the configured protocol path and tenant-backed runtime,
not integration with an external identity vendor. No paid model, external HTTP
effect, hosted account, Kubernetes rollout, network policy, production database
role separation or OS-image vulnerability assessment is claimed. Application
dependency audits and full regression CI remain separate delivery gates.
