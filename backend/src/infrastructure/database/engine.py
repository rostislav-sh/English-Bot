"""Фабрика async session_factory — общая для FastAPI и Celery.

Вынесена отдельно от config_db, чтобы импорт в Celery-воркере не создавал
глобальный engine FastAPI-приложения как побочный эффект.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def create_session_factory(database_url: str, **engine_kwargs: Any) -> async_sessionmaker[AsyncSession]:
    """Создаёт engine с переданными параметрами и session_factory поверх него."""
    engine = create_async_engine(url=database_url, **engine_kwargs)
    return async_sessionmaker(bind=engine, expire_on_commit=False)
