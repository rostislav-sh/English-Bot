"""Сервис управления токенами."""

import logging
from datetime import datetime, timedelta, timezone

from src.config import settings
from src.application.interfaces.tokens import ITokenProvider, TokenInvalidError, TokenExpiredError
from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.dto.auth import TokenPair
from src.domain.entities import RefreshToken
from src.domain.exceptions import (
    RefreshTokenNotFoundError,
    RefreshTokenExpiredError,
)

logger = logging.getLogger(__name__)


class TokenService:
    """Создание / ротация / отзыв токенов.

    Работает с доменными сущностями RefreshToken через UoW.
    """

    def __init__(self, uow: IUnitOfWork, tokens_provider: ITokenProvider) -> None:
        self._uow = uow
        self._tokens = tokens_provider

    # ── Публичные методы ─────────────────────────────────────────────

    async def issue(self, user_id: int) -> TokenPair:
        """Создаёт access/refresh JWT, сохраняет хэш refresh в БД.

        Вызывать внутри активного UoW-контекста.
        """
        access_token = self._tokens.create_access_token(user_id=user_id)
        refresh_token = self._tokens.create_refresh_token(user_id=user_id)
        refresh_hash = self._tokens.hash_session_token(token=refresh_token)
        expires_at = self._refresh_expiry()

        token_entity = RefreshToken(
            user_id=user_id,
            token_hash=refresh_hash,
            expires_at=expires_at,
        )
        await self._uow.refresh_tokens.add(token_entity)
        await self._cleanup_session(user_id=user_id)

        logger.debug("Выданы токены: user_id=%s", user_id)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def validate_and_get(self, raw_token: str) -> RefreshToken:
        """Валидирует refresh-токен: JWT-подпись → БД → статус.

        Порядок проверок:
          1. JWT-подпись и тип  — дёшево, без IO
          2. Hash-lookup в БД   — только если JWT валиден
          3. revoked / expired  — финальная проверка статуса

        Вызывать внутри активного UoW-контекста.
        """
        # Проверяем JWT: подпись, exp, тип — без обращения к БД
        try:
            self._tokens.decode_refresh_token(raw_token)
        except TokenExpiredError as e:
            raise RefreshTokenExpiredError() from e
        except TokenInvalidError as e:
            raise RefreshTokenNotFoundError() from e

        # Ищем в БД по hash
        token_hash = self._tokens.hash_session_token(raw_token)
        stored = await self._uow.refresh_tokens.get_by_hash(token_hash)

        if not stored or stored.revoked:
            logger.warning("Refresh-токен не найден или отозван")
            raise RefreshTokenNotFoundError()

        # Проверяем expires_at из БД — источник истины для отзыва
        if stored.is_expired:
            logger.info("Refresh-токен истёк: id=%s", stored.id)
            raise RefreshTokenExpiredError()

        return stored

    async def revoke(self, token: RefreshToken) -> None:
        """Инкапсулирует отзыв одного токена."""
        token.revoked = True
        # sync_tracked() запишет при commit; явный update для самодокументирования:
        await self._uow.refresh_tokens.update(token)

    async def revoke_all(self, user_id: int) -> int:
        """Отзывает все токены пользователя."""
        count = await self._uow.refresh_tokens.revoke_all_for_user(user_id=user_id)
        logger.info("Отозвано токенов: user_id=%s count=%d", user_id, count)
        return count

    # ── Приватные методы ─────────────────────────────────────────────

    async def _cleanup_session(self, user_id: int) -> None:
        """Чистка сессий после выдачи нового токена."""
        await self._uow.refresh_tokens.delete_stale_for_user(user_id)
        await self._uow.refresh_tokens.delete_oldest_beyond_limit(
            user_id=user_id,
            keep=settings.max_sessions_per_user,
        )

    @staticmethod
    def _refresh_expiry() -> datetime:
        return datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
