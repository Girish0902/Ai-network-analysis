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

    DATABASE_URL: str = "postgresql+psycopg2://investigation:investigation@localhost:5432/investigation"

    SECRET_KEY: SecretStr = SecretStr("LocalDevOnly")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    ADMIN_USERNAME: str = "superadmin"
    ADMIN_EMAIL: str = "admin@example.in"
    ADMIN_BADGE: str = "ADM-0001"
    ADMIN_PASSWORD: SecretStr = SecretStr("ChangeMe_Str0ng_Admin_2026!")

    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_ROOT: str = "uploads"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "evidence-vault"
    MINIO_SECURE: bool = False

    CLAMAV_ENABLED: bool = False

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL must not be empty")
        return value.strip()

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY.get_secret_value()


settings = Settings()

_ = Any