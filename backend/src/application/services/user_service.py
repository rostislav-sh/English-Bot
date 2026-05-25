"""Сервис управления пользователями."""

import logging

from src.application.dto.auth import RegisterCommand
from src.application.interfaces.exceptions import UniqueViolationError
from src.application.interfaces.unitofwork import IUnitOfWork
from src.domain import User, AuthProvider
from src.domain.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    UserAlreadyExistsError,
)
from src.application.services import PasswordService

logger = logging.getLogger(__name__)


class UserService:
    """Создание / поиск / обновление пользователей.

    Работает с доменными сущностями User через UoW.
    Все методы вызывать внутри активного UoW-контекста.
    """

    def __init__(self, uow: IUnitOfWork, password_service: PasswordService) -> None:
        self._uow = uow
        self._password_service = password_service

    # ── Поиск ────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: int) -> User:
        """Возвращает пользователя по ID или выбрасывает UserNotFoundError."""
        user = await self._uow.users.get_by_id(user_id)
        if not user:
            logger.warning("Пользователь не найден: user_id=%s", user_id)
            raise UserNotFoundError
        return user

    async def get_by_email(self, email: str) -> User | None:
        """Возвращает пользователя по Email или None."""
        return await self._uow.users.get_by_email(email)

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Возвращает пользователя по google_id или None."""
        return await self._uow.users.get_by_google_id(google_id)

    # ── Создание ─────────────────────────────────────────────────────

    async def register(self, cmd: RegisterCommand) -> User:
        """Создаёт локального пользователя."""
        if await self._uow.users.exists_by_email(cmd.email):
            raise UserAlreadyExistsError()

        user = User(
            email=cmd.email,
            password_hash=self._password_service.hash(cmd.password),
            username=cmd.username,
            auth_provider=AuthProvider.LOCAL,
        )
        try:
            result = await self._uow.users.add(user)
            logger.info("Пользователь создан: id=%s email=%s", result.id, cmd.email)
            return result
        except UniqueViolationError as e:
            # Ловим (Race Condition), когда кто-то вклинился между проверкой и вставкой
            logger.info("Race-condition при регистрации: %s", cmd.email)
            raise UserAlreadyExistsError() from e

    async def get_authenticated(self, email: str, password: str) -> User:
        """Проверяет credentials, возвращает пользователя или выбрасывает ошибку."""
        user = await self._uow.users.get_by_email(email)

        if not user:
            # Защита от User Enumeration Attack — постоянное время ответа
            await self._password_service.verify_with_timing_protection(password)
            logger.warning("Вход с несуществующим email: %s", email)
            raise InvalidCredentialsError()

        # Google-only аккаунт — пароль не установлен, вход через пароль невозможен
        if not user.password_hash:
            await self._password_service.verify_with_timing_protection(password)
            logger.warning(
                "Попытка входа по паролю для Google-аккаунта: user_id=%s provider=%s",
                user.id,
                user.auth_provider,
            )
            raise InvalidCredentialsError()

        if not await self._password_service.verify(password, user.password_hash):
            logger.warning("Неверный пароль: user_id=%s", user.id)
            raise InvalidCredentialsError()

        return user

    # ── Google OAuth ──────────────────────────────────────────────────

    async def get_or_create_google_user(self, user_info: GoogleUserData) -> User:
        """Возвращает существующего или создаёт нового пользователя через Google."""

        # Ищем по google_id
        user = await self._uow.users.get_by_google_id(user_info.google_id)
        if user:
            logger.info("Вход через Google: user_id=%s", user.id)
            return user

        # Ищем по email — Account Linking
        user = await self._uow.users.get_by_email(user_info.email)
        if user:
            logger.info("Привязка Google к существующему аккаунту: user_id=%s", user.id)
            return await self._link_google(user, user_info)

        # Новый пользователь
        logger.info("Создание нового Google-пользователя: email=%s", user_info.email)
        return await self._create_google_user(user_info)

    # ── Приватные методы ─────────────────────────────────────────────

    async def _link_google(self, user: User, user_info: GoogleUserData) -> User:
        """Привязывает Google-аккаунт к существующему пользователю."""
        user.google_id = user_info.google_id
        user.auth_provider = (
            AuthProvider.HYBRID if user.password_hash else AuthProvider.GOOGLE
        )
        if not user.username and user_info.username:
            user.username = user_info.username
        if not user.picture_url and user_info.picture:
            user.picture_url = user_info.picture

        await self._uow.users.update(user)
        logger.info(
            "Google привязан: user_id=%s provider=%s",
            user.id,
            user.auth_provider,
        )
        return user

    async def _create_google_user(self, user_info: GoogleUserData) -> User:
        """Создаёт нового пользователя из данных Google."""
        user = User(
            email=user_info.email,
            google_id=user_info.google_id,
            auth_provider=AuthProvider.GOOGLE,
            username=user_info.username,
            picture_url=user_info.picture,
        )
        try:
            result = await self._uow.users.add(user)
            logger.info("Google-пользователь создан: id=%s email=%s", result.id, user_info.email)
            return result
        except UniqueViolationError as e:
            # Race: параллельный запрос успел вставить → повторно читаем
            logger.info(
                "Race при создании Google-пользователя, перечитываем: %s",
                user_info.email,
            )
            user = await self._uow.users.get_by_email(user_info.email)
            if user is None:
                raise e
            return await self._link_google(user, user_info)