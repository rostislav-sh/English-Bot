from abc import ABC, abstractmethod

from .base_uow import IBaseRepository
from src.domain.entities import User


class IUserRepository(IBaseRepository[User], ABC):
    @abstractmethod
    async def get_user_by_email(self, email: str) -> "User | None":
        """Поиск пользователя по email."""

    @abstractmethod
    async def register(self, email: str, password: str, username: str) -> "User":
        """Регистрация пользователя"""
