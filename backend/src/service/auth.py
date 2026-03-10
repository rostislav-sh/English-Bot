"""Сервис аутентификации.

Содержит всю бизнес-логику: регистрация, вход, ротация токенов,
OAuth через Google.
"""

import asyncio
import logging
import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta

import aiohttp
from pydantic import ValidationError

from src.auth.tokens import tokens
from src.config import settings
from src.database.models import User, RefreshToken
from src.exceptions import (
    InvalidCredentialsError,
    RefreshTokenNotFoundError,
    RefreshTokenLifetimeExpiredError,
    UserNotFoundError,
    GoogleIdTokenNotFoundError,
    GoogleExpiredAuthorizationCodeError,
    GoogleTokenExchangeTimeoutError,
    GoogleDataReadError,
    GoogleEmailNotFoundError,
)
from src.interfaces.redis_auth_state import RedisAuthState
from src.interfaces.unitofwork import IUserUnitOfWork
from src.auth.security import security
from src.schemas.auth import TokenPair, GoogleUserData

logger = logging.getLogger(__name__)

# Тайм-аут для HTTP-запросов к Google (секунды)
_GOOGLE_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=10)


class AuthService:
    """Бизнес-логика регистрации и авторизации."""

    def __init__(self, uow: IUserUnitOfWork, redis: RedisAuthState):
        self.uow = uow
        self.redis = redis

    # ── Публичные методы ─────────────────────────────────────────────

    async def register(self, email: str, password: str) -> tuple[User, TokenPair]:
        """Создаёт пользователя и выдаёт пару токенов."""
        logger.info("Регистрация пользователя: %s", email)
        async with self.uow:
            hash_password = security.hash_password(password)
            user = await self.uow.user_repo.register(email=email, password=hash_password)
            pair = await self._issue_token(user_id=user.id)
            await self.uow.commit()
            logger.info("Пользователь зарегистрирован: id=%s, email=%s", user.id, email)
            return user, pair

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        """Проверяет учётные данные, возвращает пользователя и пару токенов."""
        logger.info("Попытка входа: %s", email)
        async with self.uow:
            user = await self._get_user_and_check_password(email=email, password=password)
            pair = await self._issue_token(user_id=user.id)
            await self.uow.commit()
            logger.info("Успешный вход: user_id=%s", user.id)
            return user, pair

    async def refresh(self, raw_refresh_token: str) -> tuple[User, TokenPair]:
        """Ротация: валидирует старый refresh, удаляет его, выдаёт новую пару."""
        logger.debug("Ротация refresh-токена")
        async with self.uow:
            update = await self._get_valid_refresh(refresh_token=raw_refresh_token)
            user = await self._get_user_for_token(user_id=update.user_id)
            await self.uow.user_repo.delete_refresh_token(token_object=update)
            pair = await self._issue_token(user_id=user.id)
            await self.uow.commit()
            logger.info("Refresh-токен обновлён: user_id=%s", user.id)
            return user, pair

    async def get_google_url(self) -> tuple[str, str]:
        """Генерирует URL для редиректа пользователя на Google OAuth consent screen.

        Returns:
            tuple[str, str]: (authorization_url, state)
        """
        state = secrets.token_urlsafe(32)
        await self.redis.save_state(state)

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

    async def authenticate_via_google(self, code: str, state: str) -> tuple[User, TokenPair]:
        """Завершает Google OAuth: обменивает code на токен, создаёт / находит пользователя.

        Args:
            code: Authorization code от Google.
            state: CSRF-state для проверки.

        Returns:
            tuple[User, TokenPair]: пользователь и пара JWT-токенов.
        """
        logger.info("Google OAuth callback, state=%s…", state[:8])
        await self.redis.consume_state(state)

        raw_id_token = await self._exchange_code_for_token(code)
        user_info = await self._parse_and_validate_google_token(raw_id_token)

        async with self.uow:
            user = await self.uow.user_repo.get_by_google_id(user_info.google_id)

            if not user:
                user = await self.uow.user_repo.get_user_by_email(user_info.email)
                if user:
                    logger.info("Привязка Google к существующему аккаунту: user_id=%s", user.id)
                    user = await self.uow.user_repo.link_google_account(user, user_info)
                else:
                    logger.info("Создание нового пользователя через Google: email=%s", user_info.email)
                    user = await self.uow.user_repo.create_google_user(user_info)
            else:
                logger.info("Вход через Google: user_id=%s", user.id)

            pair = await self._issue_token(user_id=user.id)
            await self.uow.commit()
            return user, pair

    # ── Google: обмен кода и верификация ─────────────────────────────

    async def _exchange_code_for_token(self, code: str) -> str:
        """Делает HTTP-запрос к Google Token Endpoint и возвращает сырой id_token.

        Raises:
            GoogleExpiredAuthorizationCodeError: если Google вернул не-200.
            GoogleTokenExchangeTimeoutError: при тайм-ауте запроса.
            GoogleIdTokenNotFoundError: если в ответе нет id_token.
        """
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
                        logger.error("Google token exchange failed: status=%s body=%s", response.status, body)
                        raise GoogleExpiredAuthorizationCodeError
                    token_data = await response.json()
        except asyncio.TimeoutError:
            logger.error("Тайм-аут при обмене кода авторизации Google")
            raise GoogleTokenExchangeTimeoutError

        id_token = token_data.get("id_token")
        if not id_token:
            logger.error("Google не вернул id_token, ключи ответа: %s", list(token_data.keys()))
            raise GoogleIdTokenNotFoundError

        logger.debug("Google id_token получен успешно")
        return id_token

    async def _parse_and_validate_google_token(self, raw_id_token: str) -> GoogleUserData:
        """Верифицирует подпись Google ID-токена и извлекает данные пользователя.

        ``verify_oauth2_token`` — синхронный (делает HTTP за сертификатами),
        поэтому выполняется в отдельном потоке через ``asyncio.to_thread``.

        Raises:
            GoogleDataReadError: если токен невалиден или не парсится.
            GoogleEmailNotFoundError: если email не подтверждён.
        """
        try:
            # verify_oauth2_token — блокирующий вызов (HTTP к googleapis)
            decoded_token = await asyncio.to_thread(
                security.decode_google_token, token=raw_id_token
            )
            user_info = GoogleUserData(**decoded_token)
        except (ValueError, ValidationError) as error:
            logger.warning("Ошибка верификации Google ID-токена: %s", error)
            raise GoogleDataReadError(str(error))

        if not user_info.email_verified:
            logger.warning("Email не подтверждён в Google: %s", user_info.email)
            raise GoogleEmailNotFoundError

        return user_info

    # ── Пароль ───────────────────────────────────────────────────────

    async def _get_user_and_check_password(self, email: str, password: str) -> User:
        """Проверяет пароль. Не раскрывает, что именно неверно."""
        user = await self.uow.user_repo.get_user_by_email(email=email)
        if not user:
            # Хэш-пустышка, чтобы время ответа было одинаковым (защита от User Enumeration Attack)
            security.verify_password(password=password, hashed_password=settings.fake_password_hash)
            logger.warning("Попытка входа с несуществующим email: %s", email)
            raise InvalidCredentialsError
        if not security.verify_password(password=password, hashed_password=user.password_hash):
            logger.warning("Неверный пароль: user_id=%s", user.id)
            raise InvalidCredentialsError
        return user

    # ── Токены ───────────────────────────────────────────────────────

    def _refresh_expiry(self) -> datetime:
        """UTC-время истечения refresh-токена."""
        return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    async def _issue_token(self, user_id: int) -> TokenPair:
        """Создаёт access/refresh JWT и сохраняет хэш refresh в БД."""
        access_token = tokens.create_access_token(user_id=user_id)
        refresh_token = tokens.create_refresh_token(user_id=user_id)
        refresh_hash = tokens.hash_session_token(token=refresh_token)
        expires_at = self._refresh_expiry()

        await self.uow.user_repo.create_refresh_token(
            user_id=user_id,
            token_hash=refresh_hash,
            expires_at=expires_at,
        )
        await self.uow.user_repo.enforce_session_limit(
            user_id=user_id,
            max_limit=settings.max_sessions_per_user,
        )
        logger.debug("Выданы токены: user_id=%s", user_id)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def _get_valid_refresh(self, refresh_token: str) -> RefreshToken:
        """Ищет refresh в БД, проверяет revoked и expires_at."""
        token_hash = tokens.hash_session_token(token=refresh_token)
        stored = await self.uow.user_repo.get_refresh_token(token_hash=token_hash)

        if not stored or stored.revoked:
            logger.warning("Refresh-токен не найден или отозван")
            raise RefreshTokenNotFoundError

        now = datetime.now(timezone.utc)
        expires_at = self._ensure_aware(stored.expires_at)

        if expires_at <= now:
            await self.uow.user_repo.delete_refresh_token(token_object=stored)
            await self.uow.commit()
            logger.info("Refresh-токен истёк, удалён: id=%s", stored.id)
            raise RefreshTokenLifetimeExpiredError

        return stored

    async def _get_user_for_token(self, user_id: int) -> User:
        """Возвращает пользователя по ID или выбрасывает UserNotFoundError."""
        user = await self.uow.user_repo.get_user_by_id(user_id=user_id)
        if not user:
            logger.warning("Пользователь не найден: user_id=%s", user_id)
            raise UserNotFoundError
        return user

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        """Приводит naive datetime к aware UTC."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
