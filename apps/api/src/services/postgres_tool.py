"""Bounded asynchronous libpq reads on separate, restricted data connections."""

import json
import select
from threading import BoundedSemaphore
from time import monotonic

import psycopg2
from psycopg2 import extensions
from sqlalchemy.engine import make_url

from src.config import settings
from src.schemas.postgres_tool import PARAMETER, PostgreSQLConnection, PostgreSQLOptions
from src.schemas.tool import bounded
from src.services.tool_effects import ToolAdapter, ToolFailure, digest

CONNECTION_SLOTS = BoundedSemaphore(8)
ROLE_CHECK = """
SELECT current_database() = %s AND current_user = %s
 AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
 AND NOT EXISTS (SELECT 1 FROM pg_auth_members WHERE member = r.oid)
 AND NOT has_database_privilege(current_database(), 'CREATE')
 AND NOT has_database_privilege(current_database(), 'TEMP')
 AND NOT EXISTS (SELECT 1 FROM pg_namespace
                 WHERE left(nspname, 3) <> 'pg_' AND nspname <> 'information_schema'
                   AND has_schema_privilege(oid, 'CREATE'))
 AND NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                 WHERE left(n.nspname, 3) <> 'pg_' AND n.nspname <> 'information_schema'
                   AND ((c.relkind IN ('r','p','v','m','f')
                     AND (has_table_privilege(c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')
                          OR has_any_column_privilege(c.oid, 'INSERT,UPDATE')))
                    OR (c.relkind = 'S' AND has_sequence_privilege(c.oid, 'USAGE,UPDATE'))))
FROM pg_roles r WHERE rolname = current_user
"""


def source(organization_id, options):
    options = PostgreSQLOptions.model_validate(options)
    raw = settings.postgres_tool_connections.get(f"{organization_id}/{options.connection}")
    if raw is None:
        raise ToolFailure("tool_denied", uncertain=False)
    policy = PostgreSQLConnection.model_validate(raw)
    control = make_url(settings.database_url)
    if (
        policy.database == control.database
        or policy.user == control.username
        or options.query not in policy.queries
    ):
        raise ToolFailure("tool_denied", uncertain=False)
    return options, policy


def error_code(error):
    code = error.pgcode or ""
    if code == "57014":
        return "tool_timeout"
    if code.startswith("28") or code in {"42501", "25006"}:
        return "tool_denied"
    if code.startswith("22") or code == "42P02":
        return "tool_input_invalid"
    if code.startswith(("08", "53")) or code in {"40001", "40P01", "57P01"} or not code:
        return "tool_unavailable"
    return "tool_failed"


def request(policy, query, organization_id, *, arguments, secret, timeout_seconds, control, **_):
    parameters = set(PARAMETER.findall(query))
    if set(arguments) != parameters - {"_organization_id"} or any(
        not isinstance(value, (str, int, float, bool, type(None))) for value in arguments.values()
    ):
        raise ToolFailure("tool_input_invalid", uncertain=False)
    bounded(arguments)
    if not secret:
        raise ToolFailure("tool_denied", uncertain=False)
    if not CONNECTION_SLOTS.acquire(blocking=False):
        raise ToolFailure("tool_unavailable", uncertain=False)
    end, connection = monotonic() + timeout_seconds, None

    def remaining():
        control.raise_if_aborted()
        value = end - monotonic()
        if value <= 0:
            raise ToolFailure("tool_timeout", uncertain=False)
        return value

    def wait():
        while True:
            remaining()
            state = connection.poll()
            if state == extensions.POLL_OK:
                return
            select.select(
                [connection.fileno()] if state == extensions.POLL_READ else [],
                [connection.fileno()] if state == extensions.POLL_WRITE else [],
                [],
                min(0.05, remaining()),
            )

    def execute(cursor, sql, params=None):
        remaining()
        cursor.execute(sql, params)
        wait()

    try:
        milliseconds = max(1, min(policy.statement_timeout_ms, int(remaining() * 1000)))
        connection = psycopg2.connect(
            async_=True,
            host=policy.host,
            hostaddr=policy.hostaddr,
            port=policy.port,
            dbname=policy.database,
            user=policy.user,
            password=secret,
            sslmode=policy.sslmode,
            sslrootcert=policy.sslrootcert,
            sslcert="",
            sslkey="",
            gssencmode="disable",
            client_encoding="UTF8",
            application_name="agentops-postgresql-tool",
            options=f"-c default_transaction_read_only=on -c statement_timeout={milliseconds} "
            f"-c lock_timeout={milliseconds} -c idle_in_transaction_session_timeout={milliseconds} "
            "-c search_path=pg_catalog -c row_security=on -c work_mem=4MB "
            "-c client_connection_check_interval=100",
        )
        wait()
        with connection.cursor() as cursor:
            execute(cursor, "BEGIN READ ONLY")
            execute(cursor, ROLE_CHECK, (policy.database, policy.user))
            if cursor.fetchone() != (True,):
                raise ToolFailure("tool_denied", uncertain=False)
            # SQL is operator-owned. Only scalar values use driver parameters.
            params = {**arguments, "_organization_id": str(organization_id)}
            execute(
                cursor,
                "DECLARE tool_result NO SCROLL CURSOR FOR "
                "SELECT CASE WHEN octet_length(payload) <= "
                + str(policy.max_result_bytes)
                + " THEN payload ELSE NULL END FROM (SELECT row_to_json(data)::text AS payload "
                "FROM (" + query + ") data LIMIT " + str(policy.max_rows + 1) + ") bounded",
                params,
            )
            rows, size = [], 32
            while True:
                execute(cursor, "FETCH 1 FROM tool_result")
                item = cursor.fetchone()
                if item is None:
                    break
                if item[0] is None or len(rows) >= policy.max_rows:
                    raise ToolFailure("tool_response_invalid", uncertain=False)
                size += len(item[0].encode()) + 1
                if size > policy.max_result_bytes:
                    raise ToolFailure("tool_response_invalid", uncertain=False)
                rows.append(json.loads(item[0], object_pairs_hook=unique_object))
            remaining()
            result = bounded({"rows": rows, "row_count": len(rows)})
            if len(json.dumps(result, allow_nan=False).encode()) > policy.max_result_bytes:
                raise ToolFailure("tool_response_invalid", uncertain=False)
            return result
    except psycopg2.Error as error:
        raise ToolFailure(error_code(error), uncertain=False) from None
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ToolFailure("tool_response_invalid", uncertain=False) from None
    finally:
        # Async libpq cannot safely be closed concurrently by another thread.
        # Poll every 50ms, then close here; the server also has statement/idle
        # limits and disconnect checks. No transaction is ever committed.
        if connection:
            connection.close()
        CONNECTION_SLOTS.release()


def unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Query columns must have unique names")
    return result


def adapter(contract, organization_id, credential):
    options, policy = source(organization_id, contract.options)
    if credential is None or credential.source_alias != policy.credential_alias:
        raise ToolFailure("tool_denied", uncertain=False)
    query = policy.queries[options.query].sql
    if set(contract.input_schema.properties) != set(PARAMETER.findall(query)) - {
        "_organization_id"
    }:
        raise ToolFailure("tool_input_invalid", uncertain=False)

    def invoke(**kwargs):
        kwargs.pop("options", None)
        return request(policy, query, organization_id, **kwargs)

    return ToolAdapter(
        invoke, side_effecting=False, policy_identity=digest(policy.model_dump(mode="json"))
    )
