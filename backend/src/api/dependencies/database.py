"""Базовые зависимости для работы с БД."""

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

from src.application.interfaces.unitofwork import IUnitOfWork
from src.infrastructure.database.config_db import session_factory
from src.infrastructure.database.unitofwork import SQLAlchemyUnitOfWorkFactory

# Фабрика создаётся один раз при старте
_uow_factory = SQLAlchemyUnitOfWorkFactory(session_factory)

async def get_uow() -> AsyncGenerator[IUnitOfWork, None]:
    """
    Провайдер Unit of Work для всех сервисов.

    Открывает транзакцию до выполнения запроса роутером
    и гарантированно закрывает (__aexit__) после.
    """
    async with _uow_factory() as uow:
        yield uow


@asynccontextmanager
async def open_short_uow() -> AsyncIterator[IUnitOfWork]:
    """
    UoW на время блока `async with`, а не на весь запрос.

    get_uow — зависимость с yield: FastAPI закрывает её только после того,
    как ответ отправлен целиком. Для SSE-потока это до нескольких минут, и
    каждая открытая вкладка держала бы соединение из пула SQLAlchemy
    (по умолчанию 5 + 10 overflow) — 15 ожидающих вкладок исчерпали бы пул
    для всего API. Здесь соединение берётся на миллисекунды чтения.
    """
    async with _uow_factory() as uow:
        yield uow
