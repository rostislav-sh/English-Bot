"""Утилиты безопасности: хэширование паролей и верификация Google ID-токенов."""

import hashlib
import logging

import bcrypt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from src.config import settings

logger = logging.getLogger(__name__)


class Security:
    """Хэширование и проверка паролей (SHA-256 прехэш + bcrypt),
    а также верификация Google OAuth ID-токенов."""

    # Кэшируем Request-объект, чтобы повторно использовать HTTP-сессию
    # при загрузке публичных ключей Google (кэш сертификатов внутри).
    _google_request = google_requests.Request()

    def hash_password(self, password: str) -> str:
        """Возвращает bcrypt-хэш пароля."""
        digest = self._password_digest(password)
        return bcrypt.hashpw(digest, bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Проверяет пароль против bcrypt-хэша из БД."""
        digest = self._password_digest(password)
        return bcrypt.checkpw(digest, hashed_password.encode("utf-8"))

    def decode_google_token(self, token: str) -> dict:
        """Верифицирует подпись Google ID-токена и возвращает его payload.

        Проверяет:
          - RS256-подпись по публичным ключам Google (кэшируются);
          - ``aud`` == наш ``GOOGLE_CLIENT_ID``;
          - ``iss`` ∈ {accounts.google.com, https://accounts.google.com};
          - ``exp`` (срок действия).

        Raises:
            ValueError: если токен невалидный, просроченный или audience не совпадает.
        """
        logger.debug("Верификация Google ID-токена")
        decoded = google_id_token.verify_oauth2_token(
            token,
            self._google_request,
            audience=settings.google_client_id,
        )
        logger.debug("Google ID-токен успешно верифицирован, sub=%s", decoded.get("sub"))
        return decoded

    def _password_digest(self, password: str) -> bytes:
        """SHA-256 прехэш для устранения ограничения длины пароля в bcrypt."""
        return hashlib.sha256(password.encode("utf-8")).digest()


security = Security()
