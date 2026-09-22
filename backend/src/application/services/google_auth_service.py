"""Сервис Google OAuth: построение URL, обмен code → user_info."""

import asyncio
import logging
import secrets
from urllib.parse import urlencode

import aiohttp
from pydantic import ValidationError

from src.application.dto.auth import GoogleAuthorizationURL, GoogleUserData
from src.config import settings
from src.domain.exceptions import (
    GoogleAuthorizationCodeError,
    GoogleDataReadError,
    GoogleEmailNotVerifiedError, # Изменен на NotVerifiedError для точности
    GoogleIdTokenNotFoundError,
    GoogleTokenExchangeTimeoutError,
)
from src.infrastructure.auth.security import security
from src.application.interfaces.redis import RedisAuthState

logger = logging.getLogger(__name__)


class GoogleAuthService:
    """HTTP-взаимодействие с Google OAuth и верификация id_token."""

    def __init__(self, redis: RedisAuthState, http_session: aiohttp.ClientSession) -> None:
        self._redis = redis
        self._http = http_session  # Сохраняем инжектированную сессию!

    # ────────────────────────────────────────────────────────────────
    #  Authorize URL
    # ────────────────────────────────────────────────────────────────

    async def get_authorization_url(self) -> GoogleAuthorizationURL:
        """Генерирует URL редиректа на Google consent screen."""
        state = secrets.token_urlsafe(32)
        await self._redis.save_state(state)

        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",       # Не требуем refresh_token от гугла
            "prompt": "select_account",    # Даем юзеру выбрать аккаунт (лучший UX)
        }

        url = f"{settings.google_authorize_url}?{urlencode(params)}"
        logger.info("Сгенерирован Google OAuth URL, state=%s…", state[:8])
        return GoogleAuthorizationURL(url=url, state=state)

    # ────────────────────────────────────────────────────────────────
    #  Callback
    # ────────────────────────────────────────────────────────────────

    async def get_user_info(self, code: str, state: str) -> GoogleUserData:
        """Валидирует state, обменивает code на токен, возвращает данные пользователя."""
        await self._redis.consume_state(state)

        raw_id_token = await self._exchange_code(code)
        return await self._verify_token(raw_id_token)

    # ────────────────────────────────────────────────────────────────
    #  Приватное: обмен и верификация
    # ────────────────────────────────────────────────────────────────

    async def _exchange_code(self, code: str) -> str:
        """HTTP-запрос к Google Token Endpoint, возвращает сырой id_token."""
        data = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            # Используем глобальную сессию aiohttp для переиспользования соединений
            async with self._http.post(
                settings.google_token_url,
                data=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning("Google token exchange failed: %s %s", resp.status, text)
                    raise GoogleAuthorizationCodeError()
                payload = await resp.json()

        except asyncio.TimeoutError as exc:
            logger.error("Тайм-аут при обмене кода авторизации Google")
            raise GoogleTokenExchangeTimeoutError() from exc

        id_token = payload.get("id_token")
        if not id_token:
            logger.error("Google не вернул id_token")
            raise GoogleIdTokenNotFoundError()

        logger.debug("Google id_token получен успешно")
        return id_token

    async def _verify_token(self, raw_id_token: str) -> GoogleUserData:
        """Верифицирует подпись Google ID-токена, возвращает данные пользователя."""
        try:
            # Выполняем синхронную валидацию (с походами за сертификатами) в пуле потоков
            decoded = await asyncio.to_thread(
                security.decode_google_token,
                raw_id_token,
                settings.google_client_id
            )

            # Pydantic сам отловит отсутствие обязательных полей (sub, email)
            # Примечание: Убедись, что в GoogleUserData настроен alias ("sub" -> "google_id")
            user_info = GoogleUserData(**decoded)

        except (ValueError, ValidationError) as exc:
            logger.warning("Ошибка верификации или структуры Google ID-токена: %s", exc)
            raise GoogleDataReadError(str(exc)) from exc

        if not user_info.email_verified:
            logger.warning("Email не подтверждён в Google: %s", user_info.email)
            raise GoogleEmailNotVerifiedError()

        logger.info("Google OAuth: верифицирован юзер sub=%s", user_info.google_id)
        return user_info
