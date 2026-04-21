"""Сервис управления токенами."""

import logging
from datetime import datetime, timedelta, timezone

from src.config import settings
from src.infrastructure.auth.tokens import tokens
from src.application.interfaces.unitofwork import IUnitOfWork
from src.domain.entities import RefreshToken
from src.infrastructure.database.mappers import token_entity_to_model
from src.schemas.auth import TokenPair
from src.api.exceptions import (
    RefreshTokenNotFoundError,
    RefreshTokenLifetimeExpiredError,
)


logger = logging.getLogger(__name__)


class TokenService:
    """Создание / ротация / отзыв токенов.

    Работает с доменными сущностями RefreshToken через UoW.
    """
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    # ── Публичные методы ─────────────────────────────────────────────

    async def issue(self, user_id: int) -> TokenPair:
        """Создаёт access/refresh JWT, сохраняет хэш refresh в БД.

        Вызывать внутри активного UoW-контекста.
        """
        access_token = tokens.get_access_token(user_id=user_id)
        refresh_token = tokens.get_refresh_token(user_id=user_id)
        refresh_hash = tokens.get_refresh_hash(refresh_token=refresh_token)
        expires_at = self._refresh_expiry()

        token_entity = RefreshToken(
            user_id=user_id,
            token_hash=refresh_hash,
            expires_at=expires_at,
        )

        await self._uow.refresh_token.add(token_entity)
        await self._cleanup_session(user_id=user_id)

        logger.debug("Выданы токены: user_id=%s", user_id)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def get_valid(self, raw_token: str) -> RefreshToken:
        """Ищет refresh в БД, проверяет revoked и expires_at.

        Вызывать внутри активного UoW-контекста."""
        token_hash = tokens.hash_session_token(token=raw_token)
        stored = await self._uow.tokens.get_by_hash(token_hash)

        if not stored or stored.revoked:
            logger.warning("Refresh-токен не найден или отозван")
            raise RefreshTokenNotFoundError

        if stored.is_expired:
            logger.info("Refresh-токен истёк: id=%s", stored.id)
            raise RefreshTokenLifetimeExpiredError

        return stored

    async def revoke_all(self, user_id: int) -> int:
        """Отзывает все токены пользователя."""
        count = await self._uow.refresh_token.revoke_all_for_user(user_id=user_id)
        logger.info("Отозвано токенов: user_id=%s count=%d", user_id, count)
        return count

    # ── Приватные методы ─────────────────────────────────────────────

    async def _cleanup_session(self, user_id: int) -> None:
        """Чистка сессий после выдачи нового токена."""
        await self._uow.refresh_token.delete_stale_for_user(user_id)
        await self._uow.refresh_token.delete_oldest_beyond_limit(
            user_id=user_id,
            keep=settings.max_sessions_per_user,
        )

    def _refresh_expiry(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=settings.refresh_expiry_days)
