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


