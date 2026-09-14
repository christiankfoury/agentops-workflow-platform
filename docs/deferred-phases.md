# Deferred Work and Adopted Backlog

This file distinguishes remaining optional work from backlog items now assigned
to the [platform implementation phases](phases.md#platform-expansion-planned-phases-66105).
The [consolidated plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md) owns scope.
Nothing here starts an autonomous run.

The old phase numbers in this file conflicted with completed Phases 54–64 and
referenced a different deployment sequence. They are historical labels only;
the active future sequence is Phases 66–105.

## Existing Capabilities

- API-key authentication, prototype viewer/operator/admin checks, input limits,
  and basic rate limiting exist. They are not user identity or real tenant-aware RBAC.
- Workflow events and editable human approvals exist. Authenticated actor audit
  and membership-backed approval authorization still need implementation.
- Local Compose, health checks, CI, evaluation, and demo data exist. Durable
  workers, a production Kubernetes deployment, and operational evidence remain planned.

## Adopted into the Platform Plan

These are references to the canonical phases, not a second implementation backlog.

| Historical item | Delivery in the new sequence |
| --- | --- |
| Authentication (old 54) | Phase 67: verified identity/session boundary |
| User/organization model (old 55) | Phases 67–68: users, memberships, ownership, and tenant isolation |
| Role permissions (old 56) | Phase 69: server-authoritative viewer/operator/reviewer/admin roles |
| Approval permissions (old 57) | Phases 69 and 80: reviewer/admin decisions, admin high-severity overrides, exact-input authorization |
| Audit trail (old 58) | Phase 69, extended by later resources: starts, approvals/edits/rejections, prompts/settings, exports, membership |
| Background jobs (old 59) | Phases 75–78: durable queue, workers, leases, recovery, retry, cancellation |
| Live workflow updates (old 60) | Phase 97: bounded polling and reconnect/error handling |
| Queue/worker observability (old 61) | Phases 75–76 and 97: job state, heartbeats, worker metrics, queue latency |
| Deployment setup (old 75) | Phases 100–101: production images/configuration, migrations, health, Kubernetes |
| Deployment/operation (old 76) | Phase 102: local-cluster verification and separately authorized hosted validation |

The prior suggestions of in-process background tasks or caller-selected roles
do not satisfy the new durability and identity requirements. Current runtime
limitations remain documented until their replacement phases pass acceptance.

## Remaining Deferred: Notifications

A standalone in-app notification center for workflow completion, pending approval,
workflow failure, and evaluation completion remains optional. Email and Slack
notifications may follow later. A configured action through the planned tool
executor is different from a general notification subscription system.

## Remaining Deferred: Evaluation Caching and Duplicate-Input Hints

The old caching item proposed reusing evaluations with identical case, prompt
version, model/settings, and other relevant configuration, plus showing cache hits
or duplicate-input warnings. This optimization remains deferred.

Run-start idempotency in Phase 73 suppresses retries of the same accepted request;
it does not implement evaluation-result caching or merge intentionally distinct
runs with identical input.

## Remaining Deferred: Advanced LLM Judge

An additional rubric-based evaluator for factual accuracy, completeness, clarity,
business usefulness, and unsupported claims remains outside this sequence.
Retain the existing deterministic evaluations and stored quality evidence.

## Scope Boundaries

Additional business workflows, SaaS connectors beyond the three chosen tool
integrations, arbitrary uploaded code execution, billing, and extra notification
channels are not implied by Phases 66–105. A public hosted rollout can be performed
during Phase 102 when the user supplies an authorized target/access; local
Kubernetes verification is the required reproducible acceptance path.
