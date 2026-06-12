from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_UPLOAD_BYTES = 250 * 1024
DEFAULT_MAX_INPUT_CHARS = 50_000
DEFAULT_MAX_NOTES_CHARS = 5_000


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/agentops"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4.1-mini"
    api_auth_enabled: bool = False
    api_key: SecretStr = SecretStr("")
    api_rate_limit_per_minute: int = Field(default=0, ge=0)
    max_upload_bytes: int = Field(default=DEFAULT_MAX_UPLOAD_BYTES, ge=1)
    max_input_chars: int = Field(default=DEFAULT_MAX_INPUT_CHARS, ge=1)
    max_notes_chars: int = Field(default=DEFAULT_MAX_NOTES_CHARS, ge=1)

    @property
    def openai_api_key_value(self) -> str:
        return self.openai_api_key.get_secret_value()

    @property
    def api_key_value(self) -> str:
        return self.api_key.get_secret_value()


settings = Settings()
