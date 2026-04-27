"""Базовый класс для всех моделей"""

import datetime
from datetime import timezone
from typing import Annotated

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, mapped_column

# ── Переиспользуемые аннотации для колонок ───────────────────────────

int_pk = Annotated[int, mapped_column(primary_key=True)]

created_at = Annotated[
    datetime.datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now())
]

updated_at = Annotated[
    datetime.datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.datetime.now(timezone.utc),
    )
]


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
