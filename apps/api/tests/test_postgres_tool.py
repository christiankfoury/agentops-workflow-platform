import os
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore, Event, Thread
from time import monotonic, sleep
from types import SimpleNamespace

import psycopg2
import pytest
from psycopg2 import sql
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from src.config import settings
from src.models.tenant import DEFAULT_ORGANIZATION_ID as ORGANIZATION
from src.schemas.postgres_tool import PostgreSQLConnection, PostgreSQLOptions, RegisteredQuery
from src.services import postgres_tool as pg
from src.services.execution_control import AbortSignal
from src.services.graph_expressions import ExecutionError
from src.services.tool_effects import ToolFailure

QUERY = (
    "SELECT label FROM public.records WHERE organization_id = %(_organization_id)s "
    "AND label = %(label)s"
)
PASSWORD = "fixture-data-only-password"


@pytest.fixture(scope="module")
def data_source():
    url = os.environ.get("WORKFLOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("WORKFLOW_TEST_DATABASE_URL is required for disposable data database")
    parts = make_url(url)
    # The known test admin creates only this fixture's random database and login.
    admin = psycopg2.connect(url)
    admin.autocommit = True
    name = "phase88_" + uuid.uuid4().hex
    role = name + "_reader"
    with admin.cursor() as cursor:
        cursor.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(role)), (PASSWORD,)
        )
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        cursor.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(name))
        )
        cursor.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(name), sql.Identifier(role)
            )
        )
    data = psycopg2.connect(parts.set(database=name).render_as_string(hide_password=False))
    data.autocommit = True
    other = uuid.uuid4()
    with data.cursor() as cursor:
        cursor.execute("CREATE TABLE public.records (organization_id text, label text)")
        cursor.execute(
            "INSERT INTO public.records VALUES (%s, 'one'), (%s, 'private')",
            (str(ORGANIZATION), str(other)),
        )
        cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
        cursor.execute(sql.SQL("GRANT SELECT ON public.records TO {}").format(sql.Identifier(role)))
    policy = PostgreSQLConnection(
        host=parts.host,
        hostaddr="127.0.0.1",
        port=parts.port or 5432,
        database=name,
        user=role,
        credential_alias="fixture",
        sslmode="disable",
        queries={"find": {"sql": QUERY}},
    )
    try:
        yield SimpleNamespace(policy=policy, data=data, other=other, admin=admin)
    finally:
        data.close()
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
            cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
        admin.close()


def read(data_source, query=QUERY, *, policy=None, organization=ORGANIZATION, **kwargs):
    return pg.request(
        policy or data_source.policy,
        query,
        organization,
        **{
            "arguments": {"label": "one"},
            "secret": PASSWORD,
            "timeout_seconds": 3,
            "control": AbortSignal(),
            **kwargs,
        },
    )


def active(data_source):
    with data_source.admin.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname=%s AND usename=%s",
            (data_source.policy.database, data_source.policy.user),
        )
        return cursor.fetchone()[0]


def clean(data_source):
    end = monotonic() + 3
    while active(data_source) and monotonic() < end:
        sleep(0.03)
    assert active(data_source) == 0


def test_parameterized_reads_tenant_filter_injection_and_cleanup(data_source):
    assert read(data_source) == {"rows": [{"label": "one"}], "row_count": 1}
    assert (
        read(data_source, arguments={"label": "one'; DELETE FROM public.records; --"})["rows"] == []
    )
    assert read(data_source, arguments={"label": "private"})["rows"] == []
    assert (
        read(data_source, organization=data_source.other, arguments={"label": "private"})[
            "row_count"
        ]
        == 1
    )
    with data_source.data.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM public.records")
        assert cursor.fetchone() == (2,)
    clean(data_source)


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM public.records",
        "CREATE TABLE bad (x int)",
        "SELECT 1; DELETE FROM public.records",
        "WITH x AS (DELETE FROM public.records) SELECT 1",
        "SELECT 1 INTO public.bad",
        "SELECT set_config('transaction_read_only','off',false)",
        "SELECT 1 -- comment",
        "SELECT /* comment */ 1",
        "SELECT lo_unlink(1)",
        "SELECT %s",
    ],
)
def test_registration_rejects_unsafe_sql(query):
    with pytest.raises(ValidationError):
        RegisteredQuery(sql=query)


@pytest.mark.parametrize(
    "query", ["SELECT 1 INTO public.bad", "SELECT * FROM public.records FOR UPDATE"]
)
def test_database_readonly_transaction_rejects_writes_even_without_registration_guard(
    data_source, query
):
    with pytest.raises(ToolFailure) as error:
        read(data_source, query, arguments={})
    assert error.value.code in {"tool_denied", "tool_failed"}
    clean(data_source)


@pytest.mark.parametrize(
    "change", ["max_rows", "max_result_bytes", "huge_cell", "duplicate_columns"]
)
def test_result_limits_and_duplicate_column_rejection(data_source, change):
    policy = data_source.policy.model_copy(
        update={"max_rows": 1} if change == "max_rows" else {"max_result_bytes": 128}
    )
    query = {
        "max_rows": "SELECT label FROM public.records",
        "max_result_bytes": "SELECT repeat('x', 80) AS label FROM generate_series(1,2)",
        "huge_cell": "SELECT repeat('x', 1000000) AS label",
        "duplicate_columns": "SELECT 1 AS value, 2 AS value",
    }[change]
    with pytest.raises(ToolFailure, match="tool_response_invalid"):
        read(data_source, query, policy=policy, arguments={})
    clean(data_source)


@pytest.mark.parametrize("budget", [0.15, 3])
def test_absolute_and_server_statement_timeouts(data_source, budget):
    policy = data_source.policy.model_copy(
        update={"statement_timeout_ms": 100 if budget == 3 else 5000}
    )
    started = monotonic()
    with pytest.raises(ToolFailure, match="tool_timeout"):
        read(
            data_source, "SELECT pg_sleep(10)", policy=policy, arguments={}, timeout_seconds=budget
        )
    assert monotonic() - started < 2
    clean(data_source)


def test_cancellation_closes_connection_and_stops_server_query(data_source):
    control = AbortSignal()
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(
            read, data_source, "SELECT pg_sleep(10)", arguments={}, control=control
        )
        end = monotonic() + 2
        while not active(data_source) and monotonic() < end:
            sleep(0.01)
        control.abort()
        with pytest.raises(ExecutionError, match="cancelled"):
            pending.result(timeout=1)
    clean(data_source)


@pytest.mark.parametrize("privilege", ["table", "column", "schema", "database", "membership"])
def test_overprivileged_roles_are_denied(data_source, privilege):
    role = sql.Identifier(data_source.policy.user)
    grant, revoke, connection = {
        "column": (
            sql.SQL("GRANT UPDATE(label) ON public.records TO {}").format(role),
            sql.SQL("REVOKE UPDATE(label) ON public.records FROM {}").format(role),
            data_source.data,
        ),
        "table": (
            sql.SQL("GRANT UPDATE ON public.records TO {}").format(role),
            sql.SQL("REVOKE UPDATE ON public.records FROM {}").format(role),
            data_source.data,
        ),
        "schema": (
            sql.SQL("GRANT CREATE ON SCHEMA public TO {}").format(role),
            sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(role),
            data_source.data,
        ),
        "database": (
            sql.SQL("GRANT TEMP ON DATABASE {} TO {}").format(
                sql.Identifier(data_source.policy.database), role
            ),
            sql.SQL("REVOKE TEMP ON DATABASE {} FROM {}").format(
                sql.Identifier(data_source.policy.database), role
            ),
            data_source.admin,
        ),
        "membership": (
            sql.SQL("GRANT pg_read_all_data TO {}").format(role),
            sql.SQL("REVOKE pg_read_all_data FROM {}").format(role),
            data_source.admin,
        ),
    }[privilege]
    with connection.cursor() as cursor:
        cursor.execute(grant)
        try:
            with pytest.raises(ToolFailure, match="tool_denied"):
                read(data_source)
        finally:
            cursor.execute(revoke)
    clean(data_source)


def test_source_tenant_scope_control_credentials_and_policy_validation(data_source, monkeypatch):
    raw = data_source.policy.model_dump(mode="json")
    monkeypatch.setattr(settings, "postgres_tool_connections", {f"{ORGANIZATION}/fixture": raw})
    options = {"connection": "fixture", "query": "find"}
    assert pg.source(ORGANIZATION, options)[1].database == raw["database"]
    for organization, selected in [
        (data_source.other, options),
        (ORGANIZATION, {**options, "query": "unknown"}),
    ]:
        with pytest.raises(ToolFailure, match="tool_denied"):
            pg.source(organization, selected)
    for field in ["database", "user"]:
        control = make_url(settings.database_url)
        raw[field] = control.database if field == "database" else control.username
        with pytest.raises(ToolFailure, match="tool_denied"):
            pg.source(ORGANIZATION, options)
        raw[field] = getattr(data_source.policy, field)
    with pytest.raises(ValidationError):
        PostgreSQLOptions(**options, sql="SELECT 1")
    with pytest.raises(ValidationError):
        PostgreSQLConnection.model_validate({**raw, "sslmode": "prefer"})
    with pytest.raises(ValidationError):
        PostgreSQLConnection.model_validate({**raw, "sslmode": "verify-full", "sslrootcert": ""})


def test_connection_capacity_bad_credentials_and_reserved_parameters(data_source, monkeypatch):
    semaphore = BoundedSemaphore(1)
    monkeypatch.setattr(pg, "CONNECTION_SLOTS", semaphore)
    semaphore.acquire()
    with pytest.raises(ToolFailure, match="tool_unavailable"):
        read(data_source)
    semaphore.release()
    # libpq may not expose SQLSTATE on failed authentication; no detail escapes.
    with pytest.raises(ToolFailure) as error:
        read(data_source, secret="incorrect-fixture-password")
    assert str(error.value) in {"tool_denied", "tool_unavailable"}
    for arguments in [{"label": []}, {"label": "one", "_organization_id": str(data_source.other)}]:
        with pytest.raises(ToolFailure, match="tool_input_invalid"):
            read(data_source, arguments=arguments)
    assert read(data_source)["row_count"] == 1
    clean(data_source)


def test_stalled_connection_handshake_obeys_total_deadline(data_source):
    done = Event()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(2)

        def stall():
            with listener.accept()[0]:
                done.wait(2)

        thread = Thread(target=stall, daemon=True)
        thread.start()
        policy = data_source.policy.model_copy(update={"port": listener.getsockname()[1]})
        started = monotonic()
        try:
            with pytest.raises(ToolFailure, match="tool_timeout"):
                read(data_source, policy=policy, timeout_seconds=0.2)
            assert monotonic() - started < 1
        finally:
            done.set()
            thread.join(3)


def test_non_system_pg_prefix_schema_and_sequence_privileges_are_denied(data_source):
    role = sql.Identifier(data_source.policy.user)
    with data_source.data.cursor() as cursor:
        cursor.execute("CREATE SCHEMA pgdata")
        cursor.execute("CREATE SEQUENCE public.fixture_sequence")
        try:
            cursor.execute(sql.SQL("GRANT CREATE ON SCHEMA pgdata TO {}").format(role))
            with pytest.raises(ToolFailure, match="tool_denied"):
                read(data_source)
            cursor.execute(sql.SQL("REVOKE CREATE ON SCHEMA pgdata FROM {}").format(role))
            cursor.execute(
                sql.SQL("GRANT USAGE ON SEQUENCE public.fixture_sequence TO {}").format(role)
            )
            with pytest.raises(ToolFailure, match="tool_denied"):
                read(data_source)
        finally:
            cursor.execute("DROP SEQUENCE public.fixture_sequence")
            cursor.execute("DROP SCHEMA pgdata")
    clean(data_source)
