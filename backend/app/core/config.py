from typing import Any

from pydantic import field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "AI-Assisted Criminal Investigation & Intelligence Platform"
    API_V1_PREFIX: str = "/api/v1"

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: SecretStr = SecretStr("")

    ADMIN_USERNAME: str = "superadmin"
    ADMIN_EMAIL: str = "admin@example.in"
    ADMIN_BADGE: str = "ADM-0001"
    ADMIN_PASSWORD: SecretStr = SecretStr("ChangeMe_Str0ng_Admin_2026!")

    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_ENABLED: bool = False

    @field_validator("SUPABASE_URL", mode="after")
    @classmethod
    def validate_supabase_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("SUPABASE_URL must not be empty")
        return value.strip()

    @property
    def supabase_service_role_key(self) -> str:
        return self.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()


settings = Settings()

_ = Any
