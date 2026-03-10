from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models import User, RefreshToken


class IUserRepository(ABC):
    @abstractmethod
    async def get_user_by_email(self, email: str) -> "User | None":
        """Поиск пользователя по email."""

    @abstractmethod
    async def register(self, email: str, password: str) -> "User":
        """Регистрация пользователя"""

    @abstractmethod
    async def create_refresh_token(self, user_id: int, token_hash: str, expires_at: datetime) -> "RefreshToken":
        """Вставка refresh token как ХЕШ с датой истечения"""

    @abstractmethod
    async def get_refresh_token(self, token_hash: str) -> "RefreshToken | None":
        """Получение информации о refresh токене по его хешу."""

    @abstractmethod
    async def delete_refresh_token(self, token_object: "RefreshToken") -> None:
        """Удаление refresh токена."""

    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> "User | None":
        """Получение пользователя по id."""

    @abstractmethod
    async def enforce_session_limit(self, user_id: int, max_limit: int) -> None:
        """Контролирует лимит активных сессий пользователя.

        Вызывать ПОСЛЕ создания нового refresh-токена.
        После выполнения у пользователя останется не более max_limit активных токенов.
        """

    @abstractmethod
    async def delete_all_expired_refresh_tokens(self) -> int:
        """Глобальная чистка протухших и отозванных токенов (для Celery)."""
