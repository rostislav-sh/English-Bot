"""Схемы аутентификации (domain layer)."""

from pydantic import BaseModel, Field, EmailStr


class TokenPair(BaseModel):
    """Пара токенов, выдаваемая при успешной аутентификации."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GoogleUserData(BaseModel):
    """Данные пользователя, извлечённые из верифицированного Google ID-токена."""
    google_id: str = Field(alias="sub")
    email: EmailStr
    username: str | None = Field(default=None, alias="name")
    picture: str | None = None
    email_verified: bool = False
