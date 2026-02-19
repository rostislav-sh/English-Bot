"""Схемы аутентификации (domain layer)."""

from pydantic import BaseModel


class TokenPair(BaseModel):
    """Пара токенов, выдаваемая при успешной аутентификации."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
