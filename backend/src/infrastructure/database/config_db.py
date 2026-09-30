"""Конфигурация подключения к PostgreSQL (async SQLAlchemy) для FastAPI."""

import logging

from src.config import settings
from src.infrastructure.database.engine import create_session_factory

logger = logging.getLogger(__name__)

# Engine FastAPI-приложения: один event loop на всё время жизни процесса,
# поэтому используем пул соединений по умолчанию.
session_factory = create_session_factory(settings.database_url)
logger.info("Async SQLAlchemy engine создан: %s", settings.db_host)
