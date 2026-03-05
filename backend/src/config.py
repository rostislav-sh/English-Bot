from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Разрешение имени файла .env относительно каталога backend/ для локальных запусков
_env_path = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    APP_NAME: str

    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    REDIS_URL: str

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    ACCESS_COOKIE_NAME: str
    REFRESH_COOKIE_NAME: str
    SESSION_COOKIE_SECURE: bool
    SESSION_COOKIE_HTTPONLY: bool
    SAMESITE: str
    DOMAIN: str | None = None
    PATH: str

    FAKE_PASSWORD_HASH: str

    MAX_SESSIONS_PER_USER: int

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def auth_jwt_secret_key(self) -> str:
        return self.JWT_SECRET_KEY

    @property
    def auth_jwt_algorithm(self) -> str:
        return self.JWT_ALGORITHM

    @property
    def auth_access_token_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def auth_refresh_token_expire_days(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS

    @property
    def access_cookie_name(self) -> str:
        return self.ACCESS_COOKIE_NAME

    @property
    def refresh_cookie_name(self) -> str:
        return self.REFRESH_COOKIE_NAME

    @property
    def session_cookie_secure(self):
        return self.SESSION_COOKIE_SECURE

    @property
    def session_cookie_httponly(self):
        return self.SESSION_COOKIE_HTTPONLY

    @property
    def samesite(self) -> str:
        return self.SAMESITE

    @property
    def session_cookie_domain(self):
        return self.DOMAIN

    @property
    def session_cookie_path(self):
        return self.PATH

    @property
    def app_name(self) -> str:
        return self.APP_NAME

    @property
    def fake_password_hash(self) -> str:
        return self.FAKE_PASSWORD_HASH

    @property
    def max_sessions_per_user(self) -> int:
        return self.MAX_SESSIONS_PER_USER

    @property
    def redis_url(self) -> str:
        return self.REDIS_URL

    @property
    def celery_broker_url(self) -> str:
        """Возвращает URL брокера (очереди задач)."""
        return self.CELERY_BROKER_URL

    @property
    def celery_result_backend(self) -> str:
        """Возвращает URL бэкенда (хранилища результатов)."""
        return self.CELERY_RESULT_BACKEND

    @property
    def google_client_id(self) -> str:
        return self.GOOGLE_CLIENT_ID

    @property
    def google_client_secret(self) -> str:
        return self.GOOGLE_CLIENT_SECRET

    @property
    def google_redirect_uri(self) -> str:
        return self.GOOGLE_REDIRECT_URI

    model_config = SettingsConfigDict(env_file=_env_path)


settings = Settings()
