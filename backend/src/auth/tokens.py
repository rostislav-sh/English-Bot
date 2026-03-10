"""Создание и хэширование JWT-токенов (access / refresh)."""

import hashlib
import logging
from datetime import datetime, timezone, timedelta

import jwt

from src.config import settings

logger = logging.getLogger(__name__)


class TokenHelper:
    """Создание и хэширование JWT-токенов."""

    def hash_session_token(self, token: str) -> str:
        """Возвращает SHA-256 хэш токена для безопасного хранения в БД."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_access_token(self, user_id: int) -> str:
        """Создаёт короткоживущий JWT access-токен."""
        return self._create_token(
            user_id, "access",
            timedelta(minutes=settings.access_token_expire_minutes),
        )

    def create_refresh_token(self, user_id: int) -> str:
        """Создаёт долгоживущий JWT refresh-токен."""
        return self._create_token(
            user_id, "refresh",
            timedelta(days=settings.refresh_token_expire_days),
        )

    def _create_token(self, user_id: int, token_type: str, expires_delta: timedelta) -> str:
        """Формирует JWT с claim-ами sub, type, iat, exp, iss."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),           # subject — идентификатор пользователя
            "type": token_type,             # тип токена (access / refresh)
            "iat": int(now.timestamp()),    # issued-at — время выпуска
            "exp": int((now + expires_delta).timestamp()),  # expiration — время истечения
            "iss": settings.app_name,       # issuer — имя приложения
        }
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        logger.debug("Создан %s-токен для user_id=%s", token_type, user_id)
        return token


tokens = TokenHelper()
