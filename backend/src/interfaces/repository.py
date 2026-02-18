from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models import Users


class IUserRepository(ABC):
    @abstractmethod
    async def register(self, email: str, password: str) -> "Users":
        """Регистрация пользователя"""
        ...
