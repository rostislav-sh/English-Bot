"""Инициализация и конфигурация экземпляра Celery."""

import logging

from celery import Celery

from src.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "auth_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Celery worker при старте импортирует эти модули —
    # задачи регистрируются, расписание применяется.
    include=[
        "src.tasks.jobs.token_cleanup",
        "src.tasks.schedule",
    ],
)

logger.info("Celery app инициализирован: broker=%s", settings.celery_broker_url)