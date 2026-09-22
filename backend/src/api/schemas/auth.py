"""Pydantic-схемы для роутеров аутентификации (transport layer)."""

from pydantic import BaseModel, EmailStr, Field


class Authentication(BaseModel):
    """Входные данные для регистрации / логина."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="Пароль от 8 до 128 символов")


class AuthenticationUsername(Authentication):
    """Получение имени пользователя при регистрации."""
    username: str


class UserOut(BaseModel):
    """Ответ с данными пользователя (без пароля)."""
    username: str | None
    email: EmailStr
