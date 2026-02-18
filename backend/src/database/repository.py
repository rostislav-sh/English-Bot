from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.interfaces.repository import IUserRepository
from src.database.models import Users
from src.exceptions import UserAlreadyExistsError


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, email: str, password: str) -> Users:
        existing_user = await self.session.scalar(select(Users).where(Users.email == email))

        if existing_user:
            raise UserAlreadyExistsError

        try:
            user = Users(email=email, password_hash=password)
            self.session.add(user)
            await self.session.flush()
            return user
        except IntegrityError as exc:
            # Нормализация нарушений уникальных ограничений до уровня ошибки домена.
            raise UserAlreadyExistsError from exc