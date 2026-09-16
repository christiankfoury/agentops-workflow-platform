import json
import uuid
from urllib.parse import urlsplit

from pydantic import Field, JsonValue, model_validator

from src.schemas.workflow_graph import DataSchema, GraphModel, RetryPolicy

SENSITIVE_KEYS = {
    "authorization",
    "password",
    "secret",
    "api_key",
    "apikey",
    "x_api_key",
    "access_token",
    "token",
    "refresh_token",
    "private_key",
    "client_secret",
    "cookie",
    "set_cookie",
    "connection_string",
    "database_url",
    "dsn",
    "credentials",
}


def bounded(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > 24:
            raise ValueError("Tool payload exceeds 24 levels")
        children = current.values() if isinstance(current, dict) else current
        if isinstance(current, (dict, list)):
            stack.extend((child, depth + 1) for child in children)
    if len(json.dumps(value, allow_nan=False).encode()) > 128_000:
        raise ValueError("Tool payload exceeds 128 KB")
    return value


def redact(value, secret=""):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if key.lower().replace("-", "_") in SENSITIVE_KEYS
            else redact(item, secret)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, secret) for item in value]
    if isinstance(value, str) and secret:
        return value.replace(secret, "[REDACTED]")
    return value


class ToolContract(GraphModel):
    adapter: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    input_schema: DataSchema
    output_schema: DataSchema
    timeout_seconds: float = Field(default=30, gt=0, le=300)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    side_effecting: bool = False
    credential_ref: uuid.UUID | None = None
    options: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_contract(self):
        if self.input_schema.types != {"object"} or self.output_schema.types != {"object"}:
            raise ValueError("Tool input and output must be non-null objects")
        payload = self.model_dump(mode="json")
        bounded(payload)
        if redact(self.options) != self.options:
            raise ValueError("Use credential references instead of embedded credential fields")
        stack = [self.options]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
            elif isinstance(value, str) and "://" in value and urlsplit(value).username is not None:
                raise ValueError("Tool options cannot contain URL credentials")
        return self


class ToolCreate(GraphModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    contract: ToolContract


class ToolPublish(GraphModel):
    expected_version: int = Field(ge=1)
    contract: ToolContract


class CredentialCreate(GraphModel):
    name: str = Field(min_length=1, max_length=200)
    source_alias: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{0,99}$")


class ActiveUpdate(GraphModel):
    active: bool


class EffectResolution(GraphModel):
    succeeded: bool
    result: dict[str, JsonValue] | None = None
    evidence: str = Field(min_length=1, max_length=1000)
