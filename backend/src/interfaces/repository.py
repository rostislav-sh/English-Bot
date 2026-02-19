from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models import Users


class IUserRepository(ABC):
    @abstractmethod
    async def get_user_by_email(self, email: str):
        """Поиск пользователя по email."""
        ...

    @abstractmethod
    async def register(self, email: str, password: str) -> "Users":
        """Регистрация пользователя"""
        ...
