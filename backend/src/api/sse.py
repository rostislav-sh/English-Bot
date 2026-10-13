"""Server-Sent Events: поток «статус изменился» поверх Redis Pub/Sub.

Схема:
    Celery-таска ──commit──► PUBLISH quiz:test:{id}      (tasks/notify.py)
    SSE-эндпоинт  ── SUBSCRIBE ──► ждёт сообщение ──► `event: status` ──► закрыть
    Фронт EventSource ──► получил событие ──► один обычный GET за данными

Событие не несёт данных — только сигнал «перечитай». Данные фронт берёт
существующими GET-эндпоинтами: сериализация не дублируется.

Формат SSE (text/event-stream) — текстовые блоки, разделённые пустой строкой:
    event: status\\ndata: changed\\n\\n   — именованное событие
    : ping\\n\\n                          — комментарий, браузер его игнорирует
"""

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Final

import anyio
from fastapi.responses import StreamingResponse
from redis.exceptions import RedisError

from src.domain.exceptions import DomainError
from src.infrastructure.redis.channels import STATUS_CHANGED_MESSAGE
from src.infrastructure.redis.config_redis import redis_client

logger = logging.getLogger(__name__)

# Final - подсказка для mypy и IDE: «это константа, не переприсваивай». Во время выполнения она ничего не запрещает.
# text/event-stream — значение заголовка Content-Type. По нему браузерный EventSource понимает,
# что пришёл SSE-поток. С другим типом он сразу выдаст ошибку
_SSE_MEDIA_TYPE: Final = "text/event-stream"
_SSE_HEADERS: Final = {
    # Поток нельзя кешировать ни браузеру, ни прокси.
    "Cache-Control": "no-cache",
    # nginx по умолчанию буферизует ответы проксируемого сервера — события
    # копились бы и пришли пачкой в конце. Сейчас nginx нет, но при деплое
    # за ним без этого заголовка SSE молча перестал бы работать.
    "X-Accel-Buffering": "no",
}

# Пинг держит соединение «живым»: прокси и балансировщики рвут соединения
# без трафика (у nginx proxy_read_timeout по умолчанию 60 с).
HEARTBEAT_SECONDS: Final = 15
# Верхняя граница жизни потока: если событие не придёт никогда (воркер
# убит по hard-лимиту), соединение и подписка не висят вечно. С запасом
# больше дедлайна ожидания на фронте (120 с), так что на практике поток
# закрывается раньше — по событию или по уходу клиента.
STREAM_MAX_SECONDS: Final = 150

_STATUS_EVENT: Final = f"event: status\ndata: {STATUS_CHANGED_MESSAGE}\n\n"
_PING: Final = ": ping\n\n"
# Формат SSE устроен так:
#
# каждая строка имеет вид поле: значение;
# пустая строка (то есть \n\n подряд) означает «событие закончилось, отдай его JavaScript»;
# event: задаёт имя события, поэтому на фронте его слушает addEventListener('status', ...);
# data: — полезная нагрузка;
# строка, начинающаяся с :, — комментарий. Браузер её выбрасывает, но байты по сети прошли, и прокси видит, что соединение живое.


async def status_events_response(
        channel: str,
        # is_final - это и есть наш partial (см quiz.py). Тип не требует именно
        # partial: подойдёт любая функция без аргументов (lambda, вложенная функция).
        # тут получаем функцию без аргументов, поэтому Callable[ [] - пустой, ]
        # Callable[ [],          Awaitable[bool] ]
        #           ↑ аргументы   ↑ что возвращает вызов
        #           (никаких)     (то, что можно await-ить и получить bool)
        is_final: Callable[[], Awaitable[bool]],
) -> StreamingResponse:
    """
    Готовый SSE-ответ для эндпоинта: проверка доступа + поток событий.

    :param channel: Redis-канал (src/infrastructure/redis/channels.py).
    :param is_final: читает статус из БД; True — генерация уже завершена.
        Должна бросать DomainError (→ 404 через exception_handlers), если
        сущности нет или она чужая.

    Первый вызов is_final — здесь, ДО создания StreamingResponse. Как только
    генератор начал работу, клиенту уже ушёл статус 200, и вернуть 404 или
    другой код нельзя — только оборвать соединение. Правило собрано в одной
    функции, чтобы новый SSE-эндпоинт не мог его «забыть».
    Второй вызов сделает _status_change_stream уже после подписки.
    """
    # Здесь мы вызываем наш partial, разворачивая функцию и вставляем туда аргументы.
    # Результат (True/False) не нужен — вызов ради исключения: если сущности нет
    # или она чужая, DomainError вылетит отсюда и станет 404, пока ответ не начат.
    await is_final()
    # тело создается по кусочкам во время отправки и каждый кусочек клиент получает после yield.
    # Вызов _status_change_stream(...) ниже НЕ выполняет его тело — только создаёт
    # объект-генератор; выполняться он начнёт, когда Starlette начнёт отправку.
    # StreamingResponse(
    #     content,               # источник кусков, в нашем случае _status_change_stream - асинхронный генератор
    #     status_code=200,
    #     headers=None,          # dict доп. заголовков, у нас _SSE_HEADERS (Cache-Control, X-Accel-Buffering)
    #     media_type=None,       # Content-Type, для текстовых типов Starlette сам добавляет кодировку, поэтому в проверке ответ пришёл как text/event-stream; charset=utf-8
    #     background=None,       # задача, которая выполнится после отправки ответа (у нас не используется)
    # )

    return StreamingResponse(
        _status_change_stream(channel, is_final),
        media_type=_SSE_MEDIA_TYPE,
        headers=_SSE_HEADERS,
    )


