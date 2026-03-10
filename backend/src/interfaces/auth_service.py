"""Контракт сервиса аутентификации для слоя роутеров."""

from typing import TYPE_CHECKING, Protocol

from src.schemas.auth import TokenPair

if TYPE_CHECKING:
    from src.database.models import User


class AuthServiceProtocol(Protocol):
    """Минимальный контракт auth-сервиса, используемый через Depends.

    Роутеры зависят от этого протокола, а не от конкретной реализации.
    """

    async def register(self, email: str, password: str) -> tuple["User", TokenPair]:
        """Регистрация пользователя."""

    async def login(self, email: str, password: str) -> tuple["User", TokenPair]:
        """Вход по email + пароль."""

    async def refresh(self, raw_refresh_token: str) -> tuple["User", TokenPair]:
        """Ротация refresh-токена."""

    async def get_google_url(self) -> tuple[str, str]:
        """Генерация Google OAuth URL."""

    async def authenticate_via_google(self, code: str, state: str) -> tuple["User", TokenPair]:
        """Завершение Google OAuth (code → user + tokens)."""
