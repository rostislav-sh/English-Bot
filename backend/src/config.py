"""Настройки приложения, загружаемые из переменных окружения / .env файла."""
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# Разрешение имени файла .env относительно каталога backend/ для локальных запусков
_env_path = Path(__file__).resolve().parents[2] / ".env"
print(_env_path)


class Settings(BaseSettings):
    """Конфигурация приложения. Значения читаются из ENV / .env."""

    app_name: str = Field(validation_alias="APP_NAME")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    db_host: str = Field(validation_alias="DB_HOST")
    db_port: int = Field(validation_alias="DB_PORT")
    db_user: str = Field(validation_alias="DB_USER")
    db_password: str = Field(validation_alias="DB_PASSWORD")
    db_name: str = Field(validation_alias="DB_NAME")

    redis_url: str = Field(validation_alias="REDIS_URL")

    celery_broker_url: str = Field(validation_alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(validation_alias="CELERY_RESULT_BACKEND")

    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")

    access_cookie_name: str = Field(validation_alias="ACCESS_COOKIE_NAME")
    refresh_cookie_name: str = Field(validation_alias="REFRESH_COOKIE_NAME")
    session_cookie_secure: bool = Field(validation_alias="SESSION_COOKIE_SECURE")
    session_cookie_httponly: bool = Field(validation_alias="SESSION_COOKIE_HTTPONLY")
    samesite: Literal["lax", "strict", "none"] = Field(validation_alias="SAMESITE")
    domain: str | None = Field(default=None, validation_alias="DOMAIN")
    path: str = Field(validation_alias="COOKIE_PATH")

    fake_password_hash: str = Field(validation_alias="FAKE_PASSWORD_HASH")

    max_sessions_per_user: int = Field(validation_alias="MAX_SESSIONS_PER_USER")

    google_client_id: str = Field(validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(validation_alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(validation_alias="GOOGLE_REDIRECT_URI")
    base_url: str = Field(validation_alias="BASE_URL")
    token_url: str = Field(validation_alias="TOKEN_URL")

    frontend_redirect_url: str = Field(
        default="http://localhost:3000/dashboard",
        validation_alias="FRONTEND_REDIRECT_URL",
    )

    @field_validator("samesite", mode="before")
    @classmethod
    def _normalize_samesite(cls, value: str) -> str:
        return value.lower()

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = SettingsConfigDict(
        env_file=str(_env_path) if _env_path.exists() else None,
        extra="ignore"
    )


settings = Settings()
