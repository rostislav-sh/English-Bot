"""Сервис аутентификации."""
from datetime import datetime, timezone, timedelta

from src.auth.tokens import tokens
from src.config import settings
from src.database.models import User
from src.exceptions import InvalidCredentialsError
from src.interfaces.unitofwork import IUserUnitOfWork
from src.auth.security import security
from src.schemas.auth import TokenPair


class AuthService:
    """Бизнес-логика регистрации и авторизации."""
    
    def __init__(self, uow: IUserUnitOfWork):
        self.uow = uow

    async def register(self, email: str, password: str) -> Users:
        """Создаёт пользователя с захэшированным паролем."""
        async with self.uow:
            hash_password = security.hash_password(password)
            user = await self.uow.user_repo.register(email=email, password=hash_password)
            await self.uow.commit()
            return user

    async def login(self, email: str, password: str) -> tuple[str, str]:
        """Проверяет учётные данные, возвращает (access_token, refresh_token).

        Raises:
            InvalidCredentialsError: Неверный email или пароль.
        """
        user = await self._get_user_and_check_password(email=email, password=password)
        pair = await self._issue_token(user_id=user.id)
        return pair.access_token, pair.refresh_token


    async def _get_user_and_check_password(self, email: str, password: str) -> User:
        """Находит пользователя и проверяет пароль. Не раскрывает, что именно неверно.

        Raises:
            InvalidCredentialsError: Пользователь не найден или пароль неверный.
        """
        user = await self.uow.user_repo.get_user_by_email(email=email)
        if not user or not security.verify_password(password=password, hashed_password=user.password_hash):
            raise InvalidCredentialsError
        return user

    def _refresh_expiry(self) -> datetime:
        """Возвращает UTC-время истечения refresh-токена."""
        return datetime.now(timezone.utc) + timedelta(days=settings.auth_refresh_token_expire_days)

    async def _issue_token(self, user_id: int) -> TokenPair:
        """Создаёт access/refresh JWT и сохраняет хэш refresh-токена в БД."""
        # Access — это JWT, refresh — случайная строка, хранится только как хэш.
        access_token = tokens.create_access_token(user_id=user_id)
        refresh_token = tokens.create_refresh_token(user_id=user_id)
        # Хэшируем refresh перед сохранением, чтобы не держать сырой токен в БД.
        refresh_hash = tokens.hash_session_token(token=refresh_token)
        expires_at = self._refresh_expiry()
        async with self.uow:
            await self.uow.user_repo.create_refresh_token(
                user_id=user_id,
                token_hash=refresh_hash,
                expires_at=expires_at,
            )
            await self.uow.commit()
            return TokenPair(access_token=access_token, refresh_token=refresh_token)
