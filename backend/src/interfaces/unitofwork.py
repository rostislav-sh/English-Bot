"""Абстрактный контракт Unit of Work."""

from abc import ABC, abstractmethod

from src.interfaces.repositories.auth_uow import IRefreshTokenRepository
from src.interfaces.repositories.user_uow import IUserRepository


class IUnitOfWork(ABC):
    """Координирует транзакцию над несколькими репозиториями."""

    @property
    @abstractmethod
    def users(self) -> IUserRepository:
        ...

    @property
    @abstractmethod
    def refresh_token(self) -> IRefreshTokenRepository:
        ...

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


class IUnitOfWorkFactory(ABC):
    @abstractmethod
    def __call__(self) -> "IUnitOfWork":
        ...
