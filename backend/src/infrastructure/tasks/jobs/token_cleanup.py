"""Фоновая задача: очистка просроченных refresh-токенов."""

import asyncio

from celery.utils.log import get_task_logger

from src.infrastructure.tasks.celery_config import celery_app
from src.infrastructure.tasks.db import create_task_uow
from src.application.interfaces.unitofwork import IUnitOfWork

logger = get_task_logger(__name__)


async def _run_cleanup(uow: IUnitOfWork) -> int:
    """Асинхронная логика очистки, зависящая только от абстракции IUnitOfWork."""
    deleted_count = await uow.refresh_tokens.delete_expired_global()
    await uow.commit()
    return deleted_count


async def _create_and_run() -> int:
    async with create_task_uow() as uow:
        return await _run_cleanup(uow)


@celery_app.task(name="cleanup_expired_tokens")
def cleanup_expired_tokens_task() -> str:
    """Синхронная точка входа Celery — запускает async-логику."""
    logger.info("Запуск фоновой задачи очистки токенов...")

    deleted_count = asyncio.run(_create_and_run())

    message = f"Очистка завершена. Удалено токенов: {deleted_count}"
    logger.info(message)
    return message
