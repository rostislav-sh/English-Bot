"""Репозитории для работы с БД (SQLAlchemy async)."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, exists, func, update

from src.application.interfaces.repositories import IUserRepository, IRefreshTokenRepository
from src.infrastructure.database.base_repository import SQLAlchemyBaseRepository
from src.infrastructure.database.models import UserModel, RefreshTokenModel
from src.domain.entities import User, RefreshToken
from .mappers import (
    user_model_to_entity,
    user_entity_to_model,
    update_user_model_from_entity,
    token_model_to_entity,
    token_entity_to_model,
    update_token_model_from_entity,
)

logger = logging.getLogger(__name__)


class SQLAlchemyUserRepository(SQLAlchemyBaseRepository[User], IUserRepository):
    """
    Репозиторий пользователей.

    Принимает/возвращает доменную сущность User.
    UserModel — деталь реализации, наружу не выходит.
    """

    def _get_model_class(self) -> type:
        return UserModel

    def _to_entity(self, model: UserModel) -> User:
        return user_model_to_entity(model)

    def _to_model(self, entity: User) -> UserModel:
        return user_entity_to_model(entity)

    def _update_model(self, model: UserModel, entity: User) -> None:
        update_user_model_from_entity(model, entity)

    # ── Специфичные методы ───────────────────────────────────────────

    async def get_by_email(self, email: str) -> User | None:
        """Возвращает пользователя по email или None."""
        model = await self._session.scalar(
            select(UserModel).where(UserModel.email == email)
        )
        return self._track(model) if model else None

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Возвращает пользователя по google_id или None."""
        model = await self._session.scalar(
            select(UserModel).where(UserModel.google_id == google_id)
        )
        return self._track(model) if model else None

    async def exists_by_email(self, email: str) -> bool:
        """Проверяет существование пользователя без загрузки записи."""
        result = await self._session.scalar(
            select(exists().where(UserModel.email == email))
        )
        return bool(result)


class SQLAlchemyRefreshTokenRepository(
    SQLAlchemyBaseRepository[RefreshToken], IRefreshTokenRepository
):
    """
    Репозиторий refresh-токенов.

    Принимает/возвращает доменную сущность RefreshToken.
    RefreshTokenModel — деталь реализации, наружу не выходит.
    """

    def _get_model_class(self) -> type:
        return RefreshTokenModel

    def _to_entity(self, model: RefreshTokenModel) -> RefreshToken:
        return token_model_to_entity(model)

    def _to_model(self, entity: RefreshToken) -> RefreshTokenModel:
        return token_entity_to_model(entity)

    def _update_model(self, model: RefreshTokenModel, entity: RefreshToken) -> None:
        update_token_model_from_entity(model, entity)

    # ── Специфичные методы ───────────────────────────────────────────

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Возвращает токен по SHA-256 хэшу или None."""
        model = await self._session.scalar(
            select(RefreshTokenModel).where(
                RefreshTokenModel.token_hash == token_hash
            )
        )
        return self._track(model) if model else None

    async def get_active_by_user_id(self, user_id: int) -> list[RefreshToken]:
        """Возвращает активные токены пользователя, отсортированные по дате создания."""
        result = await self._session.scalars(
            select(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked.is_(False),
                RefreshTokenModel.expires_at >= func.now(),
            )
            .order_by(RefreshTokenModel.created_at.desc())
        )
        return [self._track(model) for model in result]

    async def revoke_all_for_user(self, user_id: int) -> int:
        """Bulk UPDATE — один SQL-запрос, отзывает все активные токены пользователя."""
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked.is_(False),
            )
            .values(revoked=True)
            .execution_options(synchronize_session="fetch")
        )
        count = result.rowcount or 0
        self._evict_tracked(lambda entity: entity.user_id == user_id)
        logger.info("revoke_all_for_user: user_id=%s отозвано=%d", user_id, count)
        return count

    async def delete_stale_for_user(self, user_id: int) -> int:
        """Удаляет протухшие и отозванные токены конкретного пользователя."""
        result = await self._session.execute(
            delete(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                or_(
                    RefreshTokenModel.expires_at < func.now(),
                    RefreshTokenModel.revoked.is_(True),
                ),
            )
            .execution_options(synchronize_session="fetch")
        )
        self._evict_tracked(lambda entity: entity.user_id == user_id)
        return result.rowcount or 0

    async def delete_oldest_beyond_limit(self, user_id: int, keep: int) -> int:
        """Удаляет активные токены сверх лимита, оставляя keep самых свежих."""
        limit_to_keep = max(keep, 0)

        ids_cte = (
            select(RefreshTokenModel.id)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked.is_(False),
                RefreshTokenModel.expires_at >= func.now(),
            )
            .order_by(
                RefreshTokenModel.created_at.desc(),
                RefreshTokenModel.id.desc(),
            )
            .offset(limit_to_keep)
            .cte("ids_to_delete")
        )

        result = await self._session.execute(
            delete(RefreshTokenModel)
            .where(RefreshTokenModel.id.in_(select(ids_cte.c.id)))
            .execution_options(synchronize_session="fetch")
        )
        self._evict_tracked(lambda entity: entity.user_id == user_id)
        return result.rowcount or 0

    async def delete_expired_global(self) -> int:
        """Глобальная чистка протухших и отозванных токенов (для Celery)."""
        result = await self._session.execute(
            delete(RefreshTokenModel)
            .where(
                or_(
                    RefreshTokenModel.expires_at < func.now(),
                    RefreshTokenModel.revoked.is_(True),
                )
            )
            .execution_options(synchronize_session="fetch")
        )
        # Глобальная операция — чистим весь identity_map
        self._identity_map.clear()
        return result.rowcount or 0
