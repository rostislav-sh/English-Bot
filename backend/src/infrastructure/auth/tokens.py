"""Создание и хэширование JWT-токенов (access / refresh)."""

import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta

import jwt

from src.config import settings

logger = logging.getLogger(__name__)


class TokenExpiredError(ValueError):
    """JWT истёк."""


class TokenInvalidError(ValueError):
    """JWT невалиден или неверного типа."""


class TokenHelper:
    """Создание, декодирование и хэширование JWT-токенов."""

    def hash_session_token(self, token: str) -> str:
        """Возвращает SHA-256 хэш токена для безопасного хранения в БД."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_access_token(self, user_id: int) -> str:
        """Создаёт короткоживущий JWT access-токен."""
        return self._create_token(
            user_id=user_id,
            token_type="access",
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

    def create_refresh_token(self, user_id: int) -> str:
        """Создаёт долгоживущий JWT refresh-токен."""
        return self._create_token(
            user_id=user_id,
            token_type="refresh",
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )

    def decode_refresh_token(self, raw_token: str) -> dict:
        """Декодирует и верифицирует refresh JWT.

        Проверяет подпись, exp, тип токена.
        Вызывать ДО hash-lookup в БД — дешёвая проверка без IO.

        Raises:
            TokenExpiredError: токен истёк.
            TokenInvalidError: подпись невалидна или тип неверный.
        """
        try:
            payload = jwt.decode(
                raw_token,
                key=settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            logger.info("Refresh JWT истёк")
            raise TokenExpiredError
        except jwt.PyJWTError as exc:
            logger.warning("Невалидный refresh JWT: %s", exc)
            raise TokenInvalidError

        if payload.get("type") != "refresh":
            logger.warning(
                "Неверный тип токена при decode_refresh: %s",
                payload.get("type"),
            )
            raise TokenInvalidError

        return payload

    def _create_token(
        self,
        user_id: int,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        """Формирует JWT с claim-ами sub, type, iat, exp, iss, jti."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),           # subject — идентификатор пользователя
            "type": token_type,             # тип токена (access / refresh)
            "iat": int(now.timestamp()),    # issued-at — время выпуска
            "exp": int((now + expires_delta).timestamp()),  # expiration — время истечения
            "iss": settings.app_name,       # issuer — имя приложения
            "jti": secrets.token_hex(16),   # уникальный ID — защита от коллизий
        }
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        logger.debug("Создан %s-токен для user_id=%s", token_type, user_id)
        return token


tokens = TokenHelper()
