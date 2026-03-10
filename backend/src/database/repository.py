"""Репозитории для работы с БД."""
"""Репозитории для работы с БД (SQLAlchemy async)."""

from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.exc import IntegrityError

from src.interfaces.repository import IUserRepository
from src.database.models import User, RefreshToken
from src.exceptions import UserAlreadyExistsError
from src.schemas.auth import GoogleUserData



class UserRepository(IUserRepository):
    """Репозиторий пользователей и refresh-токенов."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Пользователи ─────────────────────────────────────────────────

    async def get_user_by_email(self, email: str) -> User | None:
        """Возвращает пользователя по email или None."""
        return await self.session.scalar(select(User).where(User.email == email))

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Возвращает пользователя по ID или None."""
        return await self.session.get(User, user_id)

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Возвращает пользователя по google_id или None."""
        return await self.session.scalar(select(User).where(User.google_id == google_id))

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

    async def create_google_user(self, user_info: GoogleUserData) -> User:
        """Создаёт нового пользователя из данных Google OAuth."""
        user = User(
            email=user_info.email,
            password_hash=None,
            google_id=user_info.google_id,
            auth_provider=AuthProvider.GOOGLE,
            username=user_info.username,
            picture_url=user_info.picture,
        )
        try:
            self.session.add(user)
            await self.session.flush()
            return user
        except IntegrityError as exc:
            raise UserAlreadyExistsError from exc

    async def link_google_account(self, user: User, user_info: GoogleUserData) -> User:
        """Привязывает Google-аккаунт к существующему пользователю (Account Linking).

        Если у пользователя уже есть пароль — ставит ``HYBRID``,
        иначе — ``GOOGLE``.
        """
        user.google_id = user_info.google_id
        user.auth_provider = AuthProvider.HYBRID if user.password_hash else AuthProvider.GOOGLE

        if not user.username and user_info.username:
            user.username = user_info.username

        if not user.picture_url and user_info.picture:
            user.picture_url = user_info.picture

        try:
            self.session.add(user)
            await self.session.flush()
            return user
        except IntegrityError as exc:
            # Race condition: кто-то в ту же миллисекунду привязал этот google_id
            raise UserAlreadyExistsError from exc

    # ── Refresh-токены ───────────────────────────────────────────────

    async def create_refresh_token(self, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        """Сохраняет SHA-256 хэш refresh-токена в БД."""
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

    async def enforce_session_limit(self, user_id: int, max_limit: int) -> None:
        """Контролирует лимит активных сессий пользователя.

        Вызывать ПОСЛЕ создания нового refresh-токена.
        После выполнения у пользователя останется не более ``max_limit`` активных токенов.
        """
        await self._delete_stale_refresh_tokens(user_id)  # Сначала чистим истекшие/отозванные токены
        await self._delete_stale_refresh_tokens(user_id)
        tokens_to_delete = await self._get_token_ids_beyond_limit(user_id, max_limit)
        if tokens_to_delete:
        await self._delete_tokens_by_ids(tokens_to_delete)

        tokens_to_delete = await self._get_token_ids_beyond_limit(user_id, max_limit)  # Список ID токенов сверх лимита
    async def delete_all_expired_refresh_tokens(self) -> int:
        """Глобальная чистка протухших и отозванных токенов (для Celery)."""
        query = delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < datetime.now(UTC),
                RefreshToken.revoked.is_(True),
            )
        )
        result = await self.session.execute(query)
        count = result.rowcount or 0
        return count

    # ── Приватные методы ─────────────────────────────────────────────

    async def _delete_stale_refresh_tokens(self, user_id: int) -> None:
        """Удаляет протухшие и отозванные токены конкретного пользователя."""
        query = delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            or_(
                RefreshToken.expires_at < datetime.now(UTC),
                RefreshToken.revoked.is_(True),
            )
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
            .order_by(RefreshToken.created_at.desc(), RefreshToken.id.desc())  # Сначала самые новые
            .offset(limit_to_keep)  # Пропускаем допустимое количество
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
