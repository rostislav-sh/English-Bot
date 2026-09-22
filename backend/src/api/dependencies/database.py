"""Базовые зависимости для работы с БД."""

from collections.abc import AsyncGenerator

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
