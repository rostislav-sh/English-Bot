from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str

    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

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
    def auth_access_token_expire_minus(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def auth_refresh_token_expire_days(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS

    @property
    def app_name(self) -> str:
        return self.APP_NAME

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
