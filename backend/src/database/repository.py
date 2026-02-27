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
        await self._delete_stale_refresh_tokens(user_id)  # Сначала чистим истекшие/отозванные токены

        tokens_to_delete = await self._get_token_ids_beyond_limit(user_id, max_limit)  # Список ID токенов сверх лимита

        await self._delete_tokens_by_ids(tokens_to_delete)  # Удаляем лишние токены

    async def _delete_stale_refresh_tokens(self, user_id: int) -> None:
        """Удаляет протухшие и отозванные токены конкретного пользователя."""
        query = delete(RefreshToken).where(
            RefreshToken.user_id == user_id,  # Только токены указанного пользователя
            or_(  # Условия очистки объединяем через OR
                RefreshToken.expires_at < datetime.now(UTC),  # Токен уже истек
                RefreshToken.revoked.is_(True),  # Токен отозван
            )
        )
        await self.session.execute(query)  # Выполняем запрос

    async def _get_token_ids_beyond_limit(self, user_id: int, max_limit: int) -> list[int]:
        """Возвращает ID активных токенов, превышающих лимит (самые старые)."""
        limit_to_keep = max(max_limit, 0)  # Негативный лимит трактуем как 0

        query = (
            select(RefreshToken.id)  # Берем только ID токенов
            .where(  # Фильтруем только активные токены пользователя
                RefreshToken.user_id == user_id,  # Токены конкретного пользователя
                RefreshToken.revoked.is_(False),  # Только неотозванные
                RefreshToken.expires_at >= datetime.now(UTC),  # Только неистекшие
            )
            .order_by(RefreshToken.created_at.desc(), RefreshToken.id.desc())  # Сначала самые новые
            .offset(limit_to_keep)  # Пропускаем допустимое количество
        )

        result = await self.session.execute(query)  # Выполняем запрос
        return list(result.scalars().all())  # Возвращаем список ID токенов на удаление

    async def _delete_tokens_by_ids(self, token_ids: list[int]) -> None:
        """Удаляет токены по списку их ID."""
        if token_ids:  # Если список не пустой
            query = delete(RefreshToken).where(
                RefreshToken.id.in_(token_ids)  # Удаляем по списку ID
            )
            await self.session.execute(query)  # Выполняем запрос

    async def delete_all_expired_refresh_tokens(self) -> int:
        """Глобальная чистка протухших и отозванных токенов (для Celery)."""
        query = delete(RefreshToken).where(
            or_(  # Условия очистки объединяем через OR
                RefreshToken.expires_at < datetime.now(UTC),  # Токен истек
                RefreshToken.revoked.is_(True),  # Токен отозван
            )
        )
        result = await self.session.execute(query)  # Выполняем запрос

        return result.rowcount or 0  # Возвращаем число удаленных строк (0 при None)