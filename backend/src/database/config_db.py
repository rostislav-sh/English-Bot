"""Конфигурация подключения к PostgreSQL (async SQLAlchemy)."""

import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(url=settings.database_url)
logger.info("Async SQLAlchemy engine создан: %s", settings.db_host)

session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей.

    Все таблицы наследуются от этого класса, чтобы Alembic
    и SQLAlchemy могли автоматически обнаруживать метаданные.
    """
    repr_cols_num = 5
    repr_cols = tuple()

    def __repr__(self):
        cols = []
        for idx, col in enumerate(self.__table__.columns.keys()):
            if col in self.repr_cols or idx < self.repr_cols_num:
                cols.append(f'{col}={getattr(self, col)}')
        return f'<{self.__class__.__name__}  {", ".join(cols)}>'
