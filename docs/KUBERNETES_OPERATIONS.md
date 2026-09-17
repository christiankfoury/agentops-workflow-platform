# Kubernetes operations verification

This runbook exercises **only the owned local kind cluster** established by
[KUBERNETES.md](KUBERNETES.md). It intentionally interrupts synthetic work and
temporarily stops its database. Never target a hosted cluster, a shared database,
or a namespace containing other users' workloads with this harness.

## Prepare and run

Complete Phase 101 deployment and authenticated verification first. Keep the
dedicated `.local/kubernetes/kubeconfig` and unexpired synthetic TLS/OIDC fixture.
The cluster must have no unrelated work; every accepted request in this experiment
is synthetic. Its PostgreSQL PVC and the earlier Compose database are retained.

```powershell
$revision = git rev-parse HEAD
uv run --directory apps/api pytest tests/test_operations_sink.py
docker build -f deploy/kubernetes/operations/Dockerfile.sink -t agentops-operations-sink:phase102 deploy/kubernetes/operations
docker build -f deploy/kubernetes/operations/Dockerfile.release --build-arg RELEASE_REVISION=$revision -t agentops-api:phase102-release deploy/kubernetes/operations
& .local/kubernetes/kind-v0.33.0.exe load docker-image agentops-operations-sink:phase102 agentops-api:phase102-release --name agentops-phase101
uv run --directory apps/api python ../../deploy/kubernetes/operations/run.py --output .local/kubernetes/operations
```

Check each exit status before continuing. A new output directory is required on
each run; failure evidence is never overwritten. The harness verifies kind labels,
the dedicated context and loopback API endpoint before mutation. It changes only
the owned `agentops` resources and creates a fresh restore database.

The release image has distinct packaging metadata and the **same application code
and schema** as the Phase 101 API image. This tests compatible rollout/rollback
mechanics. It does not claim a database downgrade or an arbitrary application
version upgrade was verified. The web image stays at its verified Phase 101 build.

## Controlled effect fixture

The [operations profile](../deploy/kubernetes/operations/kustomization.yaml) is
explicitly separate from local/hosted application profiles. It adds an internal
HTTP sink with a persistent SQLite ledger on its own PVC. No ingress route or
host port exposes it. The harness configures one tenant destination alias with
the sink Service's exact private IP `/32`, POST only, explicit local plain HTTP
and a one-hour idempotency guarantee. Paid providers stay disabled.

The sink atomically persists a receipt before acknowledging a request. Repeated
keys with identical payloads return the same result; changed payloads conflict.
Controlled delayed/held responses expose the boundary between an accepted remote
write and a locally recorded result. Concurrency, unacknowledged receipt reuse,
conflict rejection and server restart persistence have focused tests.

This guarantee belongs to the fixture. Arbitrary external services may accept a
write without providing durable idempotency or reconciliation; those outcomes
remain uncertain under the platform's existing effect policy.

## Experiments and required observations

1. **Baseline:** authenticated publication, duplicate start request, approval and
   one completed HTTP write establish the receipt relationship.
2. **Rolling release:** update API and worker images while approved work is active;
   record HTTP availability samples, wait for rollouts, reconcile every accepted run.
3. **Scaling:** use three registered worker replicas, complete a batch and return
   to one. This is an operations check, not a throughput benchmark.
4. **Active Pod loss:** remove the owner after the sink persisted a write but before
   the response completed. Require lease recovery and one final external receipt.
5. **Stale owner:** pause the worker process, start a replacement, let the original
   lease expire naturally and complete recovery. Resume the old process and require
   its late result to be discarded while completed history remains unchanged.
6. **Dependency readiness:** retain accepted approval waits, stop PostgreSQL and
   inspect API/web directly inside their Pods. Health must remain 200 and readiness
   become 503. Restore PostgreSQL, finish approvals and reconcile the accepted work.
   The worker may exit/restart on a DB exception; this is recorded separately from
   readiness and does not imply that liveness killed it.
7. **Backup/restore:** quiesce workers, require no active durable jobs, create a
   custom-format PostgreSQL backup and restore into a new owned database. Compare
   version, approval, execution, attempt, job, event and tool/effect history.
   Replace the sink Pod and verify its separate persistent receipt ledger.
8. **Compatible rollback:** restore the exact known API/worker image tags, verify
   readiness and complete another approved write. Reconcile all suite run IDs and
   effect keys against the sink, including the extra requests caused by recovery.

The summary is written as requests are accepted. Any failed assertion leaves
`passed: false`; cleanup attempts to resume a paused worker and restore DB/worker
availability. Inspect the preserved output, accepted IDs and cluster state before
retrying. Do not turn a failed local check into a successful deployment claim.
The synthetic identity fixture issues five-minute tokens; the harness signs in
again between cases and reconciliation passes without changing session expiry
rules. Intermediate deployment/replica snapshots and final worker metrics are
retained with the results.

## Backup and rollback boundaries

The harness streams `pg_dump --format=custom` bytes directly to an ignored file,
then streams that file to `pg_restore --exit-on-error --no-owner --no-acl` in a
fresh database. It never uses PowerShell text redirection for the binary archive
and never overwrites or drops the original database. The evidence records the
archive hash/size, restored database name, table counts and content hashes.
History exports omit internal claim/reservation tokens and credential digests.

PostgreSQL's [pg_dump documentation](https://www.postgresql.org/docs/16/app-pgdump.html)
describes consistent single-database snapshots and custom archives;
[pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html) restores those
archives. This check does not back up cluster roles, Kubernetes Secrets, registry
images or an external provider's data. Keep those in the deployment's separate
recovery plan. Backups and restored databases here are retained for inspection.

The rollback uses the already verified compatible application/schema pair. For a
real release with schema changes, review compatibility and migration strategy
before an image rollback; this harness authorizes no destructive schema reversal.

Hosted operational verification remains unperformed because no authorized hosted
target/access was supplied. Local results do not establish multi-node availability,
managed-service failover, internet exposure policy or hosted disaster recovery.
