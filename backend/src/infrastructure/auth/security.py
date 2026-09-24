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

    # Допуск на рассинхрон часов при проверке iat/exp Google ID-токена.
    # exp всё равно отдельно ограничивает время жизни токена, поэтому
    # небольшой допуск здесь не открывает окно для replay-атак.
    _CLOCK_SKEW_SECONDS = 10

    def hash_password(self, password: str) -> str:
        """Возвращает bcrypt-хэш пароля."""
        digest = self._password_digest(password)
        return bcrypt.hashpw(digest, bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Проверяет пароль против bcrypt-хэша из БД."""
        digest = self._password_digest(password)
        return bcrypt.checkpw(digest, hashed_password.encode("utf-8"))

    def decode_google_token(self, token: str, google_client_id: str) -> dict:
        """Верифицирует подпись Google ID-токена и возвращает его payload.

        Проверяет:
          - RS256-подпись по публичным ключам Google (кэшируются);
          - ``aud`` == наш ``GOOGLE_CLIENT_ID``;
          - ``iss`` ∈ {accounts.google.com, https://accounts.google.com};
          - ``exp``/``iat`` (срок действия) с допуском в _CLOCK_SKEW_SECONDS —
            без него даже секундный рассинхрон часов роняет верификацию
            с "Token used too early" (у google-auth дефолт 0, без допуска).

        Raises:
            ValueError: если токен невалидный, просроченный или audience не совпадает.
        """
        logger.debug("Верификация Google ID-токена")
        decoded = google_id_token.verify_oauth2_token(
            token,
            self._google_request,
            audience=google_client_id,
            clock_skew_in_seconds=self._CLOCK_SKEW_SECONDS,
        )
        logger.debug("Google ID-токен успешно верифицирован, sub=%s", decoded.get("sub"))
        return decoded

    def _password_digest(self, password: str) -> bytes:
        """SHA-256 прехэш для устранения ограничения длины пароля в bcrypt."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")


security = Security()
