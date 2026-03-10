"""Unit of Work — управление транзакцией и временем жизни сессии БД."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.config_db import session_factory as db_session
from src.database.repository import UserRepository
from src.interfaces.unitofwork import IUserUnitOfWork

logger = logging.getLogger(__name__)


class UserUnitOfWork(IUserUnitOfWork):
    """Конкретная реализация UoW поверх SQLAlchemy AsyncSession.

    При входе в ``async with`` открывает сессию и создаёт репозитории.
    При выходе — откатывает транзакцию в случае ошибки и закрывает сессию.
    """

    def __init__(self, session_factory=None):
        self.session = session_factory or db_session

    async def __aenter__(self):
        self.session: AsyncSession = self.session()
        self.user_repo = UserRepository(self.session)
        logger.debug("UoW: сессия открыта")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
            logger.warning("UoW: rollback (exc=%s: %s)", exc_type.__name__, exc_val)
        await self.session.close()
        logger.debug("UoW: сессия закрыта")

    async def commit(self):
        """Фиксирует транзакцию."""
        await self.session.commit()
        logger.debug("UoW: commit")

    async def rollback(self):
        """Откатывает транзакцию."""
        await self.session.rollback()
        logger.debug("UoW: rollback")
