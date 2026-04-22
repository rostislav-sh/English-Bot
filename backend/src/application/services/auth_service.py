"""Координирующий сервис аутентификации."""

import logging

from src.application.interfaces.unitofwork import IUnitOfWork
from src.application.services.user_service import UserService
from src.application.services.token_service import TokenService
from src.application.services.google_auth_service import GoogleAuthService
from src.domain.entities import User
from src.schemas.auth import TokenPair
from src.api.exceptions import RefreshTokenNotFoundError, RefreshTokenLifetimeExpiredError

logger = logging.getLogger(__name__)


class AuthService:
    """Координирует UserService, TokenService, GoogleAuthService.

    Содержит только бизнес-логику сценариев — без деталей криптографии,
    HTTP и персистентности.
    """

    def __init__(
            self,
            uow: IUnitOfWork,
            user_service: UserService,
            token_service: TokenService,
            google_auth_service: GoogleAuthService,
    ) -> None:
        self._uow = uow
        self._user_service = user_service
        self._token_service = token_service
        self._google_auth_service = google_auth_service

    async def register(self, email: str, password: str, username: str) -> tuple[User, TokenPair]:
        """Регистрирует пользователя, выдаёт пару токенов."""
        logger.info("Регистрация: %s", email)
        async with self._uow:
            user = await self._user_service.register(
                email=email,
                password=password,
                username=username,
            )
            pair = await self._token_service.issue(user.id)
            await self._uow.commit()
        logger.info("Пользователь зарегистрирован: id=%s", user.id)
        return user, pair

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        """Проверяет credentials, выдаёт пару токенов."""
        logger.info("Вход: %s", email)
        async with self._uow:
            user = await self._user_service.get_authenticated(
                email=email,
                password=password,
            )
            pair = await self._token_service.issue(user.id)
            await self._uow.commit()
        logger.info("Успешный вход: user_id=%s", user.id)
        return user, pair

    async def refresh(self, refresh_token: str) -> tuple[User, TokenPair]:
        """Обновляет пару токенов по refresh-токену."""
        logger.info("Обновление токенов")
        async with self._uow:
            stored_token = await self._token_service.get_valid(refresh_token)
            user = await self._user_service.get_by_id(stored_token.user_id)
            stored_token.revoked = True  # sync_tracked() запишет в БД при commit()
            pair = await self._token_service.issue(user.id)
            await self._uow.commit()
        logger.info("Токены успешно обновлены: user_id=%s", user.id)
        return user, pair

    async def logout(self, refresh_token: str) -> None:
        """Инвалидирует переданный refresh-токен.

        Истёкший или уже отозванный токен не считается ошибкой —
        пользователь всё равно считается вышедшим.
        """
        logger.info("Выход пользователя")
        async with self._uow:
            try:
                stored_token = await self._token_service.get_valid(refresh_token)
                stored_token.revoked = True
                await self._uow.commit()
            except (RefreshTokenNotFoundError, RefreshTokenLifetimeExpiredError):
                # Токен уже недействителен — выход засчитываем как успешный
                logger.info("Logout: токен уже недействителен, выход засчитан")
        logger.info("Refresh-токен отозван")

    async def get_google_url(self) -> tuple[str, str]:
        """Генерирует URL для Google OAuth consent screen."""
        return await self._google_auth_service.get_authorization_url()

    async def authenticate_via_google(self, code: str, state: str) -> tuple[User, TokenPair]:
        """Завершает Google OAuth flow."""
        logger.info("Google OAuth callback, state=%s…", state[:8])
        user_info = await self._google_auth_service.get_user_info(
            code=code,
            state=state,
        )
        async with self._uow:
            user = await self._user_service.get_or_create_google_user(user_info)
            pair = await self._token_service.issue(user.id)
            await self._uow.commit()
        return user, pair
