import hashlib
from datetime import datetime, timezone, timedelta

import jwt

from src.config import settings


class TokenHelper:
    """Создание и хэширование JWT-токенов."""

    def hash_session_token(self, token: str) -> str:
        """Возвращает SHA-256 хэш токена для безопасного хранения в БД."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_access_token(self, user_id: int) -> str:
        """Создаёт короткоживущий JWT access-токен."""
        return self._create_token(
            user_id, "access",
            timedelta(minutes=settings.auth_access_token_expire_minutes),
        )

    def create_refresh_token(self, user_id: int) -> str:
        """Создаёт долгоживущий JWT refresh-токен."""
        return self._create_token(
            user_id, "refresh",
            timedelta(days=settings.auth_refresh_token_expire_days),
        )

    def _create_token(self, user_id: int, token_type: str, expires_delta: timedelta) -> str:
        """Формирует JWT с claim-ами sub, type, iat, exp, iss."""
        now = datetime.now(timezone.utc)
        payload = {
            # subject (sub) — идентификатор пользователя в виде строки.
            "sub": str(user_id),
            # собственное поле type для различения типов (access/refresh).
            "type": token_type,
            # issued-at (iat) — время выпуска.
            "iat": int(now.timestamp()),
            # expiration (exp) — время истечения.
            "exp": int((now + expires_delta).timestamp()),
            # issuer (iss) — имя приложения, чтобы отличать токены разных сервисов.
            "iss": settings.app_name,
        }
        return jwt.encode(payload, settings.auth_jwt_secret_key, algorithm=settings.auth_jwt_algorithm)


tokens = TokenHelper()
