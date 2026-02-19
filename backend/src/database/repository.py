"""Репозитории для работы с БД."""
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.interfaces.repository import IUserRepository
from src.database.models import Users, RefreshToken
from src.exceptions import UserAlreadyExistsError


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_email(self, email: str) -> Users | None:
        """Возвращает пользователя по email или None."""
        return await self.session.scalar(select(Users).where(Users.email == email))

    async def register(self, email: str, password: str) -> Users:
        """Создаёт пользователя. Выбрасывает UserAlreadyExistsError при дубликате."""
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise UserAlreadyExistsError

        try:
            user = Users(email=email, password_hash=password)
            self.session.add(user)
            await self.session.flush()  # Получаем id без коммита
            return user
        except IntegrityError as exc:
            # Race condition: пользователь создан между проверкой и вставкой
            raise UserAlreadyExistsError from exc

    async def create_refresh_token(self, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        """Сохраняет SHA-256 хэш refresh-токена в БД.

        Returns:
            RefreshToken: Созданный объект с присвоенным id (после flush).
        """
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(token)
        await self.session.flush()
        return token
