"""Фоновая задача: очистка просроченных refresh-токенов."""

import asyncio

from celery.utils.log import get_task_logger

from src.tasks.celery_config import celery_app
from src.database.unitofwork import UserUnitOfWork
from src.interfaces.unitofwork import IUserUnitOfWork

logger = get_task_logger(__name__)


async def _run_cleanup(uow: IUserUnitOfWork) -> int:
    """Асинхронная логика очистки, зависящая только от абстракции IUserUnitOfWork."""
    async with uow:
        deleted_count = await uow.user_repo.delete_all_expired_refresh_tokens()
        await uow.commit()
        return deleted_count


@celery_app.task(name="cleanup_expired_tokens")
def cleanup_expired_tokens_task() -> str:
    """Синхронная точка входа Celery — запускает async-логику."""
    logger.info("Запуск фоновой задачи очистки токенов...")

    uow = UserUnitOfWork()
    deleted_count = asyncio.run(_run_cleanup(uow))

    message = f"Очистка завершена. Удалено токенов: {deleted_count}"
    logger.info(message)
    return message
