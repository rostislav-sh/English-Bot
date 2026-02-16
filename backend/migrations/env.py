import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 1. Импортируем твои настройки и модели
# (Обрати внимание на пути, Python должен видеть папку src)
import sys
from os.path import abspath, dirname

sys.path.insert(0, dirname(dirname(abspath(__file__))))  # Добавляем корень проекта в sys.path

from src.config import settings
from src.database.config_db import Base
# Обязательно импортируй ВСЕ модели, иначе Alembic их не увидит!
from src.database.models import Users

config = context.config

# Настройка логгера
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Указываем метаданные твоих моделей
target_metadata = Base.metadata

# 3. ПОДМЕНА URL: Берем URL из settings, а не из alembic.ini
# Pydantic URL может быть объектом, приводим к строке
config.set_main_option("sqlalchemy.url", str(settings.database_url))


def run_migrations_offline() -> None:
    """Запуск миграций в 'оффлайн' режиме (без подключения, просто генерация SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Запуск миграций в 'онлайн' режиме (реальное подключение к БД)."""

    # Создаем движок на основе конфига (куда мы уже подсунули URL settings)
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())