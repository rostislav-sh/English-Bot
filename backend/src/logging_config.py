"""Централизованная настройка логирования для всего приложения.

Вызывать ``setup_logging()`` один раз при старте (в lifespan / main.py).
В модулях использовать стандартный ``logging.getLogger(__name__)``.
"""

import logging
import sys

from src.config import settings


def setup_logging() -> None:
    """Инициализирует root-логгер с единым форматом и уровнем из настроек."""
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d — %(message)s"
    )
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    # Уменьшаем шум от сторонних библиотек
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
