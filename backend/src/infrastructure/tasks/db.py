"""Ресурсы БД для Celery-тасок.

Каждый запуск Celery-таски выполняется через отдельный asyncio.run() —
то есть в новом event loop-е. asyncpg-соединения привязаны к loop-у,
в котором открыты, поэтому пул соединений между запусками делить нельзя.

Engine при этом один на процесс воркера, но с NullPool: соединение
открывается на время сессии и закрывается сразу, как сессия его отпустит,
так что между разными event loop-ами ничего не переживает. Так же
рекомендует документация SQLAlchemy («Using multiple asyncio event loops»).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.pool import NullPool

from src.application.interfaces.unitofwork import IUnitOfWork
from src.config import settings
from src.infrastructure.database.engine import create_session_factory
from src.infrastructure.database.unitofwork import SQLAlchemyUnitOfWorkFactory

# lru_cache - для создания engine один раз за процесс
@lru_cache
def _get_uow_factory() -> SQLAlchemyUnitOfWorkFactory:
    # Создаётся лениво — уже в дочернем процессе воркера после fork.
    session_factory = create_session_factory(settings.database_url, poolclass=NullPool)
    return SQLAlchemyUnitOfWorkFactory(session_factory)


@asynccontextmanager
async def create_task_uow() -> AsyncIterator[IUnitOfWork]:
    """
    Открывает UnitOfWork на общем для процесса engine (NullPool).

    Использование:

        async with create_task_uow() as uow:
            ...
            await uow.commit()

    AsyncIterator - указывается не то, что функция «возвращает» через return, а тип объекта, который получится при вызове
    """
    async with _get_uow_factory()() as uow:
        yield uow
