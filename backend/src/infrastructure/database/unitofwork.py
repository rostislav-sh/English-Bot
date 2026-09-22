"""Unit of Work — управление транзакцией и временем жизни сессии БД."""

import logging
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.interfaces.repositories import (
    IUserRepository,
    IRefreshTokenRepository,
    ITopicRepository,
    ITestRepository,
    IAttemptRepository,
)
from src.application.interfaces.unitofwork import IUnitOfWorkFactory, IUnitOfWork
from src.infrastructure.database.repositories import (
    SQLAlchemyBaseRepository,
    SQLAlchemyUserRepository,
    SQLAlchemyRefreshTokenRepository,
    SQLAlchemyTopicRepository,
    SQLAlchemyTestRepository,
    SQLAlchemyAttemptRepository,
)

logger = logging.getLogger(__name__)


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """
    Конкретная реализация UoW.
    Управляет жизненным циклом сессии и координирует репозитории.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

        # Репозитории создаются в __aenter__, сбрасываются в __aexit__
        self._users: SQLAlchemyUserRepository | None = None
        self._refresh_tokens: SQLAlchemyRefreshTokenRepository | None = None
        self._topics: SQLAlchemyTopicRepository | None = None
        self._tests: SQLAlchemyTestRepository | None = None
        self._attempts: SQLAlchemyAttemptRepository | None = None

    # ── Guard ────────────────────────────────────────────────────────

    def _ensure_active(self) -> None:
        if self._session is None:
            raise RuntimeError(
                "UoW не активен. Используйте 'async with uow_factory() as uow:'"
            )

    @property
    def users(self) -> IUserRepository:
        self._ensure_active()
        return self._users

    @property
    def refresh_tokens(self) -> IRefreshTokenRepository:
        self._ensure_active()
        return self._refresh_tokens

    @property
    def topics(self) -> ITopicRepository:
        self._ensure_active()
        return self._topics

    @property
    def tests(self) -> ITestRepository:
        self._ensure_active()
        return self._tests

    @property
    def attempts(self) -> IAttemptRepository:
        self._ensure_active()
        return self._attempts

    # ── Lifecycle ────────────────────────────────────────────────────

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()

        self._users = SQLAlchemyUserRepository(self._session)
        self._refresh_tokens = SQLAlchemyRefreshTokenRepository(self._session)
        self._topics = SQLAlchemyTopicRepository(self._session)
        self._tests = SQLAlchemyTestRepository(self._session)
        self._attempts = SQLAlchemyAttemptRepository(self._session)

        logger.debug("UoW started, session=%s", id(self._session))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type is not None:
                logger.warning(
                    "UoW exiting with exception: %s(%s)", exc_type.__name__, exc_val
                )
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
                logger.debug("UoW session closed, session=%s", id(self._session))

            self._session = None
            self._users = None
            self._refresh_tokens = None
            self._topics = None
            self._tests = None
            self._attempts = None

    # ── Transaction control ──────────────────────────────────────────

    async def commit(self) -> None:
        self._ensure_active()
        # Синхронизируем изменения доменных сущностей → ORM-модели
        self._sync_all()
        await self._session.commit()
        logger.debug("UoW committed")

    async def rollback(self) -> None:
        self._ensure_active()
        await self._session.rollback()
        logger.debug("UoW rolled back")

    def _sync_all(self) -> None:
        """
        Вызывает sync_tracked() на всех репозиториях.

        ВАЖНО: порядок имеет значение — сначала «родительские» сущности
        (на которые ссылаются FK), потом «дочерние». Актуальный порядок:

            users → refresh_tokens
            topics → tests → attempts
        """
        repos: list[SQLAlchemyBaseRepository] = [
            r for r in (
                self._users,
                self._refresh_tokens,
                self._topics,
                self._tests,
                self._attempts,
            )
            if r is not None
        ]
        for repo in repos:
            repo.sync_tracked()


class SQLAlchemyUnitOfWorkFactory(IUnitOfWorkFactory):
    """
    Фабрика UoW.
    Каждый вызов создаёт изолированный UoW с собственной сессией.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(self._session_factory)
