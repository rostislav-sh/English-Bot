from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

class AuthProvider(str, Enum):
    """Способ аутентификации пользователя."""
    LOCAL = "local"  # Регистрация через email + пароль
    GOOGLE = "google"  # Вход только через Google
    HYBRID = "hybrid"  # И пароль, и Google привязаны


@dataclass
class User:
    """Пользователь."""

    # ── Обязательные при создании ──
    email: str
    auth_provider: AuthProvider = AuthProvider.LOCAL

    # ── Опциональные ──
    password_hash: "str | None" = None
    google_id: "str | None" = None
    username: "str | None" = None
    picture_url: "str | None" = None

    # ── Назначаются инфраструктурой ──
    id: "int | None" = None
    created_at: "datetime | None" = None
    updated_at: "datetime | None" = None


@dataclass
class RefreshToken:
    """Refresh-токен."""

    # ── Обязательные при создании ──
    user_id: int
    token_hash: str
    expires_at: datetime

    # ── С дефолтами ──
    revoked: bool = False

    # ── Назначаются инфраструктурой ──
    id: "int | None" = None
    created_at: "datetime | None" = None
    updated_at: "datetime | None" = None

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_usable(self) -> bool:
        return not self.revoked and not self.is_expired
