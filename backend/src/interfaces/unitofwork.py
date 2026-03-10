"""Абстрактный контракт Unit of Work."""

from abc import ABC, abstractmethod

from src.interfaces.repository import IUserRepository


class IUserUnitOfWork(ABC):
    """Интерфейс UoW — управляет транзакцией и предоставляет репозитории."""

    user_repo: IUserRepository

    @abstractmethod
    async def __aenter__(self):
        """Открывает сессию и инициализирует репозитории."""
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Откатывает при ошибке и закрывает сессию."""
        ...

    @abstractmethod
    async def commit(self):
        """Фиксирует транзакцию."""
        ...

    @abstractmethod
    async def rollback(self):
        """Откатывает транзакцию."""
        ...