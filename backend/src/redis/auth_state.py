"""Хранение и проверка OAuth state в Redis (CSRF-защита)."""

import logging

from redis.asyncio import Redis

from src.exceptions import InvalidOAuthStateError

logger = logging.getLogger(__name__)


class RedisAuthState:
    """Управление OAuth state через Redis.

    State сохраняется с TTL и удаляется при использовании (одноразовый).
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def save_state(self, state: str, ttl: int = 300) -> None:
        """Сохраняет state в Redis с TTL (по умолчанию 5 минут)."""
        key = f"oauth:state:{state}"
        await self.redis.set(key, "valid", ex=ttl)
        logger.debug("OAuth state сохранён в Redis: %s… (ttl=%ds)", state[:8], ttl)

    async def consume_state(self, state: str) -> None:
        """Проверяет и удаляет state (одноразовое использование).

        Raises:
            InvalidOAuthStateError: если state не найден или уже использован.
        """
        key = f"oauth:state:{state}"
        deleted = await self.redis.delete(key)
        if not deleted:
            logger.warning("OAuth state не найден или уже использован: %s…", state[:8])
            raise InvalidOAuthStateError
        logger.debug("OAuth state использован и удалён: %s…", state[:8])
