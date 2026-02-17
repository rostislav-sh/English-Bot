import datetime
from typing import Annotated

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text, String, ForeignKey, Boolean

from .config_db import Base

int_pk = Annotated[int, mapped_column(primary_key=True)]
created_at = Annotated[datetime.datetime, mapped_column(server_default=text("TIMEZONE('utc', now())"))]
updated_at = Annotated[datetime.datetime, mapped_column(
    server_default=text("TIMEZONE('utc', now())"),
    onupdate=datetime.datetime.utcnow,
)]


class Users(Base):
    __tablename__ = 'users'

    id: Mapped[int_pk]
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] # использует хеш пароля
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    refresh_tokens: Mapped[str]

class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id = Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    # Хэш refresh токена (opaque строка); используется для валидации при ротации.
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    # Дата/время истечения refresh токена
    expires_at: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    # Флаг отзыва: позволяет сделать токен недействительным без удаления.
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Время создания refresh токена
    created_at: Mapped[created_at]

    user: Mapped[Users] = relationship(back_populates="refresh_tokens")
