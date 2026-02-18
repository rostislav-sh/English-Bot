from sqlalchemy.ext.asyncio import AsyncSession

from src.database.config_db import session_factory as db_session
from src.database.repository import UserRepository
from src.interfaces.unitofwork import IUserUnitOfWork


class UserUnitOfWork(IUserUnitOfWork):
    def __init__(self, session_factory = None):
        self.session = session_factory or db_session

    async def __aenter__(self):
        self.session: AsyncSession = self.session()

        self.user_repo = UserRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()