"""Сервис Google OAuth — HTTP и верификация токена."""

import asyncio
import logging
import secrets
import urllib.parse

import aiohttp
from pydantic import ValidationError

from src.config import settings
from src.infrastructure.auth.security import security
from src.application.interfaces.redis import RedisAuthState
from src.schemas.auth import GoogleUserData
from src.api.exceptions import (
    GoogleIdTokenNotFoundError,
    GoogleExpiredAuthorizationCodeError,
    GoogleTokenExchangeTimeoutError,
    GoogleDataReadError,
    GoogleEmailNotFoundError,
)

logger = logging.getLogger(__name__)

_GOOGLE_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=10)


class GoogleAuthService:
    """HTTP-взаимодействие с Google OAuth и верификация id_token.

    Не зависит от БД и UoW — только внешний HTTP и Redis для state.
    """
    def __init__(self, redis: RedisAuthState) -> None:
        self._redis = redis

    async def get_authorization_url(self) -> tuple[str, str]:
        """Генерирует URL редиректа на Google consent screen.

        Returns:
            tuple[str, str]: (authorization_url, state)
        """
        state = secrets.token_urlsafe(32)
        await self._redis.save_state(state)

        params = {
            "client_id": settings.google_client_id,
            "response_type": "code",
            "redirect_uri": settings.google_redirect_uri,
            "scope": "openid profile email",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        url = f"{settings.base_url}?{urllib.parse.urlencode(params)}"
        logger.info("Сгенерирован Google OAuth URL, state=%s…", state[:8])
        return url, state

    async def get_user_info(self, code: str, state: str) -> GoogleUserData:
        """Валидирует state, обменивает code на токен, возвращает данные пользователя."""
        await self._redis.consume_state(state)
        raw_id_token = await self._exchange_code(code)
        return await self._verify_token(raw_id_token)

    # ── Приватные методы ─────────────────────────────────────────────

    async def _exchange_code(self, code: str) -> str:
        """HTTP-запрос к Google Token Endpoint, возвращает сырой id_token."""
        payload = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.google_redirect_uri,
        }
        try:
            async with aiohttp.ClientSession(timeout=_GOOGLE_HTTP_TIMEOUT) as session:
                async with session.post(settings.token_url, data=payload) as response:
                    if response.status != 200:
                        body = await response.text()
                        logger.error(
                            "Google token exchange failed: status=%s body=%s",
                            response.status,
                            body,
                        )
                        raise GoogleExpiredAuthorizationCodeError
                    token_data = await response.json()
        except asyncio.TimeoutError:
            logger.error("Тайм-аут при обмене кода авторизации Google")
            raise GoogleTokenExchangeTimeoutError

        id_token = token_data.get("id_token")
        if not id_token:
            logger.error(
                "Google не вернул id_token, ключи ответа: %s",
                list(token_data.keys()),
            )
            raise GoogleIdTokenNotFoundError

        logger.debug("Google id_token получен успешно")
        return id_token

    async def _verify_token(self, raw_id_token: str) -> GoogleUserData:
        """Верифицирует подпись Google ID-токена, возвращает данные пользователя.

        verify_oauth2_token — синхронный (HTTP за сертификатами),
        выполняется в пуле потоков через asyncio.to_thread.
        """
        try:
            decode = await asyncio.to_thread(
                security.decode_google_token, token=raw_id_token,
            )
            user_info = GoogleUserData(**decode)
        except (ValueError, ValidationError) as error:
            logger.warning("Ошибка верификации Google ID-токена: %s", error)
            raise GoogleDataReadError(str(error))

        if not user_info.email_verified:
            logger.warning("Email не подтверждён в Google: %s", user_info.email)
            raise GoogleEmailNotFoundError

        return user_info
