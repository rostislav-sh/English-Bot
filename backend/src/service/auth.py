"""Сервис аутентификации."""

from src.database.models import Users
from src.interfaces.unitofwork import IUserUnitOfWork
from src.auth.security import security


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