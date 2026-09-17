# Platform requirement evidence

This index maps every requirement in the [consolidated plan](../WORKFLOW_PLATFORM_IMPLEMENTATION_PLAN.md)
to implementation and acceptance evidence. The [phase ledger](phase-progress.md)
is authoritative for commit IDs, fixes, pushes, CI and review. Test files identify
reproducible checks; a link alone is not a claim that a new test run occurred.

## R01–R14 coverage

| Requirement | Delivered contract and source | Validation / recorded evidence |
| --- | --- | --- |
| R01 — definitions, versions, branching | [Graph/version contract](WORKFLOW_GRAPH.md), [definition service](../apps/api/src/services/workflow_definitions.py); Phases 70–71, 74, 82–85 | [Version tests](../apps/api/tests/test_workflow_definitions.py), [interpreter tests](../apps/api/tests/test_graph_interpreter.py), [business migration](BUSINESS_TEMPLATES.md) |
| R02 — generic records and eight primitives | [Execution records](EXECUTION_RECORDS.md), [registry](../apps/api/src/services/execution_registry.py); Phases 70, 72, 74, 79–82, 86–90 | [Record tests](../apps/api/tests/test_execution_records.py), [parallel tests](../apps/api/tests/test_parallel_runtime.py), [LLM tests](../apps/api/tests/test_llm_execution.py), adapter checks below |
| R03 — centralized state transitions | [State authority](../apps/api/src/services/workflow_state.py), [transactions](../apps/api/src/services/workflow_transactions.py); Phases 66, 72, 76 | [PostgreSQL transaction races](../apps/api/tests/test_workflow_transactions_postgres.py), [record invariants](../apps/api/tests/test_execution_records.py) |
| R04 — durable jobs and ownership | [Queue/leases](DURABLE_QUEUE.md), [worker](../apps/api/src/worker.py); Phases 75–76 | [Queue tests](../apps/api/tests/test_durable_queue.py), [lease tests](../apps/api/tests/test_worker_leases.py), [fault measurements](RELIABILITY_RESULTS.md) |
| R05 — cancellation | [Cancellation authority](../apps/api/src/services/execution_cancellation.py), [controls](WORKFLOW_RECOVERY.md); Phase 78 | [Cancellation races and I/O abort](../apps/api/tests/test_execution_cancellation.py), [fault measurements](RELIABILITY_RESULTS.md) |
| R06 — retries and deadlines | [Retry policy](RETRIES_AND_DEADLINES.md), [quality revisions](LLM_EXECUTION.md), [explicit recovery](WORKFLOW_RECOVERY.md); Phases 77, 82, 96 | [Retry tests](../apps/api/tests/test_retry_runtime.py), [LLM tests](../apps/api/tests/test_llm_execution.py), [recovery tests](../apps/api/tests/test_execution_recovery.py) |
| R07 — start/effect idempotency | [Start contract](EXECUTION_RECORDS.md#idempotent-starts-phase-73), [effect ledger](TOOL_CONTRACTS.md); Phases 73, 86 | [Concurrent starts](../apps/api/tests/test_execution_starts.py), [effect tests](../apps/api/tests/test_tool_effects.py), [sink reconciliation](KUBERNETES_OPERATIONS_RESULTS.md) |
| R08 — tools and governed LLM calls | [HTTP](HTTP_TOOL.md), [PostgreSQL](POSTGRESQL_TOOL.md), [GitHub](GITHUB_TOOL.md), [LLM tools](LLM_TOOL_CALLING.md); Phases 86–90 | [HTTP runtime](../apps/api/tests/test_http_tool_runtime.py), [PostgreSQL runtime](../apps/api/tests/test_postgres_tool_runtime.py), [GitHub runtime](../apps/api/tests/test_github_tool_runtime.py), [LLM tools](../apps/api/tests/test_llm_tools.py); fixtures, not live account acceptance |
| R09 — identity, tenants, RBAC, approvals | [Identity/permissions](IDENTITY.md), [approval service](../apps/api/src/services/approval_runtime.py); Phases 67–69, 80 | [Identity](../apps/api/tests/test_identity.py), [tenant isolation](../apps/api/tests/test_tenant_isolation.py), [permissions/audit](../apps/api/tests/test_permissions_audit.py), [exact approvals](../apps/api/tests/test_execution_approvals.py), [deployed synthetic OIDC](KUBERNETES_RESULTS.md) |
| R10 — manual, webhook, cron | [Manual starts](WORKFLOW_BUILDER.md), [webhooks](WEBHOOK_TRIGGERS.md), [schedules](SCHEDULED_TRIGGERS.md); Phases 73, 91–92 | [Start](../apps/api/tests/test_execution_starts.py), [webhook](../apps/api/tests/test_webhooks.py), [schedule](../apps/api/tests/test_schedules.py), [cron](../apps/api/tests/test_cron_schedule.py) tests |
| R11 — builder, debugger, operations | [Builder](WORKFLOW_BUILDER.md), [debugger](WORKFLOW_DEBUGGER.md), [controls](WORKFLOW_RECOVERY.md), [live operations](WORKER_OPERATIONS.md); Phases 93–97 | [Web interaction suites](../apps/web/tests), [trace tests](../apps/api/tests/test_execution_traces.py), [operations tests](../apps/api/tests/test_operations.py); browser acceptance in phase ledger |
| R12 — scale and failure evidence | [Benchmark method](BENCHMARK.md), [fault method](RELIABILITY_EXPERIMENTS.md); Phases 98–99 | [10,000-run results](BENCHMARK_RESULTS.md), [45 fault cases and separate 15-case fix validation](RELIABILITY_RESULTS.md), hashed raw archives linked from both |
| R13 — deployment and operations | [Production containers](PRODUCTION_CONTAINERS.md), [Kubernetes profiles](KUBERNETES.md), [operations harness](KUBERNETES_OPERATIONS.md); Phases 100–102 | [Container results](PRODUCTION_CONTAINER_RESULTS.md), [cluster acceptance](KUBERNETES_RESULTS.md), [rollout/recovery/restore](KUBERNETES_OPERATIONS_RESULTS.md); local complete, hosted unperformed |
| R14 — accurate positioning and delivery story | [README](../README.md), [overview](overview.md), [specification](PROJECT_SPEC.md), [architecture](ARCHITECTURE.md), [demo script](DEMO_SCRIPT.md) and [reproducible walkthrough](demo-walkthrough.md); Phases 103–105 | Phase 103 reconciles documentation; Phase 104 adds the scripted walkthrough and local fixture. The final case study remains Phase 105. Completion/CI is recorded in the phase ledger. |

## Evidence classes

- **Implemented/tested:** source plus focused deterministic tests and recorded CI.
  PostgreSQL race/migration checks use disposable real databases.
- **Measured local execution:** benchmark, injected faults, container and kind
  runs have command/seed/environment, accepted IDs, source/image hashes and raw
  reconciliation. Counts are specific to those experiments and their denominators.
- **Seeded illustration:** demo records assign output, quality, cost and latency
  values for UI exploration. They are not live provider observations.
- **Unperformed:** hosted target, production identity-provider/account acceptance,
  paid LLM comparison, real GitHub write acceptance and multi-node failover.
  No optional external access is silently substituted with a fixture claim.

## Boundaries that remain true

Delivery is at least once. External effect safety depends on provider guarantees
and evidence; unknown outcomes remain explicit. Cancellation cannot reverse an
accepted remote write. The configured cost table estimates observed usage and
cannot reconstruct unreturned provider usage. Debugger payloads are bounded
previews, and redaction is not arbitrary-secret detection.

Local synthetic identity/TLS, container hardening and permission tests do not
constitute production security certification. The Phase 102 release changes
metadata, not application code/schema. Restore compares retained workflow/tool
history in a fresh database; it is not a complete cluster/Secret/provider disaster
recovery exercise. [Security](../SECURITY.md) and [deferred work](deferred-phases.md)
retain these distinctions.
