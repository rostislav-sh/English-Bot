"""Расписание периодических задач (Celery Beat)."""

from celery.schedules import crontab

from src.tasks.celery_config import celery_app

celery_app.conf.beat_schedule = {
    "daily-token-cleanup": {
        "task": "cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=0),  # Каждый день в 03:00 UTC
    },
}
