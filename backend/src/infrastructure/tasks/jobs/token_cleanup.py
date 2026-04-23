"""Фоновая задача: очистка просроченных refresh-токенов."""

import asyncio

from celery.utils.log import get_task_logger

from src.infrastructure.tasks.celery_config import celery_app
from src.infrastructure.database.config_db import session_factory
from src.infrastructure.database.unitofwork import SQLAlchemyUnitOfWorkFactory
from src.application.interfaces.unitofwork import IUnitOfWork

logger = get_task_logger(__name__)
uow_factory = SQLAlchemyUnitOfWorkFactory(session_factory)


async def _run_cleanup(uow: IUnitOfWork) -> int:
    """Асинхронная логика очистки, зависящая только от абстракции IUserUnitOfWork."""
    async with uow:
        deleted_count = await uow.refresh_token.delete_expired_global()
        await uow.commit()
        return deleted_count


@celery_app.task(name="cleanup_expired_tokens")
def cleanup_expired_tokens_task() -> str:
    """Синхронная точка входа Celery — запускает async-логику."""
    logger.info("Запуск фоновой задачи очистки токенов...")

    uow = uow_factory()
    deleted_count = asyncio.run(_run_cleanup(uow))

    message = f"Очистка завершена. Удалено токенов: {deleted_count}"
    logger.info(message)
    return message