async def _status_change_stream(
        channel: str,
        is_final: Callable[[], Awaitable[bool]],
) -> AsyncIterator[str]:
    """
    Генератор для StreamingResponse: ждёт сообщения в `channel` и отдаёт
    одно событие `status`, после чего поток закрывается.

    Параметры — как у status_events_response; напрямую из эндпоинтов не
    вызывается, чтобы не пропустить проверку доступа до начала потока.
    """
    # Отдельное соединение из пула redis_client: подписанное соединение
    # не может выполнять другие команды. ignore_subscribe_messages — не
    # получать служебное подтверждение «subscribe» как сообщение.
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    try:
        # ПОРЯДОК ВАЖЕН: сначала подписка, потом чтение статуса.
        # Pub/Sub не хранит сообщения: опубликованное до подписки пропадает.
        # При обратном порядке была бы гонка —
        #   прочитали GENERATING → воркер закоммитил READY и опубликовал →
        #   мы подписались (событие уже потеряно) → ждём до дедлайна.
        # При порядке «подписка → чтение» любой исход ловится: либо чтение
        # увидит финальный статус, либо событие придёт в подписку.
        await pubsub.subscribe(channel)

        try:
            # тут мы также распаковываем partial и вызываем _is_test_final или
            # _is_attempt_final (смотря какой эндпоинт) уже с аргументами.
            already_final = await is_final()
        except DomainError:
            # Сущность пропала между проверкой доступа и этим чтением
            # (например, тест удалён). Шлём «перечитай» — фронт сделает GET
            # и получит нормальный 404.
            already_final = True
        if already_final:
            # На фронте: addEventListener('status') сработал, мы сами закрыли EventSource.
            # Если бы не закрыли, браузер увидел бы, что сервер закрыл соединение, и попытался бы переподключиться.
            # Поэтому фронт закрывает поток сразу при событии.

            # отдаем событие и генератор замораживается на этой строке. Starlette
            # отправляет байты в сокет и вызывает генератор снова
            yield _STATUS_EVENT
            # return — генератор продолжает работу со следующей строки, а это return.
            # Генератор завершается, async for в Starlette заканчивается,
            # и уходит пустой финальный кусок (more_body: False). HTTP-ответ закрыт.
            return

        # считаем время дедлайна: константа STREAM_MAX_SECONDS из этого модуля (не из env).
        # time.monotonic — часы, которые идут только вперёд (перевод системного
        # времени не сдвинет дедлайн, в отличие от time.time)
        deadline = time.monotonic() + STREAM_MAX_SECONDS
        while (remaining := deadline - time.monotonic()) > 0:
            # Ждём сообщение не дольше интервала пинга. None — за это время
            # ничего не пришло (или пришло служебное, которое мы игнорируем).
            message = await pubsub.get_message(timeout=min(HEARTBEAT_SECONDS, remaining))
            # получили сообщение -> отдали событие -> заморозились -> Starlette отправил
            # его и вызвал генератор снова -> делаем return и вызывается finally.
            if message is not None:
                yield _STATUS_EVENT
                return
            # отдаем пинг КЛИЕНТУ (в HTTP-поток, не в логи) и на следующем витке
            # ждём ещё до 15 с (или меньше, если до дедлайна осталось меньше).
            yield _PING
        # Дедлайн вышел без события — просто закрываем поток.
    except RedisError:
        # Redis недоступен — закрываем поток. Фронт на ошибке потока
        # переключается на обычный polling, который от Redis не зависит.
        logger.warning("SSE: Redis недоступен, поток %s закрыт", channel, exc_info=True)
    finally:
        # Отключение клиента Starlette обрабатывает отменой задачи через anyio
        # cancel scope (uvicorn сообщает ASGI spec 2.3 → ветка с
        # listen_for_disconnect в StreamingResponse). Внутри отменённого scope
        # любой await сразу же снова отменяется — без shield отписка и
        # закрытие соединения не выполнились бы, и подписанные соединения
        # к Redis копились бы с каждой закрытой вкладкой.
        with anyio.CancelScope(shield=True):
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            except RedisError:
                logger.warning("SSE: не удалось закрыть подписку на %s", channel, exc_info=True)
