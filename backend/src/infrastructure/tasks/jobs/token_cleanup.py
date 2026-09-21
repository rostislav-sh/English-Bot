"""Фоновая задача: очистка просроченных refresh-токенов."""

import asyncio

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from celery.utils.log import get_task_logger

from src.infrastructure.tasks.celery_config import celery_app
from src.infrastructure.database.unitofwork import SQLAlchemyUnitOfWorkFactory
from src.application.interfaces.unitofwork import IUnitOfWork
from src.config import settings

logger = get_task_logger(__name__)


async def _run_cleanup(uow: IUnitOfWork) -> int:
    """Асинхронная логика очистки, зависящая только от абстракции IUserUnitOfWork."""
    async with uow:
        deleted_count = await uow.refresh_tokens.delete_expired_global()
        await uow.commit()
        return deleted_count


async def _create_and_run(database_url: str) -> int:
    """
    Создаёт engine с NullPool внутри текущего event loop-а и выполняет очистку.

    NullPool не держит соединения между запросами и не использует asyncio-примитивы,
    поэтому безопасен при каждом вызове asyncio.run() с новым event loop-ом.
    """
    engine = create_async_engine(url=database_url, poolclass=NullPool)
    try:
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        uow_factory = SQLAlchemyUnitOfWorkFactory(session_factory)
        uow = uow_factory()
        return await _run_cleanup(uow)
    finally:
        # Метод .dispose() окончательно закрывает сам движок. Поскольку у нас NullPool,
        # закрывать зависшие сокеты ему не нужно, но он очищает внутренние асинхронные ресурсы самой SQLAlchemy.
        await engine.dispose()


@celery_app.task(name="cleanup_expired_tokens")
def cleanup_expired_tokens_task() -> str:
    """Синхронная точка входа Celery — запускает async-логику."""
    logger.info("Запуск фоновой задачи очистки токенов...")

    deleted_count = asyncio.run(_create_and_run(settings.database_url))

    message = f"Очистка завершена. Удалено токенов: {deleted_count}"
    logger.info(message)
    return message
