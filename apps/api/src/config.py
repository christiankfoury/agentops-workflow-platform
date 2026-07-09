from pydantic import Field, SecretStr
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
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4.1-mini"
    api_auth_enabled: bool = False
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

    @property
    def api_key_value(self) -> str:
        return self.api_key.get_secret_value()

    @property
    def agentops_telemetry_api_key_value(self) -> str:
        return self.agentops_telemetry_api_key.get_secret_value()


settings = Settings()
