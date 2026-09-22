"""ORM-модели приложения (SQLAlchemy declarative)."""

import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .attempts import TestAttemptModel

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    DateTime, String, ForeignKey, Boolean,
    text, Index,
    Enum as SQLEnum,
)

from src.infrastructure.database.models.base import Base, int_pk, created_at, updated_at
from src.domain.enums import AuthProvider


class UserModel(Base):
    """Модель пользователя."""
    __tablename__ = "users"

    id: Mapped[int_pk]
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    auth_provider: Mapped[AuthProvider] = mapped_column(
        SQLEnum(AuthProvider),
        default=AuthProvider.LOCAL,
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    test_attempts: Mapped[list["TestAttemptModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RefreshTokenModel(Base):
    """Хранение SHA-256 хэша refresh-токена в БД."""
    __tablename__ = "refresh_tokens"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        # Одиночный индекс убираем — покрывается составным ниже
        index=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
    )

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user: Mapped["UserModel"] = relationship(back_populates="refresh_tokens")

    __table_args__ = (
        # Покрывает: фильтры по user_id + revoked + expires_at
        # Используется в: get_active_by_user_id, revoke_all_for_user,
        #                 delete_stale_for_user, delete_oldest_beyond_limit
        Index(
            "ix_refresh_tokens_user_active",
            "user_id",
            "revoked",
            "expires_at",
        ),
        # Покрывает: глобальную чистку Celery (delete_expired_global)
        # WHERE expires_at < now() OR revoked = true — full scan без этого индекса
        Index(
            "ix_refresh_tokens_expires_at",
            "expires_at",
        ),
    )