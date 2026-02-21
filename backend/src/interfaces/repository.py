from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models import User, RefreshToken


class IUserRepository(ABC):
    @abstractmethod
    async def get_user_by_email(self, email: str) -> "User":
        """Поиск пользователя по email."""
        ...

    @abstractmethod
    async def register(self, email: str, password: str) -> "User":
        """Регистрация пользователя"""
        ...

    @abstractmethod
    async def create_refresh_token(self, user_id: int, token_hash: str, expires_at: datetime) -> "RefreshToken":
        """Вставка refresh token как ХЕШ с датой истечения"""
