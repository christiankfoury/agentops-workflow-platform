"""HTTP policy is server configuration; workflows select an alias and fixed path."""

from ipaddress import ip_network
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

Method = Literal["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]


def valid_path(value):
    if (
        not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or "#" in value
        or any(ord(char) < 33 or ord(char) > 126 for char in value)
    ):
        raise ValueError("HTTP path must be an encoded origin-relative path")
    return value


class HTTPOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{0,99}$")
    method: Method = "GET"
    path: str = Field(default="/", max_length=4096)

    @model_validator(mode="after")
    def path_shape(self):
        valid_path(self.path)
        if "?" in self.path:
            raise ValueError("Use schema-bound arguments for query parameters")
        return self


class HTTPDestination(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: str = Field(max_length=2048)
    methods: set[Method] = Field(default_factory=lambda: {"GET", "HEAD"}, min_length=1)
    allowed_private_cidrs: list[str] = Field(default_factory=list, max_length=20)
    allow_plain_http: bool = False
    credential_alias: str | None = Field(default=None, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{0,99}$")
    credential_header: Literal["Authorization", "X-API-Key"] = "Authorization"
    # Nonzero means the operator guarantees identical requests with the same key
    # return the same receipt for at least this many seconds, including errors.
    idempotency_retention_seconds: int = Field(default=0, ge=0, le=604800)
    max_request_bytes: int = Field(default=64000, ge=1, le=128000)
    max_response_bytes: int = Field(default=64000, ge=1, le=128000)
    max_redirects: int = Field(default=0, ge=0, le=3)

    @model_validator(mode="after")
    def destination_shape(self):
        url = urlsplit(self.origin)
        if (
            url.scheme not in {"https", "http"}
            or (url.scheme == "http" and not self.allow_plain_http)
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
            or "%" in url.netloc
            or "\\" in url.netloc
            or any(ord(char) < 33 or ord(char) > 126 for char in self.origin)
        ):
            raise ValueError("Destination must be an explicit HTTP(S) origin")
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError("Destination port is invalid")
        for cidr in self.allowed_private_cidrs:
            ip_network(cidr)
        self.origin = self.origin.rstrip("/")
        return self
