"""Уведомление API о смене статуса генерации через Redis Pub/Sub.

Почему отдельный синхронный клиент, а не готовые:
  • async `redis_client` из infrastructure/redis/config_redis.py привязан
    к event loop-у, а каждая таска — свой asyncio.run(). Та же проблема, из-за
    которой в tasks/db.py стоит NullPool, а GeminiClient закрывается через aclose().
    У синхронного клиента обычный пул сокетов без loop-а — один экземпляр
    на процесс безопасен.
  • `celery_app.backend.client` тоже синхронный, но смотрит на
    CELERY_RESULT_BACKEND, а API подписывается на REDIS_URL. Если их разведут
    по разным инстансам, публикации уходили бы туда, где никто не слушает, —
    без единой ошибки. Здесь берём тот же REDIS_URL, что и API.
Цена — одно постоянное соединение на процесс воркера (2 при --concurrency=2).
"""

from functools import lru_cache
from typing import Final

import redis
from celery.utils.log import get_task_logger
from redis.backoff import NoBackoff
from redis.retry import Retry

from src.config import settings
from src.infrastructure.redis.channels import STATUS_CHANGED_MESSAGE

logger = get_task_logger(__name__)

# По умолчанию у redis-py таймаутов нет: недоступный Redis подвесил бы таску
# до soft-лимита (52 с), и уже успешная генерация упала бы с
# SoftTimeLimitExceeded. Внутри docker-сети Redis отвечает за миллисекунды,
# 2 с — огромный запас.
_SOCKET_TIMEOUT_SECONDS: Final = 2


@lru_cache
def _get_redis() -> redis.Redis:
    """
    Клиент создаётся лениво при первой публикации — уже в дочернем процессе
    воркера после fork (как _get_uow_factory в tasks/db.py), поэтому сокеты
    не наследуются от родителя. Дальше его переиспользуют все таски процесса.
    """
    return redis.Redis.from_url(
        settings.redis_url,
        socket_timeout=_SOCKET_TIMEOUT_SECONDS,
        socket_connect_timeout=_SOCKET_TIMEOUT_SECONDS,
        # По умолчанию redis-py делает 3 ретрая с backoff — худший случай
        # вырос бы до ~9 с. Один ретрай без паузы нужен: соединение
        # постоянное, и после перезапуска Redis первая команда упадёт на
        # «мёртвом» сокете, а вторая пойдёт по новому.
        retry=Retry(NoBackoff(), retries=1),
    )


def notify_status_changed(channel: str) -> None:
    """
    Публикует в канал сообщение «статус изменился».

    Никогда не бросает исключений: уведомление — оптимизация, данные уже
    закоммичены в БД. Если Redis недоступен, фронт всё равно узнает статус:
    SSE при подключении читает его из БД, а при ошибке потока остаётся
    обычный polling. Уронить же таску из-за уведомления было бы хуже —
    Celery вызвал бы on_failure, а при ретрае повторил бы платную генерацию.
    """
    try:
        # PUBLISH возвращает число подписчиков, получивших сообщение.
        # 0 — нормально: страницу могли закрыть, сообщение просто теряется
        # (Pub/Sub ничего не хранит).
        receivers = _get_redis().publish(channel, STATUS_CHANGED_MESSAGE)
    except Exception:
        # Ловим всё, а не только redis.RedisError: сюда же попадёт, например,
        # ValueError от кривого REDIS_URL при создании клиента.
        logger.exception("Не удалось опубликовать смену статуса в канал %s", channel)
        return

    logger.info("Смена статуса опубликована в %s, подписчиков: %s", channel, receivers)
