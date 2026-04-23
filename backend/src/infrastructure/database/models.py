"""ORM-модели приложения (SQLAlchemy declarative)."""

import datetime
from datetime import timezone
from typing import Annotated

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    DateTime, String, ForeignKey, Boolean,
    func, text, Index,
    Enum as SQLEnum,
)

from .config_db import Base
from src.domain.entities import AuthProvider

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
