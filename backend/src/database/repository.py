"""Репозитории для работы с БД."""
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.exc import IntegrityError

from src.interfaces.repository import IUserRepository
from src.database.models import User, RefreshToken
from src.exceptions import UserAlreadyExistsError


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_email(self, email: str) -> User | None:
        """Возвращает пользователя по email или None."""
        return await self.session.scalar(select(User).where(User.email == email))

    async def register(self, email: str, password: str) -> User:
        """Создаёт пользователя. Выбрасывает UserAlreadyExistsError при дубликате."""
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise UserAlreadyExistsError

        try:
            user = User(email=email, password_hash=password)
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

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        """Ищет refresh-токен по SHA-256 хэшу."""
        return await self.session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    async def delete_refresh_token(self, token_object: RefreshToken) -> None:
        """Удаляет refresh-токен из БД."""
        await self.session.delete(token_object)

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Возвращает пользователя по ID или None."""
        return await self.session.get(User, user_id)

    async def enforce_session_limit(self, user_id: int, max_limit: int) -> None:
        """Контролирует лимит активных сессий пользователя.

        Вызывать ПОСЛЕ создания нового refresh-токена.
        После выполнения у пользователя останется не более max_limit активных токенов.
        """
        await self._delete_stale_refresh_tokens(user_id)

        tokens_to_delete = await self._get_token_ids_beyond_limit(user_id, max_limit)

        await self._delete_tokens_by_ids(tokens_to_delete)

    async def _delete_stale_refresh_tokens(self, user_id: int) -> None:
        """Удаляет протухшие и отозванные токены конкретного пользователя."""
        query = delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            or_(
                RefreshToken.expires_at < datetime.now(UTC),
                RefreshToken.revoked.is_(True),
            ),
        )
        await self.session.execute(query)

    async def _get_token_ids_beyond_limit(self, user_id: int, max_limit: int) -> list[int]:
        """Возвращает ID активных токенов, превышающих лимит (самые старые)."""
        limit_to_keep = max(max_limit, 0)

        query = (
            select(RefreshToken.id)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at >= datetime.now(UTC),
            )
            .order_by(RefreshToken.created_at.desc(), RefreshToken.id.desc())
            .offset(limit_to_keep)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _delete_tokens_by_ids(self, token_ids: list[int]) -> None:
        """Удаляет токены по списку их ID."""
        if token_ids:
            query = delete(RefreshToken).where(RefreshToken.id.in_(token_ids))
            await self.session.execute(query)

    async def delete_all_expired_refresh_tokens(self) -> int:
        """Глобальная чистка протухших и отозванных токенов (для Celery)."""
        query = delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < datetime.now(UTC),
                RefreshToken.revoked.is_(True),
            )
        )
        result = await self.session.execute(query)

        return result.rowcount or 0
