from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_UPLOAD_BYTES = 250 * 1024
DEFAULT_MAX_INPUT_CHARS = 50_000
DEFAULT_MAX_NOTES_CHARS = 5_000


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/agentops"
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_pool_timeout_seconds: int = Field(default=5, ge=1)
    worker_concurrency: int = Field(default=4, ge=1, le=32)
    sales_template_enabled: bool = True
    feedback_template_enabled: bool = True
    worker_poll_seconds: float = Field(default=1, gt=0, le=60)
    worker_lease_seconds: float = Field(default=30, ge=0.1, le=3600)
    worker_heartbeat_seconds: float = Field(default=10, ge=0.02, le=600)
    worker_max_recoveries: int = Field(default=3, ge=0, le=10)
    worker_control_poll_seconds: float = Field(default=0.25, ge=0.02, le=10)
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4.1-mini"
    api_auth_enabled: bool = False
    identity_enabled: bool = False
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    identity_session_seconds: int = Field(default=3600, ge=60, le=86400)
    api_key: SecretStr = SecretStr("")
    api_rate_limit_per_minute: int = Field(default=0, ge=0)
    max_upload_bytes: int = Field(default=DEFAULT_MAX_UPLOAD_BYTES, ge=1)
    max_input_chars: int = Field(default=DEFAULT_MAX_INPUT_CHARS, ge=1)
    max_notes_chars: int = Field(default=DEFAULT_MAX_NOTES_CHARS, ge=1)
    agentops_telemetry_enabled: bool = False
    agentops_telemetry_endpoint: str = "http://localhost:8000/v1/usage/llm-events"
    agentops_telemetry_api_key: SecretStr = SecretStr("agentops-local-placeholder-key-not-a-secret")
    agentops_telemetry_timeout_seconds: float = Field(default=2.0, ge=0.1)
    agentops_telemetry_max_metadata_bytes: int = Field(default=2048, ge=0)
    agentops_telemetry_redact_content: bool = True

    @property
    def openai_api_key_value(self) -> str:
        return self.openai_api_key.get_secret_value()

    @model_validator(mode="after")
    def lease_timing(self):
        if self.worker_heartbeat_seconds >= self.worker_lease_seconds:
            raise ValueError("Worker heartbeat interval must be shorter than its lease")
        return self

    @property
    def api_key_value(self) -> str:
        return self.api_key.get_secret_value()

    @property
    def agentops_telemetry_api_key_value(self) -> str:
        return self.agentops_telemetry_api_key.get_secret_value()


settings = Settings()
