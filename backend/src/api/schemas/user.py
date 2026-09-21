"""Pydantic-схемы для роутера пользователя (transport layer)."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserProfileOut(BaseModel):
    """Профиль пользователя. Пока только базовые данные."""
    id: int
    email: EmailStr
    username: str | None
    created_at: datetime | None
