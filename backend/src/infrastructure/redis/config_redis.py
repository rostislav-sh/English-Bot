"""Конфигурация подключения к Redis (async)."""

import logging

from redis import asyncio as aioredis

from src.config import settings

logger = logging.getLogger(__name__)

redis_client = aioredis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)
logger.info("Redis-клиент создан: %s", settings.redis_url)
