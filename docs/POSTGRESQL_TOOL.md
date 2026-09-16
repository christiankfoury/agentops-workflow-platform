# PostgreSQL query tool

Phase 88 adds the `postgresql` adapter to the [tool effect ledger](TOOL_CONTRACTS.md).
Only server-registered SELECT queries can run. A workflow selects connection and
query aliases; it cannot supply SQL, a DSN, a role, TLS options or a password.

## Operator configuration

Set `POSTGRES_TOOL_CONNECTIONS` on the API and worker to a JSON object keyed by
`<organization UUID>/<connection alias>`. The default `{}` disables data access.
Each entry has this shape (replace the example identifiers and certificate path):

```json
{
  "host": "data.internal.example",
  "hostaddr": "10.20.0.5",
  "port": 5432,
  "database": "reporting",
  "user": "workflow_reader",
  "credential_alias": "reporting-reader",
  "sslmode": "verify-full",
  "sslrootcert": "/run/certs/data-ca.pem",
  "max_rows": 100,
  "max_result_bytes": 64000,
  "statement_timeout_ms": 5000,
  "queries": {
    "sales-by-region": {
      "sql": "SELECT region, revenue::text AS revenue FROM reporting.sales WHERE organization_id = %(_organization_id)s AND region = %(region)s"
    }
  }
}
```

`hostaddr` pins a numeric address without DNS lookup during dispatch. `host` is
the TLS verification name. TLS defaults to `verify-full` with an explicit root
certificate; `disable` is an explicit operator option for disposable local fixtures.
Other TLS modes are rejected. PostgreSQL 16 is the tested target.

Use a **separate data database and restricted login**, with SELECT grants only on
approved objects. The source database name and user must both differ from
`DATABASE_URL`; the adapter never uses the application's connection or pool.
Revoke PUBLIC database CREATE/TEMP privileges and grant only CONNECT to the data
role. Allow schema USAGE, with no schema CREATE, table/column mutation, sequence
USAGE/UPDATE, elevated role attributes or role memberships. The worker checks
these restrictions on every fresh connection before executing the query.

Operators own the SQL registry and data permissions. Review all views, functions,
extensions and cross-database access reachable by the role; registered SQL is
trusted server configuration. The lexical SELECT guard is intentionally restrictive
and is not a general SQL sandbox. Read-only transactions prohibit database writes,
but PostgreSQL extensions/functions can have effects outside their own database.
Do not grant access to such functions. Use a dedicated database/role per tenant or
audited organization filters/RLS. The adapter supplies `%(_organization_id)s` from
the authenticated execution; callers cannot override it.

Create a catalog credential reference with source alias `reporting-reader`. Supply
its password through the worker-only `TOOL_CREDENTIAL_VALUES` key
`<organization UUID>/reporting-reader`. No password belongs in the configuration
above, workflow graph, registered SQL, API body or logs. Publication binds the server
policy fingerprint; policy changes require a new workflow publication. Revocation
and credential rotation use the shared worker dispatch and effect fences.

## Contract and results

Use a catalog contract with `adapter: "postgresql"`, `side_effecting: false`, a
credential reference, input/output schemas, and:

```json
{"connection": "reporting", "query": "sales-by-region"}
```

The graph tool config also sets `adapter: "postgresql"`, `tool_id`, and the pinned
contract `version`. Input properties must exactly match named SQL parameters,
excluding `_organization_id`. Values can be JSON scalars or null and are passed
through psycopg2 parameter binding. Lists/objects, positional parameters, comments,
multiple statements and write/DDL query shapes are rejected. Do not quote parameter
placeholders; use fully qualified table names because `search_path` is `pg_catalog`.

Results have shape `{"rows": [{"region": "East", "revenue": "1200.50"}], "row_count": 1}`.
Declare a closed object schema for each row. Give every selected column a unique
name. PostgreSQL JSON conversion defines type representation; cast large numeric
identifiers or exact decimals to text when lossless downstream representation matters.
The shared executor validates the result schema and redacts sensitive field names
and the resolved secret before retaining receipts. Errors retain only shared error
codes; SQL, provider error detail, connection strings and credentials are not retained.

## Limits and recovery

- Eight data connections maximum per worker process; saturation returns
  `tool_unavailable`. Each call closes its connection; it never commits.
- `max_rows` is 1–1,000; `max_result_bytes` is 128–120,000. Exceeding either fails
  with `tool_response_invalid`, rather than silently truncating data.
- An SQL cursor fetches one bounded JSON row at a time. Oversized cells are replaced
  with a sentinel on the server before transmission and rejected by the client.
  Serialized output is checked again against the byte limit and shared depth limit.
- Statement limits are 10–30,000ms, additionally bounded by the remaining tool,
  attempt and workflow deadline. A monotonic total deadline bounds all fetches;
  statement limits alone would restart on each fetch.
- Async libpq polling checks cancellation/deadlines every 50ms while waiting.
  Cancellation closes the connection on its owning thread. Server statement/idle
  timeouts and `client_connection_check_interval=100ms` bound orphaned work; prompt
  disconnect detection depends on OS support. Local Linux fixtures verify cleanup.
- Timeouts map to `tool_timeout`; availability/resource/serialization failures map
  to `tool_unavailable`; permission/read-only errors map to `tool_denied`. Invalid
  parameters/results are permanent. Authentication failures without libpq SQLSTATE
  map conservatively to availability errors, with bounded shared retries.
- Reads can retry after a lost response and may observe newer data. Successful
  receipts are reused by the effect ledger; cancellation still fences workflow output.

These limits bound client transfer and retained output. Operators must also size
the data server and review query plans: a large aggregation or row conversion can
consume server resources before a result is returned.

## Validation

Set `WORKFLOW_TEST_DATABASE_URL` to an **owned disposable PostgreSQL test service**
whose fixture administrator can create/drop databases and roles, then run:

```powershell
uv run --directory apps/api pytest tests/test_postgres_tool.py tests/test_postgres_tool_runtime.py -q
```

The tests create a random separate database and restricted login, prove tenant
filters, injection denial, permissions, limits, statement timeouts, cancellation,
cleanup, worker redaction/revocation, schema mismatch and read retry behavior, and
drop only fixture-owned resources. They do not validate a live production data
source or hosted deployment. No new migration is required.

Implementation references: [psycopg asynchronous support](https://www.psycopg.org/docs/advanced.html#asynchronous-support),
[PostgreSQL read-only transactions](https://www.postgresql.org/docs/16/sql-set-transaction.html),
[SQL cursors](https://www.postgresql.org/docs/16/sql-declare.html), and
[server timeouts](https://www.postgresql.org/docs/16/runtime-config-client.html).
