"""Пакет фоновых задач.

Импорт этого модуля отдаёт готовый экземпляр Celery.
Регистрация задач и расписания происходит автоматически через ``include``
в celery_config.py — ручные импорты здесь не нужны.
"""

from src.tasks.celery_config import celery_app  # noqa: F401
