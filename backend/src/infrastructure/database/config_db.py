"""Конфигурация подключения к PostgreSQL (async SQLAlchemy)."""

import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(url=settings.database_url)
logger.info("Async SQLAlchemy engine создан: %s", settings.db_host)

session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
