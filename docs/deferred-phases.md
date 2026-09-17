# Deferred work and adopted backlog

The [platform plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md) owns R01–R14 scope;
[phase progress](phase-progress.md) owns completed commits, CI and review. This
backlog does not authorize further implementation or external deployment.

## Adopted work delivered in Phases 66–102

| Earlier backlog item | Implemented scope | Contract / evidence |
| --- | --- | --- |
| Identity and organizations | Verified OIDC/session boundary, users/memberships, tenant ownership | [Identity](IDENTITY.md), Phases 67–68 |
| Permissions and audit | Server-owned roles/scopes, decision-time authorization, transactional audit | [Identity permissions](IDENTITY.md), Phases 69/80 |
| Background jobs | Durable queue, leases, fencing, recovery, retries and cancellation | [Queue](DURABLE_QUEUE.md), Phases 75–78 |
| Live updates and worker visibility | Bounded polling, tenant operations, presence and metrics | [Operations](WORKER_OPERATIONS.md), Phase 97 |
| Deployment | Production images, migration/probe/secret configuration and local Kubernetes | [Deployment](DEPLOYMENT.md), Phases 100–101 |
| Recovery verification | Local rollout/scaling, loss/fencing, readiness, backup/restore and rollback | [Measured results](KUBERNETES_OPERATIONS_RESULTS.md), Phase 102 |

Old conflicting backlog phase numbers are retired; canonical definitions remain
[Phases 66–105](phases.md#platform-expansion-planned-phases-66105). Documentation,
demo script and case study are Phases 103–105, with their status in the ledger.

## Remaining optional product work

- **Notifications:** general subscription/in-app center for completion, approval,
  failure and evaluation events; email/Slack delivery. Configured workflow actions
  are not a general notification service.
- **Evaluation caching:** reuse by case, prompt, model/settings and policy with
  visible cache provenance. Start idempotency only suppresses retries of one
  accepted request; it does not merge intentionally separate identical inputs.
- **Advanced judging:** a separately validated rubric/semantic evaluator. Existing
  deterministic scoring is retained; no live evaluator-agent call is claimed.
- **Additional connectors/business templates:** beyond HTTP, restricted PostgreSQL,
  GitHub issues and the three shipped business examples.
- **Operational extensions:** hosted account/identity acceptance, multi-node and
  managed-database failover, target-specific backups/recovery objectives and
  external tracing/metrics infrastructure.

## Explicit boundaries

Arbitrary uploaded code execution, billing, a general autonomous agent framework,
and every possible SaaS integration are outside this delivery. Production
security certification and comparative live-provider quality gains are not
established by local fixtures or seeded demonstrations. Hosted validation needs
an authorized target and access; the required local acceptance is recorded.
