"""Сервис аутентификации."""
from datetime import datetime, timezone, timedelta

from src.auth.tokens import tokens
from src.config import settings
from src.database.models import User, RefreshToken
from src.exceptions import (
    InvalidCredentialsError,
    RefreshTokenNotFoundError,
    RefreshTokenLifetimeExpiredError,
    UserNotFoundError,
)
from src.interfaces.unitofwork import IUserUnitOfWork
from src.auth.security import security
from src.schemas.auth import TokenPair


class AuthService:
    """Бизнес-логика регистрации и авторизации."""

    def __init__(self, uow: IUserUnitOfWork):
        self.uow = uow

    async def register(self, email: str, password: str) -> tuple[User, TokenPair]:
        """Создаёт пользователя и выдаёт пару токенов."""
        async with self.uow:
            hash_password = security.hash_password(password)
            user = await self.uow.user_repo.register(email=email, password=hash_password)
            pair = await self._issue_token(user_id=user.id)
            await self.uow.commit()
            return user, pair

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        """Проверяет учётные данные, возвращает пользователя и пару токенов."""
        async with self.uow:
            user = await self._get_user_and_check_password(email=email, password=password)
            pair = await self._issue_token(user_id=user.id)
            await self.uow.commit()
            return user, pair

    async def refresh(self, raw_refresh_token: str) -> tuple[User, TokenPair]:
        """Ротация: валидирует старый refresh, удаляет его, выдаёт новую пару."""
        async with self.uow:
            update = await self._get_valid_refresh(refresh_token=raw_refresh_token)
            user = await self._get_user_for_token(user_id=update.user_id)
            await self.uow.user_repo.delete_refresh_token(token_object=update)
            pair = await self._issue_token(user_id=user.id)
            await self.uow.commit()
            return user, pair

    async def _get_user_and_check_password(self, email: str, password: str) -> User:
        """Проверяет пароль. Не раскрывает, что именно неверно."""
        user = await self.uow.user_repo.get_user_by_email(email=email)
        # TODO:
        #  Если пользователь not user (нет в БД), код завершается за 1 миллисекунду.
        #  Если пользователь есть, но пароль неверный, код тратит 100-300 мс на bcrypt.
        #  Злоумышленник может замерять время ответа и узнать, зарегистрирован ли email.
        #  Это называется "User Enumeration Attack".
        #  TODO: Вычислять хэш-пустышку, если пользователь не найден,
        #   чтобы время ответа всегда было одинаково долгим.
        if not user or not security.verify_password(password=password, hashed_password=user.password_hash):
            raise InvalidCredentialsError
        return user

    def _refresh_expiry(self) -> datetime:
        """UTC-время истечения refresh-токена."""
        return datetime.now(timezone.utc) + timedelta(days=settings.auth_refresh_token_expire_days)

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
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def _get_valid_refresh(self, refresh_token: str) -> RefreshToken:
        """Ищет refresh в БД, проверяет revoked и expires_at."""
        token_hash = tokens.hash_session_token(token=refresh_token)
        stored = await self.uow.user_repo.get_refresh_token(token_hash=token_hash)

        if not stored or stored.revoked:
            raise RefreshTokenNotFoundError

        now = datetime.now(timezone.utc)
        expires_at = self._ensure_aware(stored.expires_at)

        if expires_at <= now:
            await self.uow.user_repo.delete_refresh_token(token_object=stored)
            await self.uow.commit()
            raise RefreshTokenLifetimeExpiredError

        return stored

    async def _get_user_for_token(self, user_id: int) -> User:
        """Возвращает пользователя по ID или выбрасывает UserNotFoundError."""
        user = await self.uow.user_repo.get_user_by_id(user_id=user_id)

        if not user:
            raise UserNotFoundError

        return user

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        """Приводит naive datetime к aware UTC."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt