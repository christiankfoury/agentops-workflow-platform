"""Operators register data sources and SQL; graphs select aliases only."""

import re
from ipaddress import ip_address
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ALIAS = r"^[a-zA-Z][a-zA-Z0-9_.-]{0,99}$"
PARAMETER = re.compile(r"%\(([a-zA-Z_][a-zA-Z0-9_]*)\)s")


class PostgreSQLOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection: str = Field(pattern=ALIAS)
    query: str = Field(pattern=ALIAS)


class RegisteredQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sql: str = Field(min_length=1, max_length=16000)

    @model_validator(mode="after")
    def read_shape(self):
        # This intentionally small grammar is a registration guard, not a SQL
        # sandbox. Restricted privileges and a read-only transaction enforce it.
        if (
            not re.match(r"^\s*SELECT\s", self.sql, re.I)
            or any(value in self.sql for value in (";", "--", "/*", "*/", "\x00"))
            or re.search(
                r"\b(insert|update|delete|merge|into|create|alter|drop|copy|call|do|"
                r"grant|revoke|set_config|dblink\w*|lo_\w*)\b",
                self.sql,
                re.I,
            )
            or "%" in PARAMETER.sub("", self.sql)
        ):
            raise ValueError("Register one parameterized SELECT without comments")
        return self


class PostgreSQLConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    host: str = Field(min_length=1, max_length=253, pattern=r"^[a-zA-Z0-9_.:-]+$")
    hostaddr: str
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")
    user: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")
    credential_alias: str = Field(pattern=ALIAS)
    sslmode: Literal["verify-full", "disable"] = "verify-full"
    sslrootcert: str = Field(default="", max_length=2048)
    queries: dict[str, RegisteredQuery] = Field(min_length=1, max_length=100)
    max_rows: int = Field(default=100, ge=1, le=1000)
    max_result_bytes: int = Field(default=64000, ge=128, le=120000)
    statement_timeout_ms: int = Field(default=5000, ge=10, le=30000)

    @model_validator(mode="after")
    def connection_shape(self):
        address = ip_address(self.hostaddr)
        if address.is_unspecified or address.is_multicast or address.is_link_local:
            raise ValueError("An explicit data server address is required")
        if self.sslmode == "verify-full" and not self.sslrootcert:
            raise ValueError("Verified TLS requires an operator-owned root certificate")
        if any(not re.fullmatch(ALIAS, alias) for alias in self.queries):
            raise ValueError("Invalid query alias")
        return self
