"""Абстрактный контракт Unit of Work."""

from abc import ABC, abstractmethod

from src.application.interfaces.repositories import (
    IUserRepository, IRefreshTokenRepository, ITopicRepository, ITestRepository, IAttemptRepository
)


class IUnitOfWork(ABC):
    """Координирует транзакцию над несколькими репозиториями."""

    @property
    @abstractmethod
    def users(self) -> IUserRepository:
        ...

    @property
    @abstractmethod
    def refresh_tokens(self) -> IRefreshTokenRepository:
        ...

    @property
    @abstractmethod
    def topics(self) -> ITopicRepository:
        ...

    @property
    @abstractmethod
    def tests(self) -> ITestRepository:
        ...

    @property
    @abstractmethod
    def attempts(self) -> IAttemptRepository:
        ...

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork":
        """Открывает сессию и инициализирует репозитории."""
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Откатывает при ошибке и закрывает сессию."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Фиксирует транзакцию."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Откатывает транзакцию."""
        ...


class IUnitOfWorkFactory(ABC):
    """
    Фабрика UoW.

    Используется в DI-слое. Каждый вызов возвращает новый UoW
    с собственной изолированной сессией — можно безопасно создавать
    UoW на каждый HTTP-запрос/Celery-таску.
    """
    @abstractmethod
    def __call__(self) -> "IUnitOfWork":
        ...
