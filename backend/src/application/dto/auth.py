"""DTO слоя application — пересекают границу api↔application."""

from pydantic import BaseModel, ConfigDict


class FrozenDTO(BaseModel):
    """База для всех application DTO."""
    model_config = ConfigDict(frozen=True, extra="forbid")


class TokenPair(FrozenDTO):
    """Пара токенов, выдаваемая при успешной аутентификации."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GoogleUserData(FrozenDTO):
    """Данные пользователя, извлечённые из верифицированного Google ID-токена."""
    google_id: str
    email: str
    email_verified: bool
    username: str | None = None
    picture: str | None = None


class GoogleAuthorizationURL(FrozenDTO):
    """google url для аутентификации"""
    url: str
    state: str


class RegisterCommand(FrozenDTO):
    """Входные данные при регистрации"""
    email: str
    password: str
    username: str


class LoginCommand(FrozenDTO):
    """Входные данные при логине"""
    email: str
    password: str
