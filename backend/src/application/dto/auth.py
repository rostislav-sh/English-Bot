"""DTO слоя application — пересекают границу api↔application."""

from pydantic import BaseModel, ConfigDict, Field


class FrozenDTO(BaseModel):
    """База для всех application DTO."""
    model_config = ConfigDict(frozen=True, extra="forbid")


class TokenPair(FrozenDTO):
    """Пара токенов, выдаваемая при успешной аутентификации."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GoogleUserData(BaseModel):
    """Данные пользователя, извлечённые из верифицированного Google ID-токена.

    Не наследуется от FrozenDTO: парсит внешние claims чужого JWT, где лишние
    поля (iss, aud, azp, iat, exp, at_hash, given_name, family_name и т.д.) —
    норма, а не ошибка, поэтому extra="ignore", а не "forbid".
    """
    model_config = ConfigDict(frozen=True, extra="ignore")

    google_id: str = Field(alias="sub")
    email: str
    email_verified: bool
    username: str | None = Field(default=None, alias="name")
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
