"""Pydantic-схемы для роутеров аутентификации (transport layer)."""

from pydantic import BaseModel, EmailStr, Field


class Authentication(BaseModel):
    """Входные данные для регистрации / логина."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="Пароль от 8 до 128 символов")


class UserOut(BaseModel):
    """Ответ с данными пользователя (без пароля)."""
    id: int
    email: EmailStr


class RegisterOut(UserOut):
    """Ответ на регистрацию: данные пользователя + пара токенов."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Тело запроса на обновление токенов."""
    refresh_token: str
